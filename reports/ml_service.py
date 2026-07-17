"""
Live ML inference bridge — connects Django batch intake to ``ml_pipeline.py``.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd
from django.conf import settings
from django.utils import timezone

from ml_pipeline import (
    DEFAULT_CLASSIFICATION_CONFIDENCE,
    INCONCLUSIVE_SYNDROMIC_LABEL,
    TARGET_COLUMN,
    CLIMATE_DEFAULTS,
    detect_anomalies,
    ensure_climate_columns,
    patient_case_to_feature_row,
    train_and_classify,
)
from myapp.models import EnvironmentalData
from reports.weather_service import FALLBACK_WEATHER

logger = logging.getLogger(__name__)

HISTORICAL_CSV = Path(settings.BASE_DIR) / 'historical_training_data.csv'

INSUFFICIENT_DATA_LABEL = 'Insufficient Data for Prediction'
MIN_SYMPTOMS_FOR_CLASSIFICATION = 2
CLASSIFICATION_CONFIDENCE_THRESHOLD = DEFAULT_CLASSIFICATION_CONFIDENCE


def _load_training_frame() -> pd.DataFrame:
    if HISTORICAL_CSV.is_file():
        frame = pd.read_csv(HISTORICAL_CSV)
        return ensure_climate_columns(frame)
    logger.warning('historical_training_data.csv not found — using minimal fallback training set.')
    from ml_pipeline import _build_mock_training_set  # noqa: SLF001
    return _build_mock_training_set()


def _climate_fallback_features() -> dict:
    return {
        'temperature': float(FALLBACK_WEATHER.get('temperature_c', CLIMATE_DEFAULTS['temperature'])),
        'humidity': float(FALLBACK_WEATHER.get('humidity_pct', CLIMATE_DEFAULTS['humidity'])),
        'rainfall': float(FALLBACK_WEATHER.get('precipitation_mm', CLIMATE_DEFAULTS['rainfall'])),
    }


def get_climate_features_for_timestamp(reference_dt=None) -> dict:
    """
    Resolve the closest ``EnvironmentalData`` row for a case submission time.

    Falls back to Open-Meteo safe defaults (30.0°C, 70.0%, 0.0 mm) when no
    environmental snapshot exists yet.
    """
    ref = reference_dt or timezone.now()
    if timezone.is_naive(ref):
        ref = timezone.make_aware(ref, timezone.get_current_timezone())

    try:
        before = (
            EnvironmentalData.objects.filter(recorded_at__lte=ref)
            .order_by('-recorded_at')
            .first()
        )
        if before:
            return {
                'temperature': float(before.temperature or CLIMATE_DEFAULTS['temperature']),
                'humidity': float(before.humidity or CLIMATE_DEFAULTS['humidity']),
                'rainfall': float(before.rainfall or CLIMATE_DEFAULTS['rainfall']),
            }

        after = (
            EnvironmentalData.objects.filter(recorded_at__gt=ref)
            .order_by('recorded_at')
            .first()
        )
        if after:
            return {
                'temperature': float(after.temperature or CLIMATE_DEFAULTS['temperature']),
                'humidity': float(after.humidity or CLIMATE_DEFAULTS['humidity']),
                'rainfall': float(after.rainfall or CLIMATE_DEFAULTS['rainfall']),
            }
    except Exception as exc:
        logger.warning('EnvironmentalData lookup failed: %s', exc)

    return _climate_fallback_features()


def _classification_from_label(disease_label: str) -> str:
    """Map ML disease label to SurveillanceReport.case_classification slug."""
    normalized = (disease_label or '').strip().lower()
    if normalized == 'confirmed':
        return 'confirmed'
    inconclusive = {
        'inconclusive syndromic pattern',
        'insufficient data for prediction',
        '',
    }
    if normalized in inconclusive:
        return 'unassigned'
    return 'probable'


def _count_reported_symptoms(symptoms: Sequence[str]) -> int:
    return len({str(code).strip() for code in (symptoms or []) if str(code).strip()})


def analyze_patient_case(
    *,
    age: int,
    sex: str,
    symptoms: Sequence[str],
    barangay_name: str = '',
    submission_datetime=None,
) -> Dict[str, Any]:
    """
    Run Isolation Forest outbreak screening + Random Forest classification.

    Returns dict with keys: ``is_anomaly``, ``anomaly_score``, ``disease_label``,
    ``case_classification``.
    """
    train_df = _load_training_frame()
    now = submission_datetime or timezone.now()
    symptom_count = _count_reported_symptoms(symptoms)
    climate = get_climate_features_for_timestamp(now)

    feature_row = patient_case_to_feature_row(
        age=age,
        sex=sex,
        symptom_codes=symptoms,
        temperature=climate['temperature'],
        humidity=climate['humidity'],
        rainfall=climate['rainfall'],
    )
    feature_row['barangay'] = barangay_name or ''
    feature_row['submission_date'] = now.date().isoformat()

    incoming = ensure_climate_columns(pd.DataFrame([feature_row]))

    baseline = train_df.drop(columns=[TARGET_COLUMN], errors='ignore')
    combined = pd.concat([baseline, incoming], ignore_index=True)
    screened = detect_anomalies(combined)
    result_row = screened.iloc[-1]

    is_anomaly = int(result_row['is_anomaly']) == -1
    anomaly_score = float(result_row['anomaly_score'])

    if symptom_count < MIN_SYMPTOMS_FOR_CLASSIFICATION:
        disease_label = INSUFFICIENT_DATA_LABEL
    else:
        try:
            disease_label = train_and_classify(
                train_df,
                incoming,
                confidence_threshold=CLASSIFICATION_CONFIDENCE_THRESHOLD,
                low_confidence_label=INCONCLUSIVE_SYNDROMIC_LABEL,
            )
        except Exception as exc:
            logger.exception('Random Forest classification failed: %s', exc)
            disease_label = 'Inconclusive Syndromic Pattern'

    return {
        'is_anomaly': is_anomaly,
        'anomaly_score': anomaly_score,
        'disease_label': disease_label,
        'case_classification': _classification_from_label(disease_label),
        'symptom_count': symptom_count,
        'classification_confidence_threshold': CLASSIFICATION_CONFIDENCE_THRESHOLD,
        'climate_features': climate,
    }


def analyze_batch_cases(cases: List[dict], barangay_names: Optional[dict] = None) -> List[Dict[str, Any]]:
    """Analyze each case dict from the batch JSON payload."""
    barangay_names = barangay_names or {}
    results = []
    for idx, case in enumerate(cases, start=1):
        symptoms = case.get('symptoms') or []
        brgy_id = case.get('barangay') or case.get('barangay_id')
        brgy_name = barangay_names.get(str(brgy_id), '')
        try:
            results.append(analyze_patient_case(
                age=int(case['age']),
                sex=case['sex'],
                symptoms=symptoms,
                barangay_name=brgy_name,
            ))
        except Exception as exc:
            logger.exception('ML analysis failed for patient #%s: %s', idx, exc)
            results.append({
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'disease_label': 'Inconclusive Syndromic Pattern',
                'case_classification': 'unassigned',
                'symptom_count': _count_reported_symptoms(symptoms),
            })
    return results
