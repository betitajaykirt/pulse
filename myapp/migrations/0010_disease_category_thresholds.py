from django.db import migrations, models
import django.db.models.deletion


def seed_default_thresholds(apps, schema_editor):
    DiseaseCategoryThreshold = apps.get_model('myapp', 'DiseaseCategoryThreshold')
    rows = [
        {
            'category_level': 'Category 1',
            'warning_threshold': 1,
            'outbreak_threshold': 1,
            'time_window_days': 7,
            'is_active': True,
        },
        {
            'category_level': 'Category 2',
            'warning_threshold': 2,
            'outbreak_threshold': 3,
            'time_window_days': 7,
            'is_active': True,
        },
    ]
    for row in rows:
        DiseaseCategoryThreshold.objects.update_or_create(
            category_level=row['category_level'],
            defaults=row,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0009_surveillancereport_ml_flags'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='surveillancereport',
                    name='epidemic_threshold_status',
                    field=models.CharField(blank=True, default='', max_length=32),
                ),
                migrations.CreateModel(
                    name='DiseaseCategoryThreshold',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('category_level', models.CharField(max_length=32, unique=True)),
                        ('warning_threshold', models.PositiveSmallIntegerField(default=2)),
                        ('outbreak_threshold', models.PositiveSmallIntegerField(default=3)),
                        ('time_window_days', models.PositiveSmallIntegerField(default=7)),
                        ('is_active', models.BooleanField(default=True)),
                    ],
                    options={
                        'db_table': 'disease_category_thresholds',
                        'ordering': ['category_level'],
                    },
                ),
                migrations.CreateModel(
                    name='BarangayEpidemicStatus',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('disease_label', models.CharField(max_length=150)),
                        ('pidsr_category', models.CharField(max_length=32)),
                        ('threshold_status', models.CharField(max_length=32)),
                        ('confirmed_count', models.PositiveSmallIntegerField(default=0)),
                        ('evaluated_at', models.DateTimeField()),
                        ('barangay', models.ForeignKey(
                            db_column='barangay_id',
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='epidemic_statuses',
                            to='myapp.barangay',
                        )),
                    ],
                    options={
                        'db_table': 'barangay_epidemic_statuses',
                    },
                ),
                migrations.CreateModel(
                    name='OutbreakThresholdLog',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('disease_label', models.CharField(max_length=150)),
                        ('pidsr_category', models.CharField(max_length=32)),
                        ('confirmed_count', models.PositiveSmallIntegerField(default=0)),
                        ('threshold_status', models.CharField(max_length=32)),
                        ('warning_threshold', models.PositiveSmallIntegerField(blank=True, null=True)),
                        ('outbreak_threshold', models.PositiveSmallIntegerField(blank=True, null=True)),
                        ('time_window_days', models.PositiveSmallIntegerField(default=7)),
                        ('actor_id', models.PositiveSmallIntegerField(blank=True, null=True)),
                        ('created_at', models.DateTimeField()),
                        ('barangay', models.ForeignKey(
                            db_column='barangay_id',
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            to='myapp.barangay',
                        )),
                        ('report', models.ForeignKey(
                            blank=True,
                            db_column='report_id',
                            null=True,
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            to='myapp.surveillancereport',
                        )),
                    ],
                    options={
                        'db_table': 'outbreak_threshold_logs',
                        'ordering': ['-created_at'],
                    },
                ),
                migrations.AddConstraint(
                    model_name='barangayepidemicstatus',
                    constraint=models.UniqueConstraint(
                        fields=('barangay', 'disease_label'),
                        name='uniq_barangay_disease_epidemic_status',
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE surveillance_reports "
                        "ADD COLUMN IF NOT EXISTS epidemic_threshold_status VARCHAR(32) NOT NULL DEFAULT ''"
                    ),
                    reverse_sql=(
                        "ALTER TABLE surveillance_reports "
                        "DROP COLUMN epidemic_threshold_status"
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        "CREATE TABLE IF NOT EXISTS disease_category_thresholds ("
                        "  id INT AUTO_INCREMENT PRIMARY KEY,"
                        "  category_level VARCHAR(32) NOT NULL UNIQUE,"
                        "  warning_threshold SMALLINT UNSIGNED NOT NULL DEFAULT 2,"
                        "  outbreak_threshold SMALLINT UNSIGNED NOT NULL DEFAULT 3,"
                        "  time_window_days SMALLINT UNSIGNED NOT NULL DEFAULT 7,"
                        "  is_active TINYINT(1) NOT NULL DEFAULT 1"
                        ")"
                    ),
                    reverse_sql="DROP TABLE IF EXISTS disease_category_thresholds",
                ),
                migrations.RunSQL(
                    sql=(
                        "CREATE TABLE IF NOT EXISTS barangay_epidemic_statuses ("
                        "  id INT AUTO_INCREMENT PRIMARY KEY,"
                        "  barangay_id INT NOT NULL,"
                        "  disease_label VARCHAR(150) NOT NULL,"
                        "  pidsr_category VARCHAR(32) NOT NULL,"
                        "  threshold_status VARCHAR(32) NOT NULL,"
                        "  confirmed_count SMALLINT UNSIGNED NOT NULL DEFAULT 0,"
                        "  evaluated_at DATETIME(6) NOT NULL"
                        ")"
                    ),
                    reverse_sql="DROP TABLE IF EXISTS barangay_epidemic_statuses",
                ),
                migrations.RunSQL(
                    sql=(
                        "CREATE TABLE IF NOT EXISTS outbreak_threshold_logs ("
                        "  id INT AUTO_INCREMENT PRIMARY KEY,"
                        "  barangay_id INT NOT NULL,"
                        "  report_id INT NULL,"
                        "  disease_label VARCHAR(150) NOT NULL,"
                        "  pidsr_category VARCHAR(32) NOT NULL,"
                        "  confirmed_count SMALLINT UNSIGNED NOT NULL DEFAULT 0,"
                        "  threshold_status VARCHAR(32) NOT NULL,"
                        "  warning_threshold SMALLINT UNSIGNED NULL,"
                        "  outbreak_threshold SMALLINT UNSIGNED NULL,"
                        "  time_window_days SMALLINT UNSIGNED NOT NULL DEFAULT 7,"
                        "  actor_id INT UNSIGNED NULL,"
                        "  created_at DATETIME(6) NOT NULL"
                        ")"
                    ),
                    reverse_sql="DROP TABLE IF EXISTS outbreak_threshold_logs",
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE barangay_epidemic_statuses "
                        "ADD CONSTRAINT uniq_barangay_disease_epidemic_status "
                        "UNIQUE (barangay_id, disease_label)"
                    ),
                    reverse_sql=(
                        "ALTER TABLE barangay_epidemic_statuses "
                        "DROP INDEX uniq_barangay_disease_epidemic_status"
                    ),
                ),
            ],
        ),
        migrations.RunPython(seed_default_thresholds, migrations.RunPython.noop),
    ]
