"""
Run once to seed super admin and admin accounts using Django ORM.
Usage: python seed_admins.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

import bcrypt
from django.utils import timezone
from myapp.models import SuperAdmin, Admin

def hash_pw(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

now = timezone.now()

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
if not created:
    superadmin.first_name = 'System'
    superadmin.last_name = 'Super Administrator'
    superadmin.email = 'superadmin@pulse.local'
    superadmin.password_hash = hash_pw('SuperAdmin@1234')
    superadmin.status = 'active'
    superadmin.updated_at = now
    superadmin.save()

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
if not created:
    admin.first_name = 'System'
    admin.last_name = 'Administrator'
    admin.email = 'admin@pulse.local'
    admin.password_hash = hash_pw('Admin@1234')
    admin.assigned_office = 'Bago City Health Office'
    admin.status = 'active'
    admin.updated_at = now
    admin.save()

print("Seeded super admin and admin accounts.")
