"""Seed 1 catchment nurse and 2 BHWs for each of Bago City's 24 barangays."""
from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.auth_utils import hash_password
from myapp.models import Barangay, User


# Realistic Negrense / Visayan names — fictional demo staff only.
# 1 catchment nurse + 2 BHWs per official Bago City barangay.
DEMO_STAFF = {
    'Abuanan': {
        'nurse': ('Rowena', 'P', 'Magbanua'),
        'bhw': (('Jocelyn', 'S', 'Villanueva'), ('Reynaldo', 'T', 'Gatuslao')),
    },
    'Alianza': {
        'nurse': ('Maricel', 'A', 'Torres'),
        'bhw': (('Analyn', 'B', 'Jalandoni'), ('Ernesto', 'C', 'Lizares')),
    },
    'Atipuluan': {
        'nurse': ('Cherry Mae', 'D', 'Guanzon'),
        'bhw': (('Fe', 'H', 'Lacson'), ('Joel', 'M', 'Benedicto')),
    },
    'Balingasag': {
        'nurse': ('Liza', 'R', 'Montinola'),
        'bhw': (('Rosario', 'V', 'Yulo'), ('Armando', 'K', 'Henares')),
    },
    'Binubuhan': {
        'nurse': ('Angelica', 'N', 'Locsin'),
        'bhw': (('Carmen', 'L', 'Araneta'), ('Nestor', 'P', 'Treyes')),
    },
    'Busay': {
        'nurse': ('Katrina', 'S', 'Puentevella'),
        'bhw': (('Gloria', 'F', 'Zayco'), ('Ramon', 'D', 'Miraflores')),
    },
    'Calumangan': {
        'nurse': ('Patricia', 'G', 'Ledesma'),
        'bhw': (('Helen', 'J', 'Villanueva'), ('Oscar', 'I', 'Guanzon')),
    },
    'Caridad': {
        'nurse': ('Michelle', 'E', 'Dela Cruz'),
        'bhw': (('Sonia', 'W', 'Magbanua'), ('Vicente', 'Q', 'Torres')),
    },
    'Dulao': {
        'nurse': ('Aileen', 'C', 'Jalandoni'),
        'bhw': (('Myrna', 'K', 'Gatuslao'), ('Francisco', 'B', 'Lizares')),
    },
    'Ilijan': {
        'nurse': ('Grace', 'U', 'Benedicto'),
        'bhw': (('Teresa', 'A', 'Yulo'), ('Danilo', 'R', 'Henares')),
    },
    'Lag-asan': {
        'nurse': ('Josephine', 'M', 'Locsin'),
        'bhw': (('Evelyn', 'S', 'Araneta'), ('Ricardo', 'T', 'Montinola')),
    },
    'Ma-ao': {
        'nurse': ('Bernadette', 'L', 'Lacson'),
        'bhw': (('Imelda', 'P', 'Zayco'), ('Alfredo', 'V', 'Puentevella')),
    },
    'Mailum': {
        'nurse': ('Cristina', 'H', 'Miraflores'),
        'bhw': (('Luzviminda', 'D', 'Ledesma'), ('Mario', 'F', 'Dela Cruz')),
    },
    'Malingin': {
        'nurse': ('Stephanie', 'J', 'Villanueva'),
        'bhw': (('Corazon', 'N', 'Guanzon'), ('Eduardo', 'S', 'Magbanua')),
    },
    'Napoles': {
        'nurse': ('Vanessa', 'K', 'Torres'),
        'bhw': (('Remedios', 'B', 'Jalandoni'), ('Rogelio', 'C', 'Gatuslao')),
    },
    'Pacol': {
        'nurse': ('Dianne', 'R', 'Lizares'),
        'bhw': (('Estrella', 'E', 'Benedicto'), ('Teodoro', 'A', 'Yulo')),
    },
    'Poblacion': {
        'nurse': ('Fatima', 'G', 'Henares'),
        'bhw': (('Consuelo', 'I', 'Locsin'), ('Benjamin', 'M', 'Araneta')),
    },
    'Sagasa': {
        'nurse': ('Lorna', 'P', 'Montinola'),
        'bhw': (('Milagros', 'T', 'Lacson'), ('Rodolfo', 'V', 'Zayco')),
    },
    'Sampinit': {
        'nurse': ('Hazel', 'D', 'Puentevella'),
        'bhw': (('Aurora', 'F', 'Miraflores'), ('Generoso', 'L', 'Ledesma')),
    },
    'Bacong-Montilla': {
        'nurse': ('Irene', 'S', 'Dela Cruz'),
        'bhw': (('Pilar', 'H', 'Villanueva'), ('Cesar', 'N', 'Guanzon')),
    },
    'Bagroy': {
        'nurse': ('Claudine', 'B', 'Magbanua'),
        'bhw': (('Juliana', 'C', 'Torres'), ('Manuel', 'J', 'Jalandoni')),
    },
    'Don Jorge Araneta': {
        'nurse': ('Elaine', 'A', 'Gatuslao'),
        'bhw': (('Norma', 'E', 'Lizares'), ('Roberto', 'K', 'Benedicto')),
    },
    'Tabunan': {
        'nurse': ('Sheila', 'V', 'Yulo'),
        'bhw': (('Leticia', 'R', 'Henares'), ('Antonio', 'I', 'Locsin')),
    },
    'Taloc': {
        'nurse': ('Winnie', 'M', 'Araneta'),
        'bhw': (('Perla', 'G', 'Montinola'), ('Isidro', 'P', 'Lacson')),
    },
}


