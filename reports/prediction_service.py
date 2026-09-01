"""
Django prediction service — bridges batch intake to ``ml_engine.py``.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd
from django.conf import settings
from django.utils import timezone

from ml_engine import (
    CLIMATE_DEFAULTS,
    DEFAULT_CLASSIFICATION_CONFIDENCE,
    INCONCLUSIVE_SYNDROMIC_LABEL,
    TARGET_COLUMN,
    detect_anomalies,
    ensure_climate_columns,
    fit_random_forest_classifier,
    patient_case_to_feature_row,
    train_and_classify_result,
)
from myapp.models import EnvironmentalData
from reports.pidsr_schema import normalize_symptom_codes
from reports.weather_service import FALLBACK_WEATHER

logger = logging.getLogger(__name__)

HISTORICAL_CSV = Path(settings.BASE_DIR) / 'historical_training_data.csv'
INSUFFICIENT_DATA_LABEL = 'Insufficient Data for Prediction'
MIN_SYMPTOMS_FOR_CLASSIFICATION = 2
CLASSIFICATION_CONFIDENCE_THRESHOLD = DEFAULT_CLASSIFICATION_CONFIDENCE


def _load_training_frame() -> pd.DataFrame:
    if HISTORICAL_CSV.is_file():
        return ensure_climate_columns(pd.read_csv(HISTORICAL_CSV))
    logger.warning('historical_training_data.csv not found — using minimal fallback training set.')
    from ml_pipeline import _build_mock_training_set  # noqa: SLF001
    return _build_mock_training_set()


def _get_outbreak_training_data() -> pd.DataFrame:
    baseline_path = Path(settings.BASE_DIR) / 'pulse_zero_baseline_data.csv'
    if baseline_path.is_file():
        baseline_df = pd.read_csv(baseline_path)
        grouped_baseline = baseline_df.groupby(['date', 'barangay']).agg({
            'active_cases': 'sum',
            'rainfall_mm': 'mean',
            'temperature_c': 'mean',
            'humidity_pct': 'mean'
        }).reset_index()
    else:
        grouped_baseline = pd.DataFrame()
        
    from myapp.models import SurveillanceReport
    
    reports = SurveillanceReport.objects.exclude(status__in=['Discarded', 'Closed']).values('report_date', 'barangay__barangay_name')
    db_rows = []
    for r in reports:
        dt = r['report_date']
        if dt:
            # handle timezone aware
            if timezone.is_aware(dt):
                dt = timezone.localtime(dt)
            db_rows.append({
                'date': dt.date().isoformat(),
                'barangay': r['barangay__barangay_name'] or '',
                'active_cases': 1,
            })
            
    db_df = pd.DataFrame(db_rows)
    if not db_df.empty:
        db_df = db_df.groupby(['date', 'barangay']).agg({'active_cases': 'sum'}).reset_index()
        
    if not db_df.empty and not grouped_baseline.empty:
        combined = pd.concat([grouped_baseline, db_df], ignore_index=True)
        return combined.groupby(['date', 'barangay']).agg({
            'active_cases': 'sum',
            'rainfall_mm': 'mean',
            'temperature_c': 'mean',
            'humidity_pct': 'mean'
        }).reset_index()
    elif not db_df.empty:
        # We don't have climate for these dynamically if baseline is empty, so we fill with defaults later
        return db_df
    return grouped_baseline


def get_climate_features_for_timestamp(reference_dt=None) -> dict:
    ref = reference_dt or timezone.now()
    if timezone.is_naive(ref):
        ref = timezone.make_aware(ref, timezone.get_current_timezone())
    try:
        snap = (
            EnvironmentalData.objects.filter(recorded_at__lte=ref)
            .order_by('-recorded_at')
            .first()
        )
        if snap:
            return {
                'temperature': float(snap.temperature or CLIMATE_DEFAULTS['temperature']),
                'humidity': float(snap.humidity or CLIMATE_DEFAULTS['humidity']),
                'rainfall': float(snap.rainfall or CLIMATE_DEFAULTS['rainfall']),
            }
    except Exception as exc:
        logger.warning('EnvironmentalData lookup failed: %s', exc)
    return {
        'temperature': float(FALLBACK_WEATHER.get('temperature_c', CLIMATE_DEFAULTS['temperature'])),
        'humidity': float(FALLBACK_WEATHER.get('humidity_pct', CLIMATE_DEFAULTS['humidity'])),
        'rainfall': float(FALLBACK_WEATHER.get('precipitation_mm', CLIMATE_DEFAULTS['rainfall'])),
    }


def _classification_from_label(disease_label: str) -> str:
    normalized = (disease_label or '').strip().lower()
    if normalized == 'confirmed':
        return 'confirmed'
    if normalized in {
        'inconclusive syndromic pattern',
        'insufficient data for prediction',
        '',
    }:
        return 'unassigned'
    return 'probable'


def _count_reported_symptoms(symptoms: Sequence[str]) -> int:
    return len(normalize_symptom_codes(symptoms))


def analyze_patient_case(
    *,
    age: int,
    sex: str,
    symptoms: Sequence[str],
    barangay_name: str = '',
    submission_datetime=None,
    train_df: Optional[pd.DataFrame] = None,
    outbreak_train_df: Optional[pd.DataFrame] = None,
    climate: Optional[dict] = None,
    fitted_classifier=None,
    same_day_prior_cases: int = 0,
) -> Dict[str, Any]:
    if train_df is None:
        train_df = _load_training_frame()
    if outbreak_train_df is None:
        outbreak_train_df = _get_outbreak_training_data()
    now = submission_datetime or timezone.now()
    symptoms = normalize_symptom_codes(symptoms)
    symptom_count = len(symptoms)
    if climate is None:
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

    from myapp.models import SurveillanceReport
    from datetime import datetime, time, timedelta
    
    # Safe date filtering for SQLite
    if timezone.is_naive(now):
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start_of_day = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
        
    end_of_day = start_of_day + timedelta(days=1)
    
    db_today_cases = SurveillanceReport.objects.filter(
        barangay__barangay_name=barangay_name, 
        report_date__gte=start_of_day,
        report_date__lt=end_of_day
    ).exclude(status__in=['Discarded', 'Closed']).count()

    incoming_outbreak_row = pd.DataFrame([{
        'active_cases': db_today_cases + max(int(same_day_prior_cases), 0) + 1,
        'rainfall_mm': climate.get('rainfall', CLIMATE_DEFAULTS['rainfall']),
        'temperature_c': climate.get('temperature', CLIMATE_DEFAULTS['temperature']),
        'humidity_pct': climate.get('humidity', CLIMATE_DEFAULTS['humidity']),
    }])

    screened = detect_anomalies(pd.concat([outbreak_train_df, incoming_outbreak_row], ignore_index=True))
    result_row = screened.iloc[-1]
    is_anomaly = int(result_row['is_anomaly']) == -1
    anomaly_score = float(result_row['anomaly_score'])

    if symptom_count < MIN_SYMPTOMS_FOR_CLASSIFICATION:
        disease_label = INSUFFICIENT_DATA_LABEL
        top_predicted = ''
        classification_confidence = None
        secondary_predicted = ''
        secondary_confidence = None
        has_multiple_probable = False
        exposure_gated = False
    else:
        try:
            clf = train_and_classify_result(
                train_df,
                incoming,
                confidence_threshold=CLASSIFICATION_CONFIDENCE_THRESHOLD,
                low_confidence_label=INCONCLUSIVE_SYNDROMIC_LABEL,
                fitted_classifier=fitted_classifier,
            )
            disease_label = clf['disease_label']
            top_predicted = clf.get('top_predicted_disease') or ''
            classification_confidence = clf.get('classification_confidence')
            secondary_predicted = clf.get('secondary_predicted_disease') or ''
            secondary_confidence = clf.get('secondary_classification_confidence')
            has_multiple_probable = bool(clf.get('has_multiple_probable'))
            exposure_gated = bool(clf.get('exposure_gated'))
        except Exception as exc:
            logger.exception('Random Forest classification failed: %s', exc)
            disease_label = INCONCLUSIVE_SYNDROMIC_LABEL
            top_predicted = ''
            classification_confidence = None
            secondary_predicted = ''
            secondary_confidence = None
            has_multiple_probable = False
            exposure_gated = False

    return {
        'is_anomaly': is_anomaly,
        'anomaly_score': anomaly_score,
        'disease_label': disease_label,
        'top_predicted_disease': top_predicted,
        'classification_confidence': classification_confidence,
        'secondary_predicted_disease': secondary_predicted,
        'secondary_classification_confidence': secondary_confidence,
        'has_multiple_probable': has_multiple_probable,
        'exposure_gated': exposure_gated,
        'case_classification': _classification_from_label(disease_label),
        'symptom_count': symptom_count,
        'classification_confidence_threshold': CLASSIFICATION_CONFIDENCE_THRESHOLD,
        'climate_features': climate,
    }


def analyze_batch_cases(
    cases: List[dict],
    barangay_names: Optional[dict] = None,
) -> List[Dict[str, Any]]:
    barangay_names = barangay_names or {}
    train_df = _load_training_frame()
    outbreak_train_df = _get_outbreak_training_data()
    climate = get_climate_features_for_timestamp()
    fitted_classifier = None
    try:
        fitted_classifier = fit_random_forest_classifier(train_df)
    except Exception:
        logger.exception('Shared Random Forest fit failed; falling back to per-case training.')
    results = []
    barangay_batch_counts: Dict[str, int] = {}
    for idx, case in enumerate(cases, start=1):
        symptoms = normalize_symptom_codes(case.get('symptoms') or [])
        brgy_id = case.get('barangay') or case.get('barangay_id')
        brgy_name = barangay_names.get(str(brgy_id), '')
        prior_in_batch = barangay_batch_counts.get(brgy_name, 0)
        try:
            results.append(analyze_patient_case(
                age=int(case['age']),
                sex=case['sex'],
                symptoms=symptoms,
                barangay_name=brgy_name,
                train_df=train_df,
                outbreak_train_df=outbreak_train_df,
                climate=climate,
                fitted_classifier=fitted_classifier,
                same_day_prior_cases=prior_in_batch,
            ))
        except Exception as exc:
            logger.exception('ML analysis failed for patient #%s: %s', idx, exc)
            results.append({
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'disease_label': INCONCLUSIVE_SYNDROMIC_LABEL,
                'top_predicted_disease': '',
                'classification_confidence': None,
                'exposure_gated': False,
                'case_classification': 'unassigned',
                'symptom_count': len(symptoms),
            })
        barangay_batch_counts[brgy_name] = prior_in_batch + 1
    return results
