"""
Reconcile alerts, epidemic status, and APTAS scores when surveillance cases close or are removed.
"""
from __future__ import annotations

import logging
from typing import Optional

from django.db.models import Q
from django.utils import timezone

from myapp.models import (
    Alert,
    Barangay,
    BarangayEpidemicStatus,
    NotificationLog,
    OutbreakThresholdLog,
    SurveillanceReport,
)
from myapp.threshold_data import resolve_pidsr_category
from reports.aptas_service import (
    ACTIVE_SURVEILLANCE_STATUSES,
    canonical_barangay_name,
    recalculate_aptas_for_barangay,
    reset_aptas_risk_for_barangay_syndrome,
    _syndrome_match_q,
)
from reports.threshold_service import (
    THRESHOLD_STATUS_OUTBREAK,
    THRESHOLD_STATUS_PROBABLE,
    evaluate_confirmed_thresholds,
)

logger = logging.getLogger(__name__)

ACTIVE_PROBABLE_CONFIRMED_STATUSES = ('Probable', 'Confirmed')

OUTBREAK_THRESHOLD_STATUSES = frozenset({
    THRESHOLD_STATUS_PROBABLE,
    THRESHOLD_STATUS_OUTBREAK,
    'CRITICAL_OUTBREAK',
})


def count_active_probable_confirmed(barangay_id: int, syndrome_name: str | None = None) -> int:
    """Count open Probable and Confirmed cases (excludes Closed / Discarded)."""
    qs = SurveillanceReport.objects.filter(
        barangay_id=barangay_id,
        status__in=ACTIVE_PROBABLE_CONFIRMED_STATUSES,
    )
    syndrome_q = _syndrome_match_q(syndrome_name or '')
    if syndrome_q:
        qs = qs.filter(syndrome_q)
    return qs.count()


def count_active_surveillance_cases(barangay_id: int, syndrome_name: str | None = None) -> int:
    """Count open Probable, Confirmed, and Suspected cases."""
    qs = SurveillanceReport.objects.filter(
        barangay_id=barangay_id,
        status__in=ACTIVE_SURVEILLANCE_STATUSES,
    )
    syndrome_q = _syndrome_match_q(syndrome_name or '')
    if syndrome_q:
        qs = qs.filter(syndrome_q)
    return qs.count()


def resolve_alerts_for_barangay_syndrome(barangay_name: str, syndrome_name: str) -> int:
    """
    Mark active dashboard alerts as resolved for a barangay + syndrome pair.

    Matches legacy ``Alert`` rows via ``NotificationLog`` summaries and
    ``AppNotification`` barangay/disease links.
    """
    barangay = canonical_barangay_name(barangay_name)
    syndrome = (syndrome_name or '').strip()
    if not barangay:
        return 0

    alert_ids: set[int] = set()

    notif_q = Q(barangay_name__iexact=barangay)
    if syndrome:
        notif_q &= Q(disease__iexact=syndrome) | Q(disease__icontains=syndrome)
    try:
        from dashboard.models import AppNotification

        alert_ids.update(
            AppNotification.objects.filter(notif_q)
            .exclude(alert_id__isnull=True)
            .values_list('alert_id', flat=True)
        )
    except Exception:
        logger.debug('AppNotification lookup skipped during alert resolution', exc_info=True)

    log_q = Q(message_summary__icontains=barangay, alert__status='active')
    if syndrome:
        log_q &= Q(message_summary__icontains=syndrome) | Q(alert__alert_type__iexact=syndrome)
    alert_ids.update(
        NotificationLog.objects.filter(log_q).values_list('alert_id', flat=True).distinct()
    )

    if syndrome:
        direct_ids = NotificationLog.objects.filter(
            alert__status='active',
            message_summary__icontains=barangay,
        ).filter(
            Q(alert__alert_type__iexact=syndrome) | Q(alert__alert_type__icontains=syndrome)
        ).values_list('alert_id', flat=True)
        alert_ids.update(direct_ids)

    if not alert_ids:
        return 0

    resolved = Alert.objects.filter(id__in=alert_ids, status='active').update(status='resolved')
    if resolved:
        logger.info(
            'Resolved %s active alert(s) for %s / %s',
            resolved,
            barangay,
            syndrome or 'all syndromes',
        )
    return resolved


