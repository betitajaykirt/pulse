"""APTAS — Alerts, Patterns, and Thresholds Analysis System."""
from __future__ import annotations

import logging
import math
import statistics
from datetime import timedelta
from typing import Any, Dict, Optional

from urllib.parse import urlencode

from django.db.models import Q
from django.utils import timezone

from myapp.models import BarangayEpidemicStatus, EnvironmentalData, OutbreakThresholdLog, SurveillanceReport
from reports.barangay_adjacency import (
    canonical_barangay_name,
    get_neighboring_barangays,
    haversine_meters,
)
from reports.models import BarangayRiskLog
from reports.weather_service import DATA_SOURCE, FALLBACK_WEATHER

logger = logging.getLogger(__name__)

# Isolation Forest ``score_samples`` are typically negative; lower = more anomalous.
ANOMALY_SCORE_MIN = -0.5
ANOMALY_SCORE_MAX = 0.5

RAINFALL_NORMALIZE_MM = 50.0
TEMPERATURE_OPTIMAL_C = 29.0
WET_SEASON_MONTHS = {6, 7, 8, 9, 10, 11}

RISK_LEVEL_THRESHOLDS = (
    ('Critical', 75.0),
    ('High', 60.0),
    ('Moderate', 40.0),
    ('Low', 0.0),
)

# Stability circuit-breaker — both gates must pass before dashboard alerting.
CIRCUIT_BREAKER_MIN_RISK_SCORE = 60.0
CIRCUIT_BREAKER_MIN_ANOMALY = 0.50

ACTIVE_SURVEILLANCE_STATUSES = ('Probable', 'Confirmed', 'Suspected')

INCONCLUSIVE_SYNDROME_LABELS = frozenset({
    'inconclusive syndromic pattern',
    'insufficient data for prediction',
    'undetermined',
    '',
})

SPATIAL_CLUSTER_RADIUS_M = 500.0
SPATIAL_NEARBY_CASE_CAP = 3
TEMPORAL_WINDOW_DAYS = 7
TEMPORAL_BASELINE_WEEKS = 4
SPATIAL_ACTIVITY_WINDOW_DAYS = 30


SPATIAL_ACTIVITY_WINDOW_DAYS = 30

PIDSR_THRESHOLD_STATUSES = (
    'PROBABLE_OUTBREAK',
    'OUTBREAK_CONFIRMED',
    'CRITICAL_OUTBREAK',
)

PIDSR_STATUS_RISK_LEVEL = {
    'PROBABLE_OUTBREAK': 'High',
    'OUTBREAK_CONFIRMED': 'Critical',
    'CRITICAL_OUTBREAK': 'Critical',
}

PIDSR_STATUS_HEADLINE = {
    'PROBABLE_OUTBREAK': 'PROBABLE OUTBREAK DETECTED',
    'OUTBREAK_CONFIRMED': 'OUTBREAK CONFIRMED',
    'CRITICAL_OUTBREAK': 'CRITICAL OUTBREAK DETECTED',
}


def _enrich_card_context(card: Dict[str, Any], *, nurses_by_barangay: dict | None = None) -> Dict[str, Any]:
    """Attach report-level context (officer, purok, coordinates, active cases) to a card."""
    from myapp.barangay_scope import catchment_nurse_officer_fields
    from myapp.models import Alert

    barangay_name = card.get('barangay', '')
    syndrome_name = card.get('syndrome', '')

    # Count active cases for this barangay + syndrome
    active_qs = _active_reports_qs(barangay_name, syndrome_name) if barangay_name else None
    card['active_cases'] = active_qs.count() if active_qs else 0

    # Find anchor report for purok and coordinates
    anchor = (
        active_qs.order_by('-report_date').first()
    ) if active_qs else None

    if nurses_by_barangay is not None:
        nurse = nurses_by_barangay.get((barangay_name or '').strip().casefold())
        officer_fields = catchment_nurse_officer_fields(nurse)
    else:
        officer_fields = catchment_nurse_officer_fields(barangay_name=barangay_name)
    card['officer_name'] = officer_fields['officer_name']
    card['officer_contact'] = officer_fields['officer_contact']

    if anchor:
        card['purok'] = (anchor.detailed_address or '').strip()
        card['latitude'] = float(anchor.latitude) if anchor.latitude is not None else None
        card['longitude'] = float(anchor.longitude) if anchor.longitude is not None else None
    else:
        card['purok'] = ''
        card['latitude'] = None
        card['longitude'] = None

    # Trigger source
    if not card.get('trigger_source'):
        card['trigger_source'] = 'Spatial Cluster Spike'

    # Build map URL with lat/lng for direct pan
    map_params = {'barangay': barangay_name}
    if card.get('latitude') is not None and card.get('longitude') is not None:
        map_params['lat'] = card['latitude']
        map_params['lng'] = card['longitude']
    card['map_url'] = f'/map/?{urlencode(map_params)}' if barangay_name else '/map/'

    # Find associated Alert ID (most recent active alert for this syndrome in this barangay)
    if not card.get('alert_id'):
        alert = (
            Alert.objects.filter(
                alert_type__iexact=syndrome_name,
                status='active',
            )
            .order_by('-alert_date')
            .first()
        )
        card['alert_id'] = alert.id if alert else None

    return card


