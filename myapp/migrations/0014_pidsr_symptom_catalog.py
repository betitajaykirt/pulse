from django.db import migrations


def reseed_pidsr_symptoms(apps, schema_editor):
    from myapp.symptom_data import seed_all_symptoms
    seed_all_symptoms(verbose=False)


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0013_bhw_environmentdata_healthreport_historicalrecord_and_more'),
    ]

    operations = [
        migrations.RunPython(reseed_pidsr_symptoms, migrations.RunPython.noop),
    ]