def barangay_slug(name: str) -> str:
    return (
        name.lower()
        .replace('-', '')
        .replace(' ', '')
    )


def name_token(value: str) -> str:
    return value.lower().replace('.', '').replace(' ', '').replace('-', '')


def build_email(first: str, last: str, barangay: str) -> str:
    return f'{name_token(first)}.{name_token(last)}.{barangay_slug(barangay)}@pulse-bago.demo'


def build_username(first: str, last: str, barangay: str, role_code: str) -> str:
    return f'{name_token(first)}.{name_token(last)}.{barangay_slug(barangay)}.{role_code}'[:100]


def password_slug(name: str) -> str:
    return ''.join(part.title() for part in name.replace('-', ' ').split())


def build_password(barangay: str, role_code: str) -> str:
    return f'Pulse@{password_slug(barangay)}{role_code}26'


def build_contact(index: int) -> str:
    return f'0917{1000000 + index}'[0:11]


class Command(BaseCommand):
    help = 'Create demo catchment nurse and BHW accounts for all 24 Bago City barangays.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-passwords',
            action='store_true',
            help='Update password/name/barangay for existing demo emails instead of skipping them.',
        )

        parser.add_argument(
            '--purge-unmapped',
            action='store_true',
            help='Delete leftover demo accounts whose barangay is not in the current roster.',
        )

    def handle(self, *args, **options):
        reset = bool(options.get('reset_passwords'))
        purge = bool(options.get('purge_unmapped'))
        now = timezone.now()
        created = 0
        updated = 0
        skipped = 0
        purged = 0
        rows = []
        contact_index = 1

        db_barangays = {b.barangay_name: b for b in Barangay.objects.all()}
        missing = [name for name in DEMO_STAFF if name not in db_barangays]
        if missing:
            self.stdout.write(self.style.WARNING(
                f'Barangay name mismatch (accounts still use roster names): {", ".join(missing)}'
            ))

        roster_emails = set()
        for barangay, staff in DEMO_STAFF.items():
            nurse = staff['nurse']
            roster_emails.add(build_email(nurse[0], nurse[2], barangay))
            for person in staff['bhw']:
                roster_emails.add(build_email(person[0], person[2], barangay))

        if purge:
            stale = User.objects.filter(email__iendswith='@pulse-bago.demo').exclude(
                email__in=roster_emails
            )
            purged = stale.count()
            stale.delete()

        for barangay, staff in DEMO_STAFF.items():
            people = [
                ('catchment_nurse', 'CN', 'Catchment Nurse (OIC)', staff['nurse']),
                ('barangay_health_worker', 'B1', 'Barangay Health Worker', staff['bhw'][0]),
                ('barangay_health_worker', 'B2', 'Barangay Health Worker', staff['bhw'][1]),
            ]
            for role, role_code, designation, person in people:
                first, middle, last = person
                email = build_email(first, last, barangay)
                username = build_username(first, last, barangay, role_code.lower())
                password = build_password(barangay, role_code)
                contact = build_contact(contact_index)
                contact_index += 1

                payload = {
                    'username': username,
                    'first_name': first,
                    'last_name': last,
                    'middle_name': middle,
                    'email': email,
                    'contact_number': contact,
                    'password_hash': hash_password(password),
                    'role': role,
                    'designation': designation,
                    'region_text': 'Western Visayas',
                    'province_text': 'Negros Occidental',
                    'city_text': 'Bago City',
                    'barangay_text': barangay,
                    'status': 'active',
                    'first_login': False,
                    'updated_at': now,
                }

                existing = User.objects.filter(email__iexact=email).first()
                if existing:
                    if reset:
                        User.objects.filter(id=existing.id).update(**{
                            k: v for k, v in payload.items() if k != 'username'
                        })
                        updated += 1
                        action = 'updated'
                    else:
                        skipped += 1
                        action = 'exists'
                        password = '(unchanged — use --reset-passwords to overwrite)'
                else:
                    if User.objects.filter(username=username).exists():
                        username = f'{username}.{role_code.lower()}'
                        payload['username'] = username
                    User.objects.create(created_at=now, **payload)
                    created += 1
                    action = 'created'

                rows.append({
                    'barangay': barangay,
                    'role': designation,
                    'name': f'{first} {middle}. {last}',
                    'email': email,
                    'password': password if action != 'exists' else build_password(barangay, role_code),
                    'contact': contact,
                    'action': action,
                })

        csv_path = Path(settings.BASE_DIR) / 'demo_account_credentials.csv'
        with csv_path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=['barangay', 'role', 'name', 'email', 'password', 'contact', 'action'],
            )
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(
            f'Demo accounts — created {created}, updated {updated}, skipped {skipped}, purged {purged}.'
        ))
        self.stdout.write(f'Credentials CSV: {csv_path}')
        self.stdout.write('')
        self.stdout.write(f'{"Barangay":<14} {"Role":<24} {"Name":<28} Email / Password')
        self.stdout.write('-' * 110)
        for row in rows:
            self.stdout.write(
                f'{row["barangay"]:<14} {row["role"]:<24} {row["name"]:<28} {row["email"]}  /  {row["password"]}'
            )