def _aptas_ml_log_to_card(log: BarangayRiskLog) -> Dict[str, Any]:
    return {
        'alert_source': 'aptas_ml',
        'is_pidsr_threshold': False,
        'risk_level': log.risk_level,
        'barangay': log.barangay,
        'syndrome': log.syndrome,
        'final_risk_score': log.final_risk_score,
        'anomaly_score': log.anomaly_score,
        'temporal_score': log.temporal_score,
        'spatial_score': log.spatial_score,
        'environmental_score': log.environmental_score,
        'created_at': log.created_at,
        'is_active_alert': log.is_active_alert,
    }



def _latest_threshold_window_days(barangay_id: int, disease_label: str) -> int:
    latest_log = (
        OutbreakThresholdLog.objects.filter(
            barangay_id=barangay_id,
            disease_label=disease_label,
        )
        .order_by('-created_at')
        .first()
    )
    if latest_log and latest_log.time_window_days:
        return int(latest_log.time_window_days)
    return TEMPORAL_WINDOW_DAYS


def get_pidsr_threshold_alert_cards(*, barangay_name: str | None = None) -> list[Dict[str, Any]]:
    """Build early-warning cards from active PIDSR threshold epidemic statuses."""
    qs = BarangayEpidemicStatus.objects.filter(
        threshold_status__in=PIDSR_THRESHOLD_STATUSES,
    ).select_related('barangay').order_by('-evaluated_at')

    if barangay_name:
        qs = qs.filter(barangay__barangay_name__iexact=canonical_barangay_name(barangay_name))

    cards: list[Dict[str, Any]] = []
    for row in qs:
        disease = row.disease_label or 'Unknown disease'
        if not _is_trackable_syndrome(disease):
            continue
        status = (row.threshold_status or '').strip()
        risk_level = PIDSR_STATUS_RISK_LEVEL.get(status, 'High')
        headline = PIDSR_STATUS_HEADLINE.get(status, 'THRESHOLD ALERT')
        brgy_name = row.barangay.barangay_name if row.barangay else ''
        window_days = _latest_threshold_window_days(row.barangay_id, disease)
        case_word = 'case' if row.confirmed_count == 1 else 'cases'
        summary = (
            f'{row.confirmed_count} confirmed {case_word} within {window_days} days'
        )
        map_url = f'/map/?{urlencode({"barangay": brgy_name})}' if brgy_name else '/map/'

        cards.append({
            'alert_source': 'pidsr_threshold',
            'is_pidsr_threshold': True,
            'risk_level': risk_level,
            'barangay': brgy_name,
            'syndrome': disease,
            'threshold_status': status,
            'threshold_status_display': status.replace('_', ' ').title(),
            'threshold_headline': f'{headline} — {disease} ({brgy_name})',
            'threshold_summary': summary,
            'confirmed_count': row.confirmed_count,
            'time_window_days': window_days,
            'map_url': map_url,
            'created_at': row.evaluated_at,
            'is_active_alert': True,
            'final_risk_score': 100.0 if risk_level == 'Critical' else 75.0,
            'anomaly_score': 0.95 if risk_level == 'Critical' else 0.75,
            'temporal_score': min(1.0, row.confirmed_count / max(window_days, 1)),
            'spatial_score': 0.0,
            'environmental_score': 0.0,
        })
    return cards


