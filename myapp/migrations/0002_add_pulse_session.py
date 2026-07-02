# Generated manually for PulseSession (maps to existing pulse_db.sessions table)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PulseSession',
            fields=[
                ('id', models.CharField(max_length=128, primary_key=True, serialize=False)),
                ('user_id', models.PositiveIntegerField()),
                ('user_type', models.CharField(
                    choices=[
                        ('super_admin', 'Super Admin'),
                        ('admin', 'Admin'),
                        ('user', 'User'),
                    ],
                    default='user',
                    max_length=15,
                )),
                ('ip_address', models.CharField(blank=True, max_length=45, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=500, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('invalidated', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'sessions',
            },
        ),
    ]
