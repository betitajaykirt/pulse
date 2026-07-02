from django.db import migrations, models


def seed_mitigation_protocols(apps, schema_editor):
    from myapp.mitigation_data import seed_mitigation_protocols as run_seed
    run_seed(verbose=False)


def unseed_mitigation_protocols(apps, schema_editor):
    MitigationProtocol = apps.get_model('myapp', 'MitigationProtocol')
    MitigationProtocol.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0007_symptom_model'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='MitigationProtocol',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('disease_label', models.CharField(db_index=True, max_length=150)),
                        ('action_text', models.TextField()),
                        ('priority', models.CharField(
                            choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')],
                            default='medium',
                            max_length=10,
                        )),
                        ('action_category', models.CharField(
                            choices=[
                                ('environmental', 'Environmental'),
                                ('logistical', 'Logistical'),
                                ('medical', 'Medical'),
                                ('public_warning', 'Public Warning'),
                            ],
                            max_length=20,
                        )),
                        ('is_active', models.BooleanField(default=True)),
                        ('sort_order', models.PositiveSmallIntegerField(default=0)),
                    ],
                    options={
                        'db_table': 'mitigation_protocols',
                        'ordering': ['disease_label', '-priority', 'sort_order'],
                    },
                ),
                migrations.AddConstraint(
                    model_name='mitigationprotocol',
                    constraint=models.UniqueConstraint(
                        fields=('disease_label', 'sort_order'),
                        name='uniq_mitigation_disease_sort',
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE TABLE IF NOT EXISTS mitigation_protocols ("
                        "  id INT AUTO_INCREMENT PRIMARY KEY,"
                        "  disease_label VARCHAR(150) NOT NULL,"
                        "  action_text LONGTEXT NOT NULL,"
                        "  priority VARCHAR(10) NOT NULL DEFAULT 'medium',"
                        "  action_category VARCHAR(20) NOT NULL,"
                        "  is_active TINYINT(1) NOT NULL DEFAULT 1,"
                        "  sort_order SMALLINT UNSIGNED NOT NULL DEFAULT 0,"
                        "  INDEX mitigation_protocols_disease_label_idx (disease_label)"
                        ")"
                    ),
                    reverse_sql="DROP TABLE IF EXISTS mitigation_protocols",
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE mitigation_protocols "
                        "ADD CONSTRAINT uniq_mitigation_disease_sort "
                        "UNIQUE (disease_label, sort_order)"
                    ),
                    reverse_sql=(
                        "ALTER TABLE mitigation_protocols "
                        "DROP INDEX uniq_mitigation_disease_sort"
                    ),
                ),
            ],
        ),
        migrations.RunPython(seed_mitigation_protocols, unseed_mitigation_protocols),
    ]
