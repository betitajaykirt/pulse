from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0020_drop_unused_legacy_tables'),
    ]

    operations = [
        migrations.CreateModel(
            name='AddedDisease',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('category', models.CharField(choices=[('Category 1', 'Category I'), ('Category 2', 'Category II')], max_length=12)),
                ('symptom_codes', models.JSONField(blank=True, default=list)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'added_diseases',
                'ordering': ['name'],
            },
        ),
    ]
