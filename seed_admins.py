"""
Run once to seed super admin and admin accounts using Django ORM.
Usage: python seed_admins.py

Blocked against production/shared databases unless ALLOW_PROD_COMMANDS=1.
Existing accounts are left unchanged so this cannot reset live passwords.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from mysite.command_safety import assert_safe_for_destructive_commands, load_project_env

load_project_env()
assert_safe_for_destructive_commands('seed_admins.py')

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

import bcrypt
from django.utils import timezone
from myapp.models import SuperAdmin, Admin


def hash_pw(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def main():
    now = timezone.now()
    created_labels = []

    superadmin, created = SuperAdmin.objects.get_or_create(
        username='superadmin',
        defaults={
            'first_name': 'System',
            'last_name': 'Super Administrator',
            'email': 'superadmin@pulse.local',
            'password_hash': hash_pw('SuperAdmin@1234'),
            'status': 'active',
            'created_at': now,
            'updated_at': now,
        }
    )
    created_labels.append(f'superadmin ({"created" if created else "exists"})')

    admin, created = Admin.objects.get_or_create(
        username='admin',
        defaults={
            'first_name': 'System',
            'last_name': 'Administrator',
            'email': 'admin@pulse.local',
            'password_hash': hash_pw('Admin@1234'),
            'assigned_office': 'Bago City Health Office',
            'status': 'active',
            'created_at': now,
            'updated_at': now,
        }
    )
    created_labels.append(f'admin ({"created" if created else "exists"})')

    print('Seeded super admin and admin accounts:', ', '.join(created_labels))


if __name__ == '__main__':
    main()
