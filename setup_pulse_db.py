"""
Create any missing PulseCapstone tables and seed default accounts.
Usage: python setup_pulse_db.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from django.apps import apps
from django.db import connection
from django.core.management import call_command


def existing_tables():
    with connection.cursor() as cur:
        cur.execute('SHOW TABLES')
        return {row[0] for row in cur.fetchall()}


def create_missing_tables():
    have = existing_tables()
    created = []
    skipped = []

    with connection.schema_editor() as editor:
        for model in apps.get_app_config('myapp').get_models():
            table = model._meta.db_table
            if table in have:
                skipped.append(table)
                continue
            editor.create_model(model)
            created.append(table)

    return created, skipped


def main():
    print('Creating missing tables...')
    created, skipped = create_missing_tables()
    if created:
        print('  Created:', ', '.join(created))
    else:
        print('  No new tables needed.')
    print('  Already present:', len(skipped), 'table(s)')

    print('Syncing migration records...')
    call_command('migrate', 'myapp', '--fake', verbosity=0)
    call_command('migrate', 'sessions', verbosity=0)

    import subprocess
    import sys

    print('Seeding barangays...')
    subprocess.run([sys.executable, 'seed_barangays.py'], check=True, cwd=os.path.dirname(__file__))

    print('Seeding admin accounts...')
    subprocess.run([sys.executable, 'seed_admins.py'], check=True, cwd=os.path.dirname(__file__))

    from myapp.models import SuperAdmin, Admin
    print(f'  super_admins: {SuperAdmin.objects.count()}')
    print(f'  admins:       {Admin.objects.count()}')
    print('Done. You can log in at http://localhost:8000/')


if __name__ == '__main__':
    main()
