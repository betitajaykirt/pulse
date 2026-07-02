# Adds patient_id FK column to surveillance_reports (pulse_db)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0002_add_pulse_session'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE surveillance_reports "
                "ADD COLUMN patient_id INT NULL, "
                "ADD CONSTRAINT fk_surveillance_reports_patient "
                "FOREIGN KEY (patient_id) REFERENCES patients(patient_id) "
                "ON DELETE SET NULL"
            ),
            reverse_sql=(
                "ALTER TABLE surveillance_reports "
                "DROP FOREIGN KEY fk_surveillance_reports_patient, "
                "DROP COLUMN patient_id"
            ),
        ),
    ]
