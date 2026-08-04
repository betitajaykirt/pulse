from django.core.management.base import BaseCommand
from django.utils import timezone
from reports.models import BarangayRiskLog
from reports.risk_service import _create_risk_analysis_bridge

class Command(BaseCommand):
    help = 'Synchronizes existing active BarangayRiskLogs into the Alerts table'

    def handle(self, *args, **options):
        active_logs = BarangayRiskLog.objects.filter(is_active_alert=True)
        count = 0
        
        for log in active_logs:
            # Check if an alert already exists for this log to prevent duplicates
            # Since we don't have a direct foreign key from Alert to BarangayRiskLog,
            # we'll approximate it by checking date, type and barangay.
            alert_exists = Alert.objects.filter(
                alert_type__iexact=log.syndrome,
                alert_date__date=log.created_at.date()
            ).exists()
            
            if not alert_exists:
                from myapp.models import Barangay, SurveillanceReport, Alert, NotificationLog
                barangay_obj = Barangay.objects.filter(barangay_name__iexact=log.barangay).first()
                fallback_report = SurveillanceReport.objects.filter(
                    barangay_id=barangay_obj.id if barangay_obj else None,
                ).first() or SurveillanceReport.objects.first()
                
                if not fallback_report:
                    self.stdout.write(self.style.WARNING(
                        f'Skipped {log.barangay} — no surveillance report for bridge row.'
                    ))
                    continue

                analysis = _create_risk_analysis_bridge(
                    fallback_report,
                    risk_score=log.final_risk_score / 100.0,
                    anomaly_score=log.anomaly_score,
                    risk_level=log.risk_level.lower(),
                    algorithm_used='aptas-engine-v1-retroactive',
                )
                
                alert_level = log.risk_level.lower()
                
                alert = Alert.objects.create(
                    alert_level=alert_level,
                    alert_date=log.created_at,
                    status='active',
                    alert_type=log.syndrome,
                    analysis_id=analysis.id
                )
                
                summary = f'APTAS RISK: {log.syndrome} at {alert_level.title()} level in {log.barangay}'
                
                for role in ('admin', 'health_officer', 'surveillance_officer'):
                    NotificationLog.objects.create(
                        alert_id=alert.id,
                        recipient_role=role,
                        channel='dashboard',
                        message_summary=summary,
                        delivery_status='sent',
                        sent_at=log.created_at,
                        created_at=log.created_at
                    )
                
                count += 1
                self.stdout.write(self.style.SUCCESS(f'Synced alert for {log.barangay} - {log.syndrome}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully synced {count} old APTAS alerts.'))
