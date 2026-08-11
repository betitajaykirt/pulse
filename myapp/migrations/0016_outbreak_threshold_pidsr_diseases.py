from django.db import migrations


def seed_pidsr_outbreak_thresholds(apps, schema_editor):
    from myapp.threshold_data import seed_outbreak_thresholds
    seed_outbreak_thresholds(verbose=False)


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0015_outbreakthreshold_fieldtask'),
    ]

    operations = [
        migrations.RunPython(seed_pidsr_outbreak_thresholds, migrations.RunPython.noop),
    ]
