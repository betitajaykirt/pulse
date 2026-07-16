"""
Dynamic PIDSR category threshold evaluation for admin-confirmed cases.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, Optional, Union

from django.db.models import Sum
from django.utils import timezone

from myapp.models import (
    Barangay, DiseaseCategoryThreshold, SurveillanceReport,
    BarangayEpidemicStatus, OutbreakThresholdLog,
)
from myapp.threshold_data import resolve_pidsr_category
from reports.risk_service import trigger_threshold_outbreak_alert


THRESHOLD_STATUS_ISOLATED = 'ISOLATED_CASE'
THRESHOLD_STATUS_PROBABLE = 'PROBABLE_OUTBREAK'
THRESHOLD_STATUS_OUTBREAK = 'OUTBREAK_CONFIRMED'
THRESHOLD_STATUS_NORMAL = 'NORMAL'


def _count_confirmed_cases(
    barangay: Barangay,
    *,
    disease_label: Optional[str],
    window_days: int,
) -> int:
    cutoff = timezone.now() - timedelta(days=window_days)
    qs = SurveillanceReport.objects.filter(
        barangay_id=barangay.id,
        status='Confirmed',
        case_classification='confirmed',
        confirmed_at__gte=cutoff,
    ).exclude(status='Closed')
    if disease_label:
        qs = qs.filter(syndrome_type=disease_label)
    total = qs.aggregate(total=Sum('case_count'))['total']
    return int(total or 0)


def _apply_category_logic(confirmed_count: int, config: DiseaseCategoryThreshold) -> str:
    level = config.category_level.strip()

    if level == 'Category 1':
        if confirmed_count >= config.outbreak_threshold:
            return THRESHOLD_STATUS_OUTBREAK
        return THRESHOLD_STATUS_NORMAL

    # Category 2 (default multi-tier logic)
    if confirmed_count >= config.outbreak_threshold:
        return THRESHOLD_STATUS_OUTBREAK
    if confirmed_count == config.warning_threshold:
        return THRESHOLD_STATUS_PROBABLE
    if confirmed_count == 1:
        return THRESHOLD_STATUS_ISOLATED
    return THRESHOLD_STATUS_NORMAL


def evaluate_confirmed_thresholds(
    barangay: Union[Barangay, int],
    disease_category: str,
    *,
    disease_label: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate admin-confirmed case counts against dynamic PIDSR thresholds.

    Parameters
    ----------
    barangay : Barangay or int
        Target barangay instance or primary key.
    disease_category : str
        PIDSR level, e.g. ``'Category 1'`` or ``'Category 2'``.
    disease_label : str, optional
        Syndrome / disease label used to scope confirmed-case counting.

    Returns
    -------
    dict
        Keys: ``status``, ``confirmed_count``, ``category_level``,
        ``warning_threshold``, ``outbreak_threshold``, ``time_window_days``.
    """
    if isinstance(barangay, int):
        barangay = Barangay.objects.filter(id=barangay).first()
    if not barangay:
        raise ValueError('Barangay not found for threshold evaluation.')

    # Check for specific disease threshold first
    from myapp.models import OutbreakThreshold
    if disease_label:
        specific_threshold = OutbreakThreshold.objects.filter(
            disease_label__iexact=disease_label,
            is_active=True
        ).first()

        if specific_threshold:
            confirmed_count = _count_confirmed_cases(
                barangay,
                disease_label=disease_label,
                window_days=specific_threshold.rolling_window_days,
            )
            
            # Simple threshold logic: if cases >= threshold, it's an outbreak
            status = THRESHOLD_STATUS_NORMAL
            if confirmed_count >= specific_threshold.case_threshold:
                status = THRESHOLD_STATUS_OUTBREAK
            elif specific_threshold.case_threshold > 1 and confirmed_count == specific_threshold.case_threshold - 1:
                # Optionally warn if they are 1 case away, or just use PROBABLE
                status = THRESHOLD_STATUS_PROBABLE
            elif confirmed_count > 0:
                status = THRESHOLD_STATUS_ISOLATED

            return {
                'status': status,
                'confirmed_count': confirmed_count,
                'category_level': 'Disease Specific',
                'warning_threshold': specific_threshold.case_threshold,
                'outbreak_threshold': specific_threshold.case_threshold,
                'time_window_days': specific_threshold.rolling_window_days,
                'disease_label': disease_label,
                'barangay_id': barangay.id,
                'barangay_name': barangay.barangay_name,
            }

    # Fallback to category logic
    config = DiseaseCategoryThreshold.objects.filter(
        category_level=disease_category,
        is_active=True,
    ).first()
    if not config:
        config = DiseaseCategoryThreshold.objects.filter(is_active=True).order_by('category_level').first()
    if not config:
        return {
            'status': THRESHOLD_STATUS_NORMAL,
            'confirmed_count': 0,
            'category_level': disease_category,
            'warning_threshold': None,
            'outbreak_threshold': None,
            'time_window_days': 7,
        }

    confirmed_count = _count_confirmed_cases(
        barangay,
        disease_label=disease_label,
        window_days=config.time_window_days,
    )
    status = _apply_category_logic(confirmed_count, config)

    return {
        'status': status,
        'confirmed_count': confirmed_count,
        'category_level': config.category_level,
        'warning_threshold': config.warning_threshold,
        'outbreak_threshold': config.outbreak_threshold,
        'time_window_days': config.time_window_days,
        'disease_label': disease_label or '',
        'barangay_id': barangay.id,
        'barangay_name': barangay.barangay_name,
    }


def process_confirmation_threshold_check(
    report: SurveillanceReport,
    *,
    actor_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run threshold evaluation after admin confirmation and escalate if needed.

    Persists barangay epidemic status, logs the evaluation, updates report
    metadata, and triggers APTAS alerts for probable/confirmed outbreaks.
    """
    disease_label = (report.syndrome_type or report.suspected_disease or '').strip()
    category = resolve_pidsr_category(disease_label)
    result = evaluate_confirmed_thresholds(
        report.barangay,
        category,
        disease_label=disease_label,
    )

    now = timezone.now()

    BarangayEpidemicStatus.objects.update_or_create(
        barangay_id=report.barangay_id,
        disease_label=disease_label or 'Unknown',
        defaults={
            'pidsr_category': category,
            'threshold_status': result['status'],
            'confirmed_count': result['confirmed_count'],
            'evaluated_at': now,
        },
    )

    OutbreakThresholdLog.objects.create(
        barangay_id=report.barangay_id,
        report_id=report.id,
        disease_label=disease_label or 'Unknown',
        pidsr_category=category,
        confirmed_count=result['confirmed_count'],
        threshold_status=result['status'],
        warning_threshold=result['warning_threshold'],
        outbreak_threshold=result['outbreak_threshold'],
        time_window_days=result['time_window_days'],
        actor_id=actor_id,
        created_at=now,
    )

    SurveillanceReport.objects.filter(
        barangay_id=report.barangay_id,
        syndrome_type=disease_label,
        status='Confirmed',
    ).update(
        epidemic_threshold_status=result['status'],
        updated_at=now,
    )

    if result['status'] in (THRESHOLD_STATUS_PROBABLE, THRESHOLD_STATUS_OUTBREAK):
        trigger_threshold_outbreak_alert(
            report_id=report.id,
            threshold_result=result,
        )

    return result
