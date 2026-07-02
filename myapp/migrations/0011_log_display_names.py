from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0010_disease_category_thresholds'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='systemlog',
                    name='user_display_name',
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
                migrations.AddField(
                    model_name='auditlog',
                    name='actor_display_name',
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE system_logs "
                        "ADD COLUMN user_display_name VARCHAR(255) NULL"
                    ),
                    reverse_sql=(
                        "ALTER TABLE system_logs "
                        "DROP COLUMN user_display_name"
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE audit_logs "
                        "ADD COLUMN actor_display_name VARCHAR(255) NULL"
                    ),
                    reverse_sql=(
                        "ALTER TABLE audit_logs "
                        "DROP COLUMN actor_display_name"
                    ),
                ),
            ],
        ),
    ]
