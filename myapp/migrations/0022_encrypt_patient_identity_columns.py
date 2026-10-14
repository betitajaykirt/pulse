from django.db import migrations


FORWARD = """
ALTER TABLE patients
    MODIFY full_name TEXT NOT NULL;
ALTER TABLE surveillance_reports
    MODIFY patient_name TEXT NOT NULL;
ALTER TABLE patient_cases
    MODIFY patient_name TEXT NOT NULL;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0021_addeddisease'),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD, reverse_sql=migrations.RunSQL.noop),
    ]
