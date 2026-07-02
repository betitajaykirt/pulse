from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0008_mitigationprotocol'),
    ]

    operations = [
        migrations.AddField(
            model_name='surveillancereport',
            name='is_anomaly',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='surveillancereport',
            name='ml_anomaly_score',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True),
        ),
    ]
