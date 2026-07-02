# Batch entry tables — RunSQL to match legacy barangay_id / report PK columns

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0004_surveillancereport_status'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='SurveillanceSession',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('case_classification', models.CharField(default='suspected', max_length=10)),
                        ('syndrome_type', models.CharField(max_length=150)),
                        ('source_type', models.CharField(default='BHW', max_length=20)),
                        ('patient_count', models.PositiveIntegerField(default=1)),
                        ('session_date', models.DateTimeField()),
                        ('created_at', models.DateTimeField()),
                        ('updated_at', models.DateTimeField()),
                        ('submitted_by', models.ForeignKey(
                            db_column='submitted_by', on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name='surveillance_sessions', to='myapp.user',
                        )),
                    ],
                    options={'db_table': 'surveillance_sessions'},
                ),
                migrations.AddField(
                    model_name='surveillancereport',
                    name='session',
                    field=models.ForeignKey(
                        blank=True, db_column='session_id', null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name='surveillance_reports', to='myapp.surveillancesession',
                    ),
                ),
                migrations.CreateModel(
                    name='PatientCase',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('sequence_no', models.PositiveIntegerField(default=1)),
                        ('purok_street', models.TextField()),
                        ('latitude', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                        ('longitude', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                        ('date_of_onset', models.DateField(blank=True, null=True)),
                        ('symptoms_json', models.TextField()),
                        ('fever_duration', models.PositiveSmallIntegerField(blank=True, null=True)),
                        ('created_at', models.DateTimeField()),
                        ('barangay', models.ForeignKey(
                            db_column='barangay_id', on_delete=django.db.models.deletion.DO_NOTHING, to='myapp.barangay',
                        )),
                        ('session', models.ForeignKey(
                            db_column='session_id', on_delete=django.db.models.deletion.CASCADE,
                            related_name='patient_cases', to='myapp.surveillancesession',
                        )),
                        ('surveillance_report', models.ForeignKey(
                            blank=True, db_column='report_id', null=True,
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name='patient_case', to='myapp.surveillancereport',
                        )),
                    ],
                    options={'db_table': 'patient_cases'},
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE TABLE IF NOT EXISTS surveillance_sessions ("
                        "  id INT AUTO_INCREMENT PRIMARY KEY,"
                        "  submitted_by INT NOT NULL,"
                        "  case_classification VARCHAR(10) NOT NULL DEFAULT 'suspected',"
                        "  syndrome_type VARCHAR(150) NOT NULL,"
                        "  source_type VARCHAR(20) NOT NULL DEFAULT 'BHW',"
                        "  patient_count INT UNSIGNED NOT NULL DEFAULT 1,"
                        "  session_date DATETIME NOT NULL,"
                        "  created_at DATETIME NOT NULL,"
                        "  updated_at DATETIME NOT NULL"
                        ")"
                    ),
                    reverse_sql="DROP TABLE IF EXISTS patient_cases; DROP TABLE IF EXISTS surveillance_sessions;",
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE surveillance_reports "
                        "ADD COLUMN session_id INT NULL"
                    ),
                    reverse_sql=(
                        "ALTER TABLE surveillance_reports DROP COLUMN session_id"
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        "CREATE TABLE IF NOT EXISTS patient_cases ("
                        "  id INT AUTO_INCREMENT PRIMARY KEY,"
                        "  session_id INT NOT NULL,"
                        "  barangay_id INT NOT NULL,"
                        "  report_id INT NULL,"
                        "  sequence_no INT UNSIGNED NOT NULL DEFAULT 1,"
                        "  purok_street TEXT NOT NULL,"
                        "  latitude DECIMAL(10,7) NULL,"
                        "  longitude DECIMAL(10,7) NULL,"
                        "  date_of_onset DATE NULL,"
                        "  symptoms_json TEXT NOT NULL,"
                        "  fever_duration SMALLINT UNSIGNED NULL,"
                        "  created_at DATETIME NOT NULL"
                        ")"
                    ),
                    reverse_sql="DROP TABLE IF EXISTS patient_cases",
                ),
            ],
        ),
    ]
