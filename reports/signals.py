"""Signal handlers for surveillance case lifecycle events."""
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from myapp.models import SurveillanceReport


@receiver(pre_delete, sender=SurveillanceReport)
def reconcile_after_report_delete(sender, instance, **kwargs):
    """Re-resolve alerts and reset APTAS when a surveillance report is deleted."""
    if not instance.barangay_id:
        return
    from reports.case_state_service import handle_case_state_change

    handle_case_state_change(
        barangay_id=instance.barangay_id,
        syndrome=(instance.syndrome_type or instance.suspected_disease or '').strip(),
        trigger_report_id=instance.id,
    )
