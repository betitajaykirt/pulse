from django.db import migrations, models


def seed_symptoms(apps, schema_editor):
    from myapp.symptom_data import seed_all_symptoms
    seed_all_symptoms(verbose=False)


def unseed_symptoms(apps, schema_editor):
    Symptom = apps.get_model('myapp', 'Symptom')
    Symptom.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0006_patientcase_age_sex'),
    ]

    operations = [
        migrations.CreateModel(
            name='Symptom',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('syndromic_group', models.CharField(
                    choices=[
                        ('A', 'Group A — Systemic & Constitutional'),
                        ('B', 'Group B — Respiratory & ENT'),
                        ('C', 'Group C — Gastrointestinal & Hepatic'),
                        ('D', 'Group D — Dermatological & Specialized Triggers'),
                        ('E', 'Group E — Contextual Exposure'),
                    ],
                    max_length=1,
                )),
                ('description', models.TextField(blank=True, default='')),
            ],
            options={
                'db_table': 'symptoms',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='patientcase',
            name='symptoms',
            field=models.ManyToManyField(blank=True, related_name='cases', to='myapp.symptom'),
        ),
        migrations.RunPython(seed_symptoms, unseed_symptoms),
    ]
