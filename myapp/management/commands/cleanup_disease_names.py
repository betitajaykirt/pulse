from django.core.management.base import BaseCommand
from django.db import transaction

# Import all models that might store the disease name
from myapp.models import Alert, SurveillanceReport, MlAiPrediction
from dashboard.models import AppNotification
from reports.models import BarangayRiskLog


class Command(BaseCommand):
    help = 'Normalizes legacy disease names in the database (e.g., Dengue -> Dengue Fever)'

    def handle(self, *args, **kwargs):
        old_name = 'Dengue'
        new_name = 'Dengue Fever'
        
        self.stdout.write(self.style.WARNING(f'Starting disease name cleanup: "{old_name}" -> "{new_name}"'))
        
        with transaction.atomic():
            # SurveillanceReport
            reports_syndrome = SurveillanceReport.objects.filter(syndrome_type=old_name).update(syndrome_type=new_name)
            reports_suspected = SurveillanceReport.objects.filter(suspected_disease=old_name).update(suspected_disease=new_name)
            self.stdout.write(f"Updated {reports_syndrome + reports_suspected} SurveillanceReport records.")

            # Alert
            alerts = Alert.objects.filter(alert_type=old_name).update(alert_type=new_name)
            self.stdout.write(f"Updated {alerts} Alert records.")

            # AppNotification
            notifications = AppNotification.objects.filter(disease=old_name).update(disease=new_name)
            self.stdout.write(f"Updated {notifications} AppNotification records.")

            # BarangayRiskLog
            risk_logs = BarangayRiskLog.objects.filter(syndrome=old_name).update(syndrome=new_name)
            self.stdout.write(f"Updated {risk_logs} BarangayRiskLog records.")

            # MlAiPrediction
            ml_preds = MlAiPrediction.objects.filter(disease_type=old_name).update(disease_type=new_name)
            self.stdout.write(f"Updated {ml_preds} MlAiPrediction records.")

        self.stdout.write(self.style.SUCCESS(f'Successfully completed disease name normalization.'))
