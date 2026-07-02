# Generated migration — adds case verification status to surveillance_reports

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0003_surveillance_report_patient_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='surveillancereport',
            name='status',
            field=models.CharField(
                choices=[
                    ('Suspected', 'Suspected'),
                    ('Probable', 'Probable'),
                    ('Confirmed', 'Confirmed'),
                    ('Discarded', 'Discarded'),
                ],
                default='Suspected',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='surveillancereport',
            name='confirmed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
