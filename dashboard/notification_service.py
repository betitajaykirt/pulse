"""Filter and prune dashboard alert popups tied to live surveillance cases."""

from __future__ import annotations

from django.db.models import Q

from myapp.models import Alert, Barangay, SurveillanceReport
from reports.aptas_service import ACTIVE_SURVEILLANCE_STATUSES, _syndrome_match_q


def _active_alert_ids() -> set[int]:
    return set(Alert.objects.filter(status='active').values_list('id', flat=True))


def notification_is_still_relevant(notif, active_alert_ids: set[int] | None = None) -> bool:
    """Return True only when the linked alert and open cases still warrant a popup."""
    if active_alert_ids is None:
        active_alert_ids = _active_alert_ids()

    if notif.alert_id and notif.alert_id not in active_alert_ids:
        return False

    barangay = Barangay.objects.filter(barangay_name__iexact=notif.barangay_name).first()
    if not barangay:
        return False

    qs = SurveillanceReport.objects.filter(
        barangay_id=barangay.id,
        status__in=ACTIVE_SURVEILLANCE_STATUSES,
    )
    from reports.ml_display import is_alertable_disease_label

    disease = (notif.disease or '').strip()
    if not is_alertable_disease_label(disease):
        return False
    if disease:
        qs = qs.filter(_syndrome_match_q(disease))
    return qs.exists()


def relevant_app_notifications(queryset, *, limit: int = 20):
    """Return recent notifications that still map to active surveillance."""
    active_ids = _active_alert_ids()
    relevant = []
    for notif in queryset.order_by('-created_at')[: max(limit * 3, 30)]:
        if notification_is_still_relevant(notif, active_ids):
            relevant.append(notif)
        if len(relevant) >= limit:
            break
    return relevant


def dismiss_app_notifications(*, alert_ids=None, barangay_name=None, disease=None) -> int:
    """Remove stale popup rows when alerts are resolved or cases are closed."""
    from dashboard.models import AppNotification

    qs = AppNotification.objects.all()
    if alert_ids:
        deleted, _ = qs.filter(alert_id__in=alert_ids).delete()
        return deleted

    if barangay_name:
        qs = qs.filter(barangay_name__iexact=barangay_name)
    if disease:
        qs = qs.filter(Q(disease__iexact=disease) | Q(disease__icontains=disease))

    stale_ids = [
        notif.id for notif in qs
        if not notification_is_still_relevant(notif)
    ]
    if not stale_ids:
        return 0
    deleted, _ = AppNotification.objects.filter(id__in=stale_ids).delete()
    return deleted


def prune_stale_app_notifications(scan_limit: int = 100) -> int:
    """Delete historical popup rows that no longer have open cases."""
    from dashboard.models import AppNotification

    active_ids = _active_alert_ids()
    stale_ids = [
        notif.id
        for notif in AppNotification.objects.order_by('-created_at')[:scan_limit]
        if not notification_is_still_relevant(notif, active_ids)
    ]
    if not stale_ids:
        return 0
    deleted, _ = AppNotification.objects.filter(id__in=stale_ids).delete()
    return deleted