def deactivate_inconclusive_alerts() -> None:
    """Retire live APTAS/PIDSR signals that still use an inconclusive label."""
    from django.db.models import Q
    from myapp.models import Alert

    inconclusive_q = (
        Q(syndrome__iexact='Inconclusive Syndromic Pattern')
        | Q(syndrome__icontains='inconclusive')
        | Q(syndrome__iexact='Insufficient Data for Prediction')
        | Q(syndrome__iexact='Undetermined')
        | Q(syndrome='')
    )
    BarangayRiskLog.objects.filter(is_active_alert=True).filter(inconclusive_q).update(
        is_active_alert=False,
    )

    alert_q = (
        Q(alert_type__iexact='Inconclusive Syndromic Pattern')
        | Q(alert_type__icontains='inconclusive')
        | Q(alert_type__iexact='Insufficient Data for Prediction')
        | Q(alert_type__iexact='Undetermined')
    )
    Alert.objects.filter(status='active').filter(alert_q).update(status='resolved')

    try:
        from dashboard.models import AppNotification

        notif_q = (
            Q(disease__iexact='Inconclusive Syndromic Pattern')
            | Q(disease__icontains='inconclusive')
            | Q(disease__iexact='Insufficient Data for Prediction')
            | Q(disease__iexact='Undetermined')
        )
        AppNotification.objects.filter(notif_q).delete()
    except Exception:
        logger.debug('Inconclusive AppNotification cleanup skipped', exc_info=True)


def get_aptas_dashboard_context(*, barangay_name=None, limit=12):
    """Build template context for APTAS alert cards (ML signals + PIDSR thresholds)."""
    deactivate_inconclusive_alerts()
    base_qs = BarangayRiskLog.objects.all()
    if barangay_name:
        base_qs = base_qs.filter(barangay__iexact=barangay_name)

    active_qs = base_qs.filter(is_active_alert=True).order_by(
        '-final_risk_score', '-created_at',
    )

    pidsr_cards = get_pidsr_threshold_alert_cards(barangay_name=barangay_name)
    pidsr_keys = {
        (c['barangay'].casefold(), c['syndrome'].casefold())
        for c in pidsr_cards
    }

    ml_cards = [
        _aptas_ml_log_to_card(log)
        for log in active_qs
        if _is_trackable_syndrome(log.syndrome)
        and (log.barangay.casefold(), log.syndrome.casefold()) not in pidsr_keys
    ]

    def _sort_key(card: Dict[str, Any]):
        level_rank = {'Critical': 0, 'High': 1, 'Moderate': 2, 'Low': 3}.get(card['risk_level'], 4)
        pidsr_rank = 0 if card.get('is_pidsr_threshold') else 1
        return (pidsr_rank, level_rank, -float(card.get('final_risk_score') or 0))

    merged_alerts = sorted(pidsr_cards + ml_cards, key=_sort_key)[:limit]
    from myapp.barangay_scope import catchment_nurses_by_barangay
    nurses_by_barangay = catchment_nurses_by_barangay(
        [card.get('barangay') for card in merged_alerts]
    )
    merged_alerts = [
        _enrich_card_context(card, nurses_by_barangay=nurses_by_barangay)
        for card in merged_alerts
    ]

    critical_count = sum(1 for c in pidsr_cards + ml_cards if c['risk_level'] == 'Critical')
    high_count = sum(1 for c in pidsr_cards + ml_cards if c['risk_level'] == 'High')
    moderate_count = sum(1 for c in ml_cards if c['risk_level'] == 'Moderate')
    low_count = sum(1 for c in ml_cards if c['risk_level'] == 'Low')
    active_count = len(pidsr_cards) + active_qs.count()

    return {
        'aptas_alerts': merged_alerts,
        'aptas_pidsr_alerts': pidsr_cards,
        'aptas_alert_count': active_count,
        'aptas_risk_counts': {
            'critical': critical_count,
            'high': high_count,
            'moderate': moderate_count,
            'low': low_count,
        },
        'aptas_latest_logs': list(base_qs.order_by('-created_at')[:limit]),
    }


def resolve_aptas_barangay_filter(role, user_id, ctx):
    """Limit APTAS cards to a BHW / barangay-scoped user's assigned barangay."""
    from myapp.barangay_scope import BARANGAY_SCOPED_ROLES, resolve_user_barangay
    from myapp.models import User

    if role not in BARANGAY_SCOPED_ROLES:
        return None

    if ctx.get('barangay_name'):
        return ctx['barangay_name']

    if not user_id:
        return None

    user = User.objects.filter(id=user_id).first()
    barangay = resolve_user_barangay(user) if user else None
    return barangay.barangay_name if barangay else None


def normalize_anomaly_score(raw_anomaly_score) -> float:
    """
    Map Isolation Forest ``score_samples`` (or pre-normalized values) to [0.0, 1.0].

    Higher values indicate stronger deviation from baseline (more anomalous).
    """
    if raw_anomaly_score is None:
        return 0.0

    score = float(raw_anomaly_score)
    if math.isnan(score) or math.isinf(score):
        return 0.0

    if 0.0 <= score <= 1.0:
        return score

    span = ANOMALY_SCORE_MAX - ANOMALY_SCORE_MIN
    if span <= 0:
        return 0.0

    normalized = (ANOMALY_SCORE_MAX - score) / span
    return max(0.0, min(1.0, normalized))


