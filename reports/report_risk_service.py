"""Shared APTAS risk resolution for map, incidents, and exports."""

from __future__ import annotations

from reports.aptas_service import (
    classify_risk_level,
    compute_aptas_breakdown,
    normalize_anomaly_score,
)
from reports.ml_display import ml_top_prediction_for_report


def _raw_anomaly_for_report(report, assessment=None) -> float | None:
    if assessment and assessment.anomaly_score is not None:
        return float(assessment.anomaly_score)
    if report.ml_anomaly_score is not None:
        return float(report.ml_anomaly_score)
    return None


def aptas_breakdown_for_report(report, assessment=None, cache=None) -> dict:
    """Return raw APTAS breakdown (final_risk_score on 0–100 scale)."""
    if cache is None:
        cache = {}
    barangay = report.barangay.barangay_name if report.barangay else ''
    syndrome = (
        ml_top_prediction_for_report(report)
        or report.syndrome_type
        or report.suspected_disease
        or 'Undetermined'
    ).strip()
    raw_anomaly = _raw_anomaly_for_report(report, assessment)
    cache_key = (barangay.lower(), syndrome.lower(), report.id, round(raw_anomaly or 0.0, 4))
    if cache_key not in cache:
        try:
            cache[cache_key] = compute_aptas_breakdown(
                barangay, syndrome, raw_anomaly, report=report,
            )
        except (ValueError, TypeError):
            anomaly = normalize_anomaly_score(raw_anomaly)
            cache[cache_key] = {
                'anomaly_score': anomaly,
                'temporal_score': 0.0,
                'spatial_score': 0.0,
                'environmental_score': 0.0,
                'final_risk_score': 0.0,
            }
    return cache[cache_key]


def aptas_display_scores_for_report(report, assessment=None, cache=None) -> dict:
    """Normalized 0–1 scores for map popups and UI."""
    breakdown = aptas_breakdown_for_report(report, assessment, cache)
    return {
        'final_score': round(float(breakdown['final_risk_score']) / 100.0, 4),
        'anomaly_score': round(float(breakdown['anomaly_score']), 4),
        'temporal_score': round(float(breakdown['temporal_score']), 4),
        'spatial_score': round(float(breakdown['spatial_score']), 4),
        'environmental_score': round(float(breakdown['environmental_score']), 4),
    }


def risk_level_for_report(report, assessment=None, cache=None) -> str:
    """APTAS tier label: Low / Moderate / High / Critical."""
    breakdown = aptas_breakdown_for_report(report, assessment, cache)
    return classify_risk_level(float(breakdown.get('final_risk_score') or 0.0))
