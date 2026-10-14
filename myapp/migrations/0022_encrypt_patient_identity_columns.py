from django.db import migrations


FORWARD = """
ALTER TABLE patients
    MODIFY full_name TEXT NOT NULL,
    MODIFY address TEXT NOT NULL,
    MODIFY birthdate TEXT NOT NULL;
ALTER TABLE surveillance_reports
    MODIFY patient_name TEXT NOT NULL,
    MODIFY date_of_birth TEXT NULL,
    MODIFY detailed_address TEXT NULL,
    MODIFY school_name TEXT NULL,
    MODIFY grade_year_section TEXT NULL;
ALTER TABLE patient_cases
    MODIFY patient_name TEXT NOT NULL,
    MODIFY date_of_birth TEXT NULL,
    MODIFY detailed_address TEXT NULL,
    MODIFY school_name TEXT NULL,
    MODIFY grade_year_section TEXT NULL,
    MODIFY purok_street TEXT NOT NULL;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0021_addeddisease'),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD, reverse_sql=migrations.RunSQL.noop),
    ]