def _local_today():
    return timezone.localdate()


def _coerce_date(value):
    if value is None:
        return _local_today()
    if hasattr(value, 'date') and not isinstance(value, type(_local_today())):
        try:
            if timezone.is_aware(value):
                return timezone.localtime(value).date()
        except (TypeError, ValueError):
            pass
        return value.date()
    return value


def _canonical_disease_key(label: str) -> str:
    """Normalize disease labels for cluster matching (Dengue ≈ Dengue Fever)."""
    from reports.pidsr_schema import normalize_disease_label

    text = normalize_disease_label((label or '').strip()).lower()
    for suffix in (' fever', ' disease', ' / severe enteroviral disease'):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    return text


def _disease_match_terms(label: str) -> set[str]:
    """Search terms used to find related reports in the same disease cluster."""
    syndrome = (label or '').strip()
    if not syndrome:
        return set()

    terms = {
        syndrome.lower(),
        _canonical_disease_key(syndrome),
        syndrome,
    }
    compact = _canonical_disease_key(syndrome)
    if compact and ' ' not in compact and ',' not in compact:
        terms.add(compact)
    if compact:
        terms.add(compact.title())
    return {t for t in terms if t and len(t) >= 3}


def _is_trackable_syndrome(syndrome_name: str) -> bool:
    from reports.ml_display import is_alertable_disease_label

    if (syndrome_name or '').strip().lower() in INCONCLUSIVE_SYNDROME_LABELS:
        return False
    return is_alertable_disease_label(syndrome_name)


def _syndrome_match_q(syndrome_name: str) -> Q:
    syndrome = (syndrome_name or '').strip()
    if not _is_trackable_syndrome(syndrome):
        return Q()

    terms = _disease_match_terms(syndrome)
    if not terms:
        return Q()

    q = Q()
    for term in terms:
        q |= Q(syndrome_type__icontains=term)
        q |= Q(suspected_disease__icontains=term)
        q |= Q(remarks__icontains=f'ML Top Prediction: {term}')
        q |= Q(remarks__icontains=f'ML Classification: {term}')
    return q


def _cluster_window_bounds(reference_date):
    """Symmetric rolling window so co-emerging cases see each other on the map."""
    ref = _coerce_date(reference_date)
    half = max(1, TEMPORAL_WINDOW_DAYS // 2)
    return ref - timedelta(days=half), ref + timedelta(days=half)


def _active_reports_qs(
    barangay_name: str,
    syndrome_name: str | None = None,
    *,
    reference_date=None,
    activity_window_days: int | None = SPATIAL_ACTIVITY_WINDOW_DAYS,
    forward_days: int = 0,
):
    barangay = canonical_barangay_name(barangay_name)
    qs = SurveillanceReport.objects.filter(
        barangay__barangay_name__iexact=barangay,
        status__in=ACTIVE_SURVEILLANCE_STATUSES,
    )
    syndrome_q = _syndrome_match_q(syndrome_name or '')
    if syndrome_q:
        qs = qs.filter(syndrome_q)
    if activity_window_days:
        ref = _coerce_date(reference_date)
        start = ref - timedelta(days=activity_window_days)
        end = ref + timedelta(days=forward_days)
        qs = qs.filter(
            Q(date_of_onset__gte=start, date_of_onset__lte=end)
            | Q(
                date_of_onset__isnull=True,
                report_date__date__gte=start,
                report_date__date__lte=end,
            )
        )
    return qs


def _count_reports_in_date_window(
    barangay_name: str,
    syndrome_name: str,
    start,
    end,
    *,
    exclude_report_id=None,
) -> int:
    qs = _active_reports_qs(
        barangay_name,
        syndrome_name,
        reference_date=end,
        activity_window_days=None,
    )
    qs = qs.filter(
        Q(date_of_onset__gte=start, date_of_onset__lte=end)
        | Q(
            date_of_onset__isnull=True,
            report_date__date__gte=start,
            report_date__date__lte=end,
        )
    )
    if exclude_report_id:
        qs = qs.exclude(id=exclude_report_id)
    return qs.count()


def _syndrome_report_count(
    barangay_name: str,
    syndrome_name: str,
    start,
    end,
    *,
    exclude_report_id=None,
) -> int:
    return _count_reports_in_date_window(
        barangay_name,
        syndrome_name,
        start,
        end,
        exclude_report_id=exclude_report_id,
    )


def compute_temporal_score(
    barangay_name: str,
    syndrome_name: str,
    *,
    reference_date=None,
    exclude_report_id=None,
    cluster_mode: bool = False,
) -> float:
    """
    T = min(1, max(0, (x_7 - mu_28) / (3 * sigma_28))) with zero-variance safeguard.

    Uses ``date_of_onset`` (fallback ``report_date``) and counts Probable, Confirmed,
    and Suspected cases relative to the case reference date (not only "today").

    When ``cluster_mode`` is True (per-pin map popups), uses a symmetric rolling window
    so cases that emerge a few days apart still contribute to the same cluster signal.
    """
    ref = _coerce_date(reference_date)
    if cluster_mode:
        week_start, week_end = _cluster_window_bounds(ref)
    else:
        week_start = ref - timedelta(days=TEMPORAL_WINDOW_DAYS - 1)
        week_end = ref
    baseline_end = week_start - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=(TEMPORAL_BASELINE_WEEKS * 7) - 1)

    x_7 = _syndrome_report_count(
        barangay_name,
        syndrome_name,
        week_start,
        week_end,
        exclude_report_id=exclude_report_id,
    )

    weekly_counts = []
    for week_index in range(TEMPORAL_BASELINE_WEEKS):
        window_start = baseline_start + timedelta(days=week_index * 7)
        window_end = window_start + timedelta(days=6)
        weekly_counts.append(
            _syndrome_report_count(
                barangay_name,
                syndrome_name,
                window_start,
                window_end,
                exclude_report_id=exclude_report_id,
            )
        )

    mu_28 = statistics.mean(weekly_counts) if weekly_counts else 0.0
    sigma_28 = statistics.pstdev(weekly_counts) if len(weekly_counts) > 1 else 0.0

    if sigma_28 == 0:
        return 1.0 if x_7 > 0 else 0.0

    t_score = (x_7 - mu_28) / (3 * sigma_28)
    return max(0.0, min(1.0, t_score))


