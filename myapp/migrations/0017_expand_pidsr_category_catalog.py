from django.db import migrations


def expand_pidsr_category_catalog(apps, schema_editor):
    from myapp.symptom_data import seed_all_symptoms
    from myapp.threshold_data import seed_outbreak_thresholds

    seed_all_symptoms(verbose=False)
    seed_outbreak_thresholds(verbose=False)


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0016_outbreak_threshold_pidsr_diseases'),
    ]

    operations = [
        migrations.RunPython(expand_pidsr_category_catalog, migrations.RunPython.noop),
    ]
