"""Encrypt patient names that are still stored in the clear."""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from myapp.field_encryption import is_encrypted, scrub_identity_from_remarks


class Command(BaseCommand):
    help = 'Encrypt patient names on patients, surveillance reports, and patient cases.'

    def handle(self, *args, **options):
        self._require_text_column('patient_cases', 'patient_name')
        from myapp.models import Patient, PatientCase, SurveillanceReport

        patients = self._rewrite(Patient, 'patients', 'patient_id', ['full_name'])
        reports = self._rewrite(
            SurveillanceReport,
            'surveillance_reports',
            'id',
            ['patient_name'],
            scrub_remarks=True,
        )
        cases = self._rewrite(PatientCase, 'patient_cases', 'id', ['patient_name'])
        self.stdout.write(self.style.SUCCESS(
            f'Encrypted names on {patients} patients, {reports} reports, and {cases} case rows.'
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
                'The patient name column is still too short for encrypted text. '
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
            needs_name = any(_is_plaintext(values.get(field)) for field in fields)
            needs_remarks = False
            if scrub_remarks:
                scrubbed = scrub_identity_from_remarks(values.get('remarks'))
                needs_remarks = scrubbed != (values.get('remarks') or '')
            if not needs_name and not needs_remarks:
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
    return not is_encrypted(str(value))