def _normalize_rainfall(mm: float) -> float:
    return max(0.0, min(1.0, float(mm) / RAINFALL_NORMALIZE_MM))


def _normalize_humidity(pct: float) -> float:
    return max(0.0, min(1.0, float(pct) / 100.0))


def _seasonal_weather_factor(temperature_c: float, reference_date=None) -> float:
    """W — seasonal temperature / weather suitability in [0.0, 1.0]."""
    ref = reference_date or _local_today()
    month = ref.month if hasattr(ref, 'month') else timezone.localdate().month

    temp_score = 1.0 - min(abs(float(temperature_c) - TEMPERATURE_OPTIMAL_C) / 10.0, 1.0)
    season_score = 0.85 if month in WET_SEASON_MONTHS else 0.45
    return max(0.0, min(1.0, (0.6 * temp_score) + (0.4 * season_score)))


def _latest_environmental_record():
    record = (
        EnvironmentalData.objects.filter(data_source=DATA_SOURCE)
        .order_by('-recorded_at')
        .first()
    )
    if record:
        return record

    return (
        EnvironmentalData.objects.order_by('-recorded_at').first()
    )


def compute_environmental_score(reference_dt=None) -> float:
    """
    E = (0.40 * R) + (0.30 * H) + (0.30 * W) using the latest Open-Meteo cache row.
    """
    record = _latest_environmental_record()
    if record:
        rainfall = float(record.rainfall or 0.0)
        humidity = float(record.humidity or 0.0)
        temperature = float(record.temperature or FALLBACK_WEATHER['temperature_c'])
        ref_date = record.recorded_at
    else:
        rainfall = float(FALLBACK_WEATHER['precipitation_mm'])
        humidity = float(FALLBACK_WEATHER['humidity_pct'])
        temperature = float(FALLBACK_WEATHER['temperature_c'])
        ref_date = reference_dt or timezone.now()

    r_norm = _normalize_rainfall(rainfall)
    h_norm = _normalize_humidity(humidity)
    w_norm = _seasonal_weather_factor(temperature, ref_date)

    return (0.40 * r_norm) + (0.30 * h_norm) + (0.30 * w_norm)


def _neighbor_has_elevated_activity(neighbor_name: str, syndrome_name: str, *, reference_date=None) -> bool:
    ref = _coerce_date(reference_date)
    week_start = ref - timedelta(days=TEMPORAL_WINDOW_DAYS - 1)
    return _syndrome_report_count(neighbor_name, syndrome_name, week_start, ref) > 0


def compute_spatial_score(
    barangay_name: str,
    syndrome_name: str,
    *,
    reference_date=None,
) -> float:
    """
    Regional score: elevated adjacent barangays / total adjacent neighbors.
    """
    neighbors = get_neighboring_barangays(barangay_name)
    if not neighbors:
        return 0.0

    elevated = sum(
        1 for neighbor in neighbors
        if _neighbor_has_elevated_activity(
            neighbor,
            syndrome_name,
            reference_date=reference_date,
        )
    )
    return elevated / len(neighbors)