def _re_evaluate_epidemic_status(
    barangay: Barangay,
    syndrome: str,
    *,
    report_id: Optional[int] = None,
    actor_id: Optional[int] = None,
) -> dict:
    """Re-run PIDSR threshold evaluation after a case is closed or removed."""
    category = resolve_pidsr_category(syndrome)
    result = evaluate_confirmed_thresholds(
        barangay,
        category,
        disease_label=syndrome or None,
    )
    now = timezone.now()
    disease_label = syndrome or 'Unknown'

    BarangayEpidemicStatus.objects.update_or_create(
        barangay_id=barangay.id,
        disease_label=disease_label,
        defaults={
            'pidsr_category': category,
            'threshold_status': result['status'],
            'confirmed_count': result['confirmed_count'],
            'evaluated_at': now,
        },
    )

    OutbreakThresholdLog.objects.create(
        barangay_id=barangay.id,
        report_id=report_id,
        disease_label=disease_label,
        pidsr_category=category,
        confirmed_count=result['confirmed_count'],
        threshold_status=result['status'],
        warning_threshold=result.get('warning_threshold'),
        outbreak_threshold=result.get('outbreak_threshold'),
        time_window_days=result.get('time_window_days') or 7,
        actor_id=actor_id,
        created_at=now,
    )

    SurveillanceReport.objects.filter(
        barangay_id=barangay.id,
        status='Confirmed',
    ).filter(_syndrome_match_q(syndrome)).update(
        epidemic_threshold_status=result['status'],
        updated_at=now,
    )
    return result


def handle_case_state_change(
    *,
    report: SurveillanceReport | None = None,
    barangay_id: int | None = None,
    syndrome: str | None = None,
    trigger_report_id: int | None = None,
    actor_id: int | None = None,
) -> dict:
    """
    Reconcile alerts and APTAS scores after a case is closed, recovered, or deleted.

    Called from ``close_case`` and the ``pre_delete`` signal on ``SurveillanceReport``.
    """
    if report is not None:
        barangay_id = report.barangay_id
        syndrome = (report.syndrome_type or report.suspected_disease or '').strip()
        trigger_report_id = trigger_report_id or report.id

    if not barangay_id:
        return {'resolved_alerts': 0, 'aptas_reset': False}

    barangay = Barangay.objects.filter(id=barangay_id).first()
    if not barangay:
        return {'resolved_alerts': 0, 'aptas_reset': False}

    syndrome = (syndrome or '').strip()
    barangay_name = barangay.barangay_name

    threshold_result = _re_evaluate_epidemic_status(
        barangay,
        syndrome,
        report_id=trigger_report_id,
        actor_id=actor_id,
    )

    probable_confirmed_count = count_active_probable_confirmed(barangay.id, syndrome)
    surveillance_count = count_active_surveillance_cases(barangay.id, syndrome)
    below_outbreak = threshold_result['status'] not in OUTBREAK_THRESHOLD_STATUSES

    resolved_alerts = 0
    aptas_reset = False

    if probable_confirmed_count == 0 or below_outbreak:
        resolved_alerts = resolve_alerts_for_barangay_syndrome(barangay_name, syndrome)

    if surveillance_count == 0 and syndrome:
        reset_aptas_risk_for_barangay_syndrome(barangay_name, syndrome)
        aptas_reset = True

    recalculate_aptas_for_barangay(
        barangay.id,
        trigger_report_id=trigger_report_id,
        syndrome_hints=[syndrome] if syndrome else None,
    )

    return {
        'resolved_alerts': resolved_alerts,
        'aptas_reset': aptas_reset,
        'probable_confirmed_count': probable_confirmed_count,
        'surveillance_count': surveillance_count,
        'threshold_status': threshold_result['status'],
    }
