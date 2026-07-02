# Add age and sex demographics to patient_cases

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0005_batch_entry_models'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='patientcase',
                    name='age',
                    field=models.PositiveSmallIntegerField(default=0),
                    preserve_default=False,
                ),
                migrations.AddField(
                    model_name='patientcase',
                    name='sex',
                    field=models.CharField(
                        choices=[('Male', 'Male'), ('Female', 'Female')],
                        default='Male',
                        max_length=10,
                    ),
                    preserve_default=False,
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE patient_cases "
                        "ADD COLUMN age SMALLINT UNSIGNED NOT NULL DEFAULT 0, "
                        "ADD COLUMN sex VARCHAR(10) NOT NULL DEFAULT 'Male'"
                    ),
                    reverse_sql=(
                        "ALTER TABLE patient_cases "
                        "DROP COLUMN age, DROP COLUMN sex"
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE patient_cases "
                        "ALTER COLUMN age DROP DEFAULT, "
                        "ALTER COLUMN sex DROP DEFAULT"
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