def compute_spatial_score_for_report(
    report,
    syndrome_name: str,
    *,
    radius_m: float = SPATIAL_CLUSTER_RADIUS_M,
) -> float:
    """
    Case-level spatial score using Haversine proximity within ``radius_m`` meters
    in the same barangay, blended with adjacent-barangay regional activity.
    """
    if not report or not report.barangay_id:
        return 0.0

    barangay = canonical_barangay_name(report.barangay.barangay_name)
    syndrome = (syndrome_name or report.syndrome_type or report.suspected_disease or '').strip()
    track_syndrome = syndrome if _is_trackable_syndrome(syndrome) else None
    ref = report.date_of_onset or (
        report.report_date.date() if report.report_date else _local_today()
    )

    local_score = 0.0
    try:
        lat = float(report.latitude)
        lng = float(report.longitude)
    except (TypeError, ValueError):
        lat = lng = None

    if lat is not None and lng is not None:
        nearby = 0
        candidates = _active_reports_qs(
            barangay,
            track_syndrome,
            reference_date=ref,
            forward_days=TEMPORAL_WINDOW_DAYS,
        ).exclude(id=report.id).filter(
            latitude__isnull=False,
            longitude__isnull=False,
        )
        for other in candidates.only('id', 'latitude', 'longitude'):
            try:
                dist_m = haversine_meters(
                    lat,
                    lng,
                    float(other.latitude),
                    float(other.longitude),
                )
            except (TypeError, ValueError):
                continue
            if dist_m <= radius_m:
                nearby += 1
        if nearby:
            local_score = min(1.0, nearby / SPATIAL_NEARBY_CASE_CAP)
    else:
        week_start = _coerce_date(ref) - timedelta(days=TEMPORAL_WINDOW_DAYS - 1)
        count = _count_reports_in_date_window(
            barangay,
            syndrome,
            week_start,
            _coerce_date(ref),
            exclude_report_id=report.id,
        )
        local_score = min(1.0, count / 5.0) if count else 0.0

    regional_score = compute_spatial_score(
        barangay,
        syndrome,
        reference_date=ref,
    )
    if local_score <= 0 and regional_score <= 0:
        return 0.0
    return min(1.0, (0.75 * local_score) + (0.25 * regional_score))


def classify_risk_level(final_risk_score: float) -> str:
    """Map final risk score to thesis tiers: Low / Moderate / High / Critical."""
    for label, minimum in RISK_LEVEL_THRESHOLDS:
        if final_risk_score >= minimum:
            return label
    return 'Low'


def should_activate_aptas_alert(final_risk_score: float, anomaly_score: float, force_activate: bool = False) -> bool:
    """
    Stability circuit-breaker gate.

    Active alerting requires BOTH:
    - final RiskScore >= 60 (High or Critical tier), and
    - normalized anomaly A >= 0.50 (confirmed ML deviation).
    """
    if force_activate:
        return True
    return (
        final_risk_score >= CIRCUIT_BREAKER_MIN_RISK_SCORE
        and anomaly_score >= CIRCUIT_BREAKER_MIN_ANOMALY
    )


def compute_final_risk_score(
    anomaly_score: float,
    temporal_score: float,
    environmental_score: float,
    spatial_score: float,
) -> float:
    composite = (
        (0.50 * anomaly_score)
        + (0.20 * temporal_score)
        + (0.15 * environmental_score)
        + (0.15 * spatial_score)
    )
    return round(100.0 * composite, 2)


