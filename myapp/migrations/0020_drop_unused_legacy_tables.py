from django.db import migrations


UNUSED_TABLES = (
    'historical_records',
    'incident_report',
    'health_report',
    'notification',
    'environment_data',
    'bhw',
    'admin',
    'super_admin',
    'ocr_results',
    'registration_requests',
)

STALE_MODELS = (
    'bhw',
    'environmentdata',
    'healthreport',
    'historicalrecord',
    'incidentreport',
    'legacyadmin',
    'legacynotification',
    'legacysuperadmin',
    'ocrresult',
    'registrationrequest',
)


def drop_unused_tables(apps, schema_editor):
    """Drop empty prototype tables. Abort if any of them has rows."""
    connection = schema_editor.connection
    quoted_models = ', '.join(['%s'] * len(STALE_MODELS))
    with connection.cursor() as cursor:
        for table in UNUSED_TABLES:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                """,
                [table],
            )
            if cursor.fetchone()[0] == 0:
                continue
            cursor.execute(f'SELECT COUNT(*) FROM `{table}`')
            count = cursor.fetchone()[0]
            if count:
                raise RuntimeError(
                    f'Refusing to drop {table}: it has {count} rows.'
                )
        for table in UNUSED_TABLES:
            cursor.execute(f'DROP TABLE IF EXISTS `{table}`')
        cursor.execute(
            f"""
            DELETE FROM auth_permission
            WHERE content_type_id IN (
                SELECT id FROM (
                    SELECT id FROM django_content_type
                    WHERE app_label = 'myapp' AND model IN ({quoted_models})
                ) AS stale_types
            )
            """,
            list(STALE_MODELS),
        )
        cursor.execute(
            f"""
            DELETE FROM django_content_type
            WHERE app_label = 'myapp' AND model IN ({quoted_models})
            """,
            list(STALE_MODELS),
        )


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0019_recommendationrevision_scope_disease'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='HistoricalRecord'),
                migrations.DeleteModel(name='IncidentReport'),
                migrations.DeleteModel(name='HealthReport'),
                migrations.DeleteModel(name='Bhw'),
                migrations.DeleteModel(name='LegacyAdmin'),
                migrations.DeleteModel(name='LegacySuperAdmin'),
                migrations.DeleteModel(name='LegacyNotification'),
                migrations.DeleteModel(name='EnvironmentData'),
                migrations.DeleteModel(name='OcrResult'),
                migrations.DeleteModel(name='RegistrationRequest'),
            ],
            database_operations=[
                migrations.RunPython(drop_unused_tables, migrations.RunPython.noop),
            ],
        ),
    ]
