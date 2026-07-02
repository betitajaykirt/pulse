from django.db import migrations, models


DEMOGRAPHIC_COLUMNS_SQL = """
ALTER TABLE surveillance_reports
    ADD COLUMN patient_name VARCHAR(255) NOT NULL DEFAULT 'Unknown Resident',
    ADD COLUMN civil_status VARCHAR(50) NULL,
    ADD COLUMN date_of_birth DATE NULL,
    ADD COLUMN detailed_address TEXT NULL,
    ADD COLUMN is_student TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN grade_year_section VARCHAR(100) NULL,
    ADD COLUMN school_name VARCHAR(255) NULL;

ALTER TABLE patient_cases
    ADD COLUMN patient_name VARCHAR(255) NOT NULL DEFAULT 'Unknown Resident',
    ADD COLUMN civil_status VARCHAR(50) NULL,
    ADD COLUMN date_of_birth DATE NULL,
    ADD COLUMN detailed_address TEXT NULL,
    ADD COLUMN is_student TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN grade_year_section VARCHAR(100) NULL,
    ADD COLUMN school_name VARCHAR(255) NULL;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0011_log_display_names'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='patientcase',
                    name='civil_status',
                    field=models.CharField(blank=True, max_length=50, null=True),
                ),
                migrations.AddField(
                    model_name='patientcase',
                    name='date_of_birth',
                    field=models.DateField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='patientcase',
                    name='detailed_address',
                    field=models.TextField(blank=True, default=''),
                ),
                migrations.AddField(
                    model_name='patientcase',
                    name='grade_year_section',
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name='patientcase',
                    name='is_student',
                    field=models.BooleanField(default=False),
                ),
                migrations.AddField(
                    model_name='patientcase',
                    name='patient_name',
                    field=models.CharField(default='Unknown Resident', max_length=255),
                ),
                migrations.AddField(
                    model_name='patientcase',
                    name='school_name',
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
                migrations.AddField(
                    model_name='surveillancereport',
                    name='civil_status',
                    field=models.CharField(blank=True, max_length=50, null=True),
                ),
                migrations.AddField(
                    model_name='surveillancereport',
                    name='date_of_birth',
                    field=models.DateField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='surveillancereport',
                    name='detailed_address',
                    field=models.TextField(blank=True, default=''),
                ),
                migrations.AddField(
                    model_name='surveillancereport',
                    name='grade_year_section',
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
                migrations.AddField(
                    model_name='surveillancereport',
                    name='is_student',
                    field=models.BooleanField(default=False),
                ),
                migrations.AddField(
                    model_name='surveillancereport',
                    name='patient_name',
                    field=models.CharField(default='Unknown Resident', max_length=255),
                ),
                migrations.AddField(
                    model_name='surveillancereport',
                    name='school_name',
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=DEMOGRAPHIC_COLUMNS_SQL,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