def compute_and_log_barangay_risk(
    barangay_name: str,
    syndrome_name: str,
    raw_anomaly_score,
    *,
    deactivate_previous: bool = True,
    force_activate: bool = False,
    report=None,
) -> BarangayRiskLog:
    """
    Run the APTAS multi-variate formula and persist a ``BarangayRiskLog`` row.

    RiskScore = 100 * ((0.50 * A) + (0.20 * T) + (0.15 * E) + (0.15 * S))
    """
    barangay = canonical_barangay_name(barangay_name)
    syndrome = (syndrome_name or '').strip()
    if not barangay or not syndrome:
        raise ValueError('barangay_name and syndrome_name are required for APTAS scoring.')

    anomaly = normalize_anomaly_score(raw_anomaly_score)
    ref_date = None
    if report is not None:
        ref_date = report.date_of_onset or (
            report.report_date.date() if report.report_date else None
        )
    temporal = compute_temporal_score(
        barangay,
        syndrome,
        reference_date=ref_date,
        exclude_report_id=getattr(report, 'id', None),
        cluster_mode=report is not None,
    )
    environmental = compute_environmental_score()
    if report is not None:
        spatial = compute_spatial_score_for_report(report, syndrome)
    else:
        spatial = compute_spatial_score(barangay, syndrome, reference_date=ref_date)
    final_score = compute_final_risk_score(anomaly, temporal, environmental, spatial)
    risk_level = classify_risk_level(final_score)
    is_active = should_activate_aptas_alert(final_score, anomaly, force_activate=force_activate)
    if not _is_trackable_syndrome(syndrome):
        is_active = False

    if deactivate_previous:
        BarangayRiskLog.objects.filter(
            barangay__iexact=barangay,
            syndrome__iexact=syndrome,
            is_active_alert=True,
        ).update(is_active_alert=False)

    log = BarangayRiskLog.objects.create(
        barangay=barangay,
        syndrome=syndrome,
        anomaly_score=round(anomaly, 4),
        temporal_score=round(temporal, 4),
        environmental_score=round(environmental, 4),
        spatial_score=round(spatial, 4),
        final_risk_score=final_score,
        risk_level=risk_level,
        is_active_alert=is_active,
        created_at=timezone.now(),
    )

    logger.info(
        'APTAS risk logged for %s / %s: score=%.2f level=%s active=%s',
        barangay, syndrome, final_score, risk_level, is_active,
    )
    return log


def compute_aptas_breakdown(
    barangay_name: str,
    syndrome_name: str,
    raw_anomaly_score,
    *,
    report=None,
) -> Dict[str, Any]:
    """Return component scores without writing to the database (for tests / debugging)."""
    barangay = canonical_barangay_name(barangay_name)
    syndrome = (syndrome_name or '').strip()
    if _active_reports_qs(barangay, syndrome).count() == 0:
        return {
            'barangay': barangay,
            'syndrome': syndrome,
            'anomaly_score': 0.0,
            'temporal_score': 0.0,
            'environmental_score': 0.0,
            'spatial_score': 0.0,
            'final_risk_score': 0.0,
            'risk_level': 'Low',
            'is_active_alert': False,
        }
    anomaly = normalize_anomaly_score(raw_anomaly_score)
    ref_date = None
    exclude_report_id = None
    if report is not None:
        ref_date = report.date_of_onset or (
            report.report_date.date() if report.report_date else None
        )
        exclude_report_id = report.id
    temporal = compute_temporal_score(
        barangay,
        syndrome,
        reference_date=ref_date,
        exclude_report_id=exclude_report_id,
        cluster_mode=report is not None,
    )
    environmental = compute_environmental_score()
    if report is not None:
        spatial = compute_spatial_score_for_report(report, syndrome)
    else:
        spatial = compute_spatial_score(barangay, syndrome, reference_date=ref_date)
    final_score = compute_final_risk_score(anomaly, temporal, environmental, spatial)
    return {
        'barangay': barangay,
        'syndrome': syndrome,
        'anomaly_score': anomaly,
        'temporal_score': temporal,
        'environmental_score': environmental,
        'spatial_score': spatial,
        'final_risk_score': final_score,
        'risk_level': classify_risk_level(final_score),
        'is_active_alert': (
            should_activate_aptas_alert(final_score, anomaly)
            and _is_trackable_syndrome(syndrome)
        ),
    }


def _raw_anomaly_for_report(report) -> float:
    if report.ml_anomaly_score is not None:
        return float(report.ml_anomaly_score)
    if report.is_anomaly:
        return 0.75   # Pre-calibrated: maps to High tier
    return 0.15       # Pre-calibrated: maps to Low/Baseline tier


def reset_aptas_risk_for_barangay_syndrome(barangay_name: str, syndrome_name: str) -> BarangayRiskLog | None:
    """
    Deactivate APTAS alerts and persist a zero-score breakdown for a barangay/syndrome.

    Used when no active surveillance cases remain after closure or deletion.
    """
    barangay = canonical_barangay_name(barangay_name)
    syndrome = (syndrome_name or '').strip()
    if not barangay or not syndrome:
        return None

    BarangayRiskLog.objects.filter(
        barangay__iexact=barangay,
        syndrome__iexact=syndrome,
        is_active_alert=True,
    ).update(is_active_alert=False)

    log = BarangayRiskLog.objects.create(
        barangay=barangay,
        syndrome=syndrome,
        anomaly_score=0.0,
        temporal_score=0.0,
        environmental_score=0.0,
        spatial_score=0.0,
        final_risk_score=0.0,
        risk_level='Low',
        is_active_alert=False,
        created_at=timezone.now(),
    )
    logger.info('APTAS risk reset to zero for %s / %s', barangay, syndrome)
    return log


