"""Encrypt patient identity values that are still stored in the clear."""
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from myapp.field_encryption import is_encrypted, scrub_identity_from_remarks


class Command(BaseCommand):
    help = 'Encrypt patient names, birthdates, addresses, and school fields already in the database.'

    def handle(self, *args, **options):
        self._require_text_column('patients', 'birthdate')
        from myapp.models import Patient, PatientCase, SurveillanceReport

        patients = self._rewrite(Patient, 'patients', 'patient_id', [
            'full_name', 'address', 'birthdate',
        ])
        reports = self._rewrite(
            SurveillanceReport,
            'surveillance_reports',
            'id',
            [
                'patient_name', 'detailed_address', 'school_name',
                'grade_year_section', 'date_of_birth',
            ],
            scrub_remarks=True,
        )
        cases = self._rewrite(PatientCase, 'patient_cases', 'id', [
            'patient_name', 'detailed_address', 'school_name',
            'grade_year_section', 'purok_street', 'date_of_birth',
        ])
        self.stdout.write(self.style.SUCCESS(
            f'Encrypted {patients} patient rows, {reports} reports, and {cases} case rows.'
        ))

    def _require_text_column(self, table, column):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DATA_TYPE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = %s
                  AND COLUMN_NAME = %s
                """,
                [table, column],
            )
            row = cursor.fetchone()
        if not row or row[0].lower() not in {'text', 'tinytext', 'mediumtext', 'longtext'}:
            raise CommandError(
                'Identity columns are still date or short text columns. '
                'Deploy the app so migration 0022 runs, then run this command.'
            )

    def _rewrite(self, model, table, pk_column, fields, *, scrub_remarks=False):
        columns = [pk_column, *fields]
        if scrub_remarks:
            columns.append('remarks')
        selected = ', '.join(f'`{name}`' for name in columns)
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT {selected} FROM `{table}`')
            raw_rows = cursor.fetchall()

        changed = 0
        for raw in raw_rows:
            pk = raw[0]
            values = dict(zip(columns, raw))
            needs_identity = any(_is_plaintext(values.get(field)) for field in fields)
            needs_remarks = False
            if scrub_remarks:
                scrubbed = scrub_identity_from_remarks(values.get('remarks'))
                needs_remarks = scrubbed != (values.get('remarks') or '')
            if not needs_identity and not needs_remarks:
                continue
            row = model.objects.get(pk=pk)
            if needs_remarks:
                row.remarks = scrub_identity_from_remarks(row.remarks)
            update_fields = list(fields)
            if needs_remarks:
                update_fields.append('remarks')
            row.save(update_fields=update_fields)
            changed += 1
        return changed


def _is_plaintext(value) -> bool:
    if value in (None, ''):
        return False
    if isinstance(value, (date, datetime)):
        return True
    return not is_encrypted(str(value))
