"""
Wipe the configured database and replay a local pulse.sql dump.

Blocked against production/shared hosts unless ALLOW_PROD_COMMANDS=1.
Requires --wipe-confirm. Connection settings come from the environment, never
from hardcoded credentials.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mysite.command_safety import assert_safe_for_destructive_commands, load_project_env


def connect_from_env():
    host = (os.environ.get('DB_HOST') or '').strip()
    name = (os.environ.get('DB_NAME') or '').strip()
    user = (os.environ.get('DB_USER') or '').strip()
    password = os.environ.get('DB_PASSWORD') or ''
    port = int(os.environ.get('DB_PORT') or '3306')
    missing = [key for key, value in (
        ('DB_HOST', host),
        ('DB_NAME', name),
        ('DB_USER', user),
    ) if not value]
    if missing:
        raise SystemExit(f'Missing required environment variables: {", ".join(missing)}')
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=name,
        autocommit=True,
        charset='utf8mb4',
    )


def main():
    load_project_env()
    parser = argparse.ArgumentParser(
        description='DROP every table in DB_NAME, then replay pulse.sql.',
    )
    parser.add_argument(
        '--wipe-confirm',
        action='store_true',
        help='Required. Confirms that every table in DB_NAME will be dropped.',
    )
    parser.add_argument(
        '--sql-file',
        default=str(ROOT / 'pulse.sql'),
        help='Path to the SQL dump to replay.',
    )
    args = parser.parse_args()

    assert_safe_for_destructive_commands('import_db.py')
    if not args.wipe_confirm:
        raise SystemExit(
            'Refusing to run. Pass --wipe-confirm if you intend to DROP every table in DB_NAME.'
        )

    sql_path = Path(args.sql_file)
    print(f'Connecting to {os.environ.get("DB_HOST")} / {os.environ.get("DB_NAME")}...')
    try:
        connection = connect_from_env()
        print('Connected.')
    except Exception as exc:
        raise SystemExit(f'Connection failed: {exc}') from exc

    print('Wiping existing tables...')
    with connection.cursor() as cursor:
        cursor.execute('SET FOREIGN_KEY_CHECKS = 0;')
        cursor.execute('SHOW TABLES;')
        tables = cursor.fetchall()
        for table in tables:
            cursor.execute(f'DROP TABLE IF EXISTS `{table[0]}`;')
        cursor.execute('SET FOREIGN_KEY_CHECKS = 1;')
    print('Database cleared.')

    print(f'Reading {sql_path}...')
    try:
        content = sql_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        connection.close()
        raise SystemExit(f'Could not find SQL dump at {sql_path}') from None

    raw_commands = content.split(';')
    sql_commands = []
    for cmd in raw_commands:
        clean_cmd = cmd.strip()
        if not clean_cmd or clean_cmd.startswith(('--', '/*', '#')):
            continue
        sql_commands.append(clean_cmd)

    print(f'Found {len(sql_commands)} statements to execute.')

    with connection.cursor() as cursor:
        cursor.execute('SET FOREIGN_KEY_CHECKS = 0;')
        success_count = 0
        skipped_count = 0
        for idx, cmd in enumerate(sql_commands, 1):
            try:
                cursor.execute(cmd)
                success_count += 1
            except Exception as exc:
                skipped_count += 1
                if 'syntax' not in str(exc).lower():
                    print(f'  Statement {idx} skipped: {str(exc)[:75]}')
        cursor.execute('SET FOREIGN_KEY_CHECKS = 1;')

    print(f'Done. Applied {success_count} statements, skipped {skipped_count}.')
    connection.close()


if __name__ == '__main__':
    main()