def recalculate_aptas_for_barangay(
    barangay,
    *,
    trigger_report_id=None,
    syndrome_hints: list[str] | None = None,
) -> list[BarangayRiskLog]:
    """
    Recompute APTAS logs for active syndromes in a barangay.

    Called after batch submission and case confirmation so neighbor records refresh.
    """
    from myapp.models import Barangay

    if isinstance(barangay, int):
        barangay = Barangay.objects.filter(id=barangay).first()
    if not barangay:
        return []

    logs: list[BarangayRiskLog] = []
    processed_syndromes: set[str] = set()
    syndrome_labels: dict[str, str] = {}

    def _register_syndrome(label: str) -> None:
        if _is_trackable_syndrome(label):
            syndrome_labels[label.casefold()] = label

    if syndrome_hints:
        for hint in syndrome_hints:
            _register_syndrome((hint or '').strip())

    for label in BarangayRiskLog.objects.filter(
        barangay__iexact=barangay.barangay_name,
        is_active_alert=True,
    ).values_list('syndrome', flat=True):
        _register_syndrome(label)

    if trigger_report_id:
        trigger = SurveillanceReport.objects.filter(
            id=trigger_report_id,
            barangay_id=barangay.id,
        ).select_related('barangay').first()
        if trigger:
            syndrome = (trigger.syndrome_type or trigger.suspected_disease or '').strip()
            _register_syndrome(syndrome)
            key = syndrome.casefold()
            if _is_trackable_syndrome(syndrome) and key not in processed_syndromes:
                if _active_reports_qs(barangay.barangay_name, syndrome).count() == 0:
                    reset_log = reset_aptas_risk_for_barangay_syndrome(
                        barangay.barangay_name,
                        syndrome,
                    )
                    if reset_log:
                        logs.append(reset_log)
                    processed_syndromes.add(key)
                else:
                    anchor = (
                        _active_reports_qs(barangay.barangay_name, syndrome)
                        .order_by('-report_date')
                        .first()
                    )
                    if anchor:
                        processed_syndromes.add(key)
                        logs.append(
                            compute_and_log_barangay_risk(
                                barangay.barangay_name,
                                syndrome,
                                _raw_anomaly_for_report(anchor),
                                report=anchor,
                            )
                        )

    siblings = (
        SurveillanceReport.objects.filter(
            barangay_id=barangay.id,
            status__in=ACTIVE_SURVEILLANCE_STATUSES,
        )
        .select_related('barangay')
        .order_by('-report_date')[:40]
    )
    for sibling in siblings:
        syndrome = (sibling.syndrome_type or sibling.suspected_disease or '').strip()
        key = syndrome.casefold()
        if not _is_trackable_syndrome(syndrome) or key in processed_syndromes:
            continue
        processed_syndromes.add(key)
        _register_syndrome(syndrome)
        logs.append(
            compute_and_log_barangay_risk(
                barangay.barangay_name,
                syndrome,
                _raw_anomaly_for_report(sibling),
                report=sibling,
            )
        )

    for key, label in syndrome_labels.items():
        if key in processed_syndromes:
            continue
        if _active_reports_qs(barangay.barangay_name, label).count() == 0:
            reset_log = reset_aptas_risk_for_barangay_syndrome(barangay.barangay_name, label)
            if reset_log:
                logs.append(reset_log)
            processed_syndromes.add(key)

    return logs


def get_barangay_risk_map_matrix() -> Dict[str, Dict[str, Any]]:
    """
    Latest APTAS score per barangay for choropleth map styling.

    Returns ``{barangay_name: {'score': float, 'level': str}}``.
    Barangays with no open surveillance cases always return zero risk.
    """
    from myapp.models import Barangay

    matrix: Dict[str, Dict[str, Any]] = {}
    barangay_ids_by_name: Dict[str, int] = {}
    for row in Barangay.objects.values('id', 'barangay_name'):
        name = canonical_barangay_name(row['barangay_name'])
        if name:
            barangay_ids_by_name[name.casefold()] = row['id']

    logs = BarangayRiskLog.objects.order_by('-created_at')
    for log in logs:
        name = canonical_barangay_name(log.barangay)
        if not name or name in matrix:
            continue
        brgy_id = barangay_ids_by_name.get(name.casefold())
        if brgy_id and not SurveillanceReport.objects.filter(
            barangay_id=brgy_id,
            status__in=ACTIVE_SURVEILLANCE_STATUSES,
        ).exists():
            matrix[name] = {'score': 0.0, 'level': 'Low'}
            continue
        matrix[name] = {
            'score': float(log.final_risk_score),
            'level': log.risk_level,
        }
    return matrix
