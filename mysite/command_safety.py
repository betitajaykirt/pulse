"""Block seed/wipe scripts against production and shared hosted databases."""
from __future__ import annotations

import os
from pathlib import Path

ALLOW_ENV = 'ALLOW_PROD_COMMANDS'

PRODUCTION_HOST_MARKERS = (
    'hstgr.io',
    'hostinger',
    'aivencloud.com',
    'aiven.io',
    'rds.amazonaws.com',
    'azure.com',
    'cloud.google.com',
    'vercel-storage.com',
)

LOCAL_HOSTS = frozenset({'', 'localhost', '127.0.0.1', '::1'})


def _truthy(value: str | None) -> bool:
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def project_env_path() -> Path:
    return Path(__file__).resolve().parent.parent / '.env'


def load_project_env() -> None:
    env_path = project_env_path()
    if not env_path.exists():
        return
    import environ
    environ.Env.read_env(str(env_path), overwrite=False)


def production_block_reason(command_name: str) -> str | None:
    """Return a refusal message if this seed/wipe command must not run."""
    load_project_env()
    if _truthy(os.environ.get(ALLOW_ENV)):
        return None

    debug = _truthy(os.environ.get('DEBUG'))
    db_host = (os.environ.get('DB_HOST') or '').strip().lower()

    if not debug:
        return (
            f'{command_name} is blocked when DEBUG is False. '
            'Seed and wipe commands are for local/demo databases only. '
            f'Set {ALLOW_ENV}=1 only if you fully intend to run this against the current database.'
        )

    if db_host in LOCAL_HOSTS:
        return None

    if any(marker in db_host for marker in PRODUCTION_HOST_MARKERS):
        return (
            f'{command_name} is blocked for database host {db_host}. '
            'Refusing to seed or wipe a shared/production database.'
        )

    return (
        f'{command_name} is blocked for database host {db_host}. '
        'Seed and wipe commands only run against localhost. '
        f'Set {ALLOW_ENV}=1 to override.'
    )


def assert_safe_for_destructive_commands(command_name: str) -> None:
    reason = production_block_reason(command_name)
    if not reason:
        return
    try:
        from django.core.management.base import CommandError
    except ImportError:
        raise RuntimeError(reason) from None
    raise CommandError(reason)
