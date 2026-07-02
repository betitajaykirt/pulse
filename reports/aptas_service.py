"""APTAS — Alerts, Patterns, and Thresholds Analysis System."""
from __future__ import annotations

import logging
import math
import statistics
from datetime import timedelta
from typing import Any, Dict, Optional

from django.utils import timezone

from myapp.models import EnvironmentalData, SurveillanceReport
from reports.barangay_adjacency import canonical_barangay_name, get_neighboring_barangays
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


def get_aptas_dashboard_context(*, barangay_name=None, limit=12):
    """Build template context for APTAS alert cards."""
    base_qs = BarangayRiskLog.objects.all()
    if barangay_name:
        base_qs = base_qs.filter(barangay__iexact=barangay_name)

    active_qs = base_qs.filter(is_active_alert=True).order_by(
        '-final_risk_score', '-created_at',
    )

    return {
        'aptas_alerts': list(active_qs[:limit]),
        'aptas_alert_count': active_qs.count(),
        'aptas_risk_counts': {
            'critical': active_qs.filter(risk_level='Critical').count(),
            'high': active_qs.filter(risk_level='High').count(),
            'moderate': active_qs.filter(risk_level='Moderate').count(),
            'low': active_qs.filter(risk_level='Low').count(),
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


def _syndrome_report_count(barangay_name: str, syndrome_name: str, start, end) -> int:
    return SurveillanceReport.objects.filter(
        barangay__barangay_name__iexact=barangay_name,
        syndrome_type__iexact=syndrome_name,
        report_date__date__gte=start,
        report_date__date__lte=end,
    ).count()


def compute_temporal_score(barangay_name: str, syndrome_name: str) -> float:
    """
    T = min(1, max(0, (x_7 - mu_28) / (3 * sigma_28))) with zero-variance safeguard.

    ``mu_28`` and ``sigma_28`` are the mean and population std-dev of weekly case
    counts across the 28-day baseline immediately before the current 7-day window.
    """
    today = _local_today()
    week_start = today - timedelta(days=6)
    baseline_end = week_start - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=27)

    x_7 = _syndrome_report_count(barangay_name, syndrome_name, week_start, today)

    weekly_counts = []
    for week_index in range(4):
        window_start = baseline_start + timedelta(days=week_index * 7)
        window_end = window_start + timedelta(days=6)
        weekly_counts.append(
            _syndrome_report_count(barangay_name, syndrome_name, window_start, window_end)
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


def _neighbor_has_elevated_activity(neighbor_name: str, syndrome_name: str) -> bool:
    today = _local_today()
    week_start = today - timedelta(days=6)
    return _syndrome_report_count(neighbor_name, syndrome_name, week_start, today) > 0


def compute_spatial_score(barangay_name: str, syndrome_name: str) -> float:
    """
    S = elevated neighbors / total adjacent neighbors (0.0 when none found).
    """
    neighbors = get_neighboring_barangays(barangay_name)
    if not neighbors:
        return 0.0

    elevated = sum(
        1 for neighbor in neighbors
        if _neighbor_has_elevated_activity(neighbor, syndrome_name)
    )
    return elevated / len(neighbors)


def classify_risk_level(final_risk_score: float) -> str:
    """Map final risk score to thesis tiers: Low / Moderate / High / Critical."""
    for label, minimum in RISK_LEVEL_THRESHOLDS:
        if final_risk_score >= minimum:
            return label
    return 'Low'


def should_activate_aptas_alert(final_risk_score: float, anomaly_score: float) -> bool:
    """
    Stability circuit-breaker gate.

    Active alerting requires BOTH:
    - final RiskScore >= 60 (High or Critical tier), and
    - normalized anomaly A >= 0.50 (confirmed ML deviation).
    """
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
    temporal = compute_temporal_score(barangay, syndrome)
    environmental = compute_environmental_score()
    spatial = compute_spatial_score(barangay, syndrome)
    final_score = compute_final_risk_score(anomaly, temporal, environmental, spatial)
    risk_level = classify_risk_level(final_score)
    is_active = should_activate_aptas_alert(final_score, anomaly)

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
) -> Dict[str, Any]:
    """Return component scores without writing to the database (for tests / debugging)."""
    barangay = canonical_barangay_name(barangay_name)
    syndrome = (syndrome_name or '').strip()
    anomaly = normalize_anomaly_score(raw_anomaly_score)
    temporal = compute_temporal_score(barangay, syndrome)
    environmental = compute_environmental_score()
    spatial = compute_spatial_score(barangay, syndrome)
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
        'is_active_alert': should_activate_aptas_alert(final_score, anomaly),
    }


def get_barangay_risk_map_matrix() -> Dict[str, Dict[str, Any]]:
    """
    Latest APTAS score per barangay for choropleth map styling.

    Returns ``{barangay_name: {'score': float, 'level': str}}``.
    """
    matrix: Dict[str, Dict[str, Any]] = {}
    logs = BarangayRiskLog.objects.order_by('-created_at')
    for log in logs:
        name = canonical_barangay_name(log.barangay)
        if not name or name in matrix:
            continue
        matrix[name] = {
            'score': float(log.final_risk_score),
            'level': log.risk_level,
        }
    return matrix
