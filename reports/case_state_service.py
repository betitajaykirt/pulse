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
    THRESHOLD_STATUS_NORMAL,
    evaluate_confirmed_thresholds,
)

logger = logging.getLogger(__name__)

ACTIVE_PROBABLE_CONFIRMED_STATUSES = ('Probable', 'Confirmed')


def count_active_probable_confirmed(barangay_id: int, syndrome_name: str | None = None) -> int:
    """Count open Probable and Confirmed cases (excludes Closed / Discarded)."""
    qs = SurveillanceReport.objects.filter(
        barangay_id=barangay_id,
        status__in=ACTIVE_PROBABLE_CONFIRMED_STATUSES,
    )
    if syndrome_name and syndrome_name.strip():
        qs = qs.filter(_syndrome_match_q(syndrome_name))
    return qs.count()


def count_active_surveillance_cases(barangay_id: int, syndrome_name: str | None = None) -> int:
    """Count open Probable, Confirmed, and Suspected cases."""
    qs = SurveillanceReport.objects.filter(
        barangay_id=barangay_id,
        status__in=ACTIVE_SURVEILLANCE_STATUSES,
    )
    if syndrome_name and syndrome_name.strip():
        qs = qs.filter(_syndrome_match_q(syndrome_name))
    return qs.count()


def _collect_barangay_syndromes(barangay: Barangay) -> set[str]:
    """Syndromes that may still have stale alerts or epidemic status."""
    labels: set[str] = set()
    barangay_name = barangay.barangay_name

    for disease_label in BarangayEpidemicStatus.objects.filter(
        barangay_id=barangay.id,
    ).values_list('disease_label', flat=True):
        if disease_label and disease_label.strip():
            labels.add(disease_label.strip())

    from reports.models import BarangayRiskLog

    for syndrome in BarangayRiskLog.objects.filter(
        barangay__iexact=barangay_name,
        is_active_alert=True,
    ).values_list('syndrome', flat=True):
        if syndrome and syndrome.strip():
            labels.add(syndrome.strip())

    for syndrome_type, suspected in SurveillanceReport.objects.filter(
        barangay_id=barangay.id,
    ).values_list('syndrome_type', 'suspected_disease'):
        for value in (syndrome_type, suspected):
            if value and value.strip():
                labels.add(value.strip())

    return labels


def resolve_all_barangay_alerts(barangay_name: str) -> int:
    """Resolve every active alert tied to a barangay (any syndrome)."""
    barangay = canonical_barangay_name(barangay_name)
    if not barangay:
        return 0

    alert_ids: set[int] = set()
    try:
        from dashboard.models import AppNotification

        alert_ids.update(
            AppNotification.objects.filter(barangay_name__iexact=barangay)
            .exclude(alert_id__isnull=True)
            .values_list('alert_id', flat=True)
        )
    except Exception:
        logger.debug('AppNotification lookup skipped during barangay-wide resolution', exc_info=True)

    alert_ids.update(
        NotificationLog.objects.filter(
            message_summary__icontains=barangay,
            alert__status='active',
        ).values_list('alert_id', flat=True).distinct()
    )

    if not alert_ids:
        return 0

    resolved = Alert.objects.filter(id__in=alert_ids, status='active').update(status='resolved')
    if resolved:
        logger.info('Resolved %s active alert(s) for barangay %s', resolved, barangay)
    try:
        from dashboard.notification_service import dismiss_app_notifications

        dismiss_app_notifications(alert_ids=alert_ids)
        dismiss_app_notifications(barangay_name=barangay)
    except Exception:
        logger.debug('AppNotification cleanup skipped during barangay-wide resolution', exc_info=True)
    return resolved


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
    try:
        from dashboard.notification_service import dismiss_app_notifications

        dismiss_app_notifications(alert_ids=alert_ids)
        if barangay and syndrome:
            dismiss_app_notifications(barangay_name=barangay, disease=syndrome)
    except Exception:
        logger.debug('AppNotification cleanup skipped during alert resolution', exc_info=True)
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


def reconcile_barangay_surveillance_state(
    barangay_id: int,
    *,
    trigger_report_id: int | None = None,
    actor_id: int | None = None,
    extra_syndromes: list[str] | None = None,
) -> dict:
    """
    Full barangay reconciliation after case closure, recovery, or deletion.

    Re-evaluates epidemic thresholds per syndrome, resolves stale alerts, and
    resets APTAS scores when no open surveillance cases remain.
    """
    barangay = Barangay.objects.filter(id=barangay_id).first()
    if not barangay:
        return {'resolved_alerts': 0, 'aptas_resets': 0}

    barangay_name = barangay.barangay_name
    syndromes = _collect_barangay_syndromes(barangay)
    if extra_syndromes:
        for label in extra_syndromes:
            if label and label.strip():
                syndromes.add(label.strip())

    total_active = count_active_surveillance_cases(barangay.id)
    aptas_resets = 0
    threshold_updates: list[str] = []

    for syndrome in sorted(syndromes):
        result = _re_evaluate_epidemic_status(
            barangay,
            syndrome,
            report_id=trigger_report_id,
            actor_id=actor_id,
        )
        threshold_updates.append(f'{syndrome}:{result["status"]}')

        syndrome_active = count_active_surveillance_cases(barangay.id, syndrome)
        if syndrome_active == 0:
            if reset_aptas_risk_for_barangay_syndrome(barangay_name, syndrome):
                aptas_resets += 1
            resolve_alerts_for_barangay_syndrome(barangay_name, syndrome)

    resolved_alerts = 0
    if total_active == 0:
        resolved_alerts = resolve_all_barangay_alerts(barangay_name)
        BarangayEpidemicStatus.objects.filter(barangay_id=barangay.id).exclude(
            threshold_status=THRESHOLD_STATUS_NORMAL,
        ).update(
            threshold_status=THRESHOLD_STATUS_NORMAL,
            confirmed_count=0,
            evaluated_at=timezone.now(),
        )

    recalculate_aptas_for_barangay(
        barangay.id,
        trigger_report_id=trigger_report_id,
        syndrome_hints=list(syndromes),
    )

    return {
        'resolved_alerts': resolved_alerts,
        'aptas_resets': aptas_resets,
        'total_active_cases': total_active,
        'threshold_updates': threshold_updates,
    }


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

    return reconcile_barangay_surveillance_state(
        barangay_id,
        trigger_report_id=trigger_report_id,
        actor_id=actor_id,
        extra_syndromes=[syndrome] if syndrome else None,
    )
