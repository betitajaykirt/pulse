"""
DOH PIDSR Machine Learning inference engine.

Stage 1: Isolation Forest outbreak screening
Stage 2: Random Forest multi-class classification (7 monitored diseases)
         with Group E exposure-based confidence gating
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder

from reports.pidsr_schema import (
    DISEASE_EXPOSURE_REQUIREMENTS,
    DISEASE_LABELS,
    EXPOSURE_GATING_CONFIDENCE_CAP,
    EXPOSURE_GATING_PENALTY_FACTOR,
    INCONCLUSIVE_SYNDROMIC_LABEL,
    SYNDROMIC_FEATURE_COLUMNS,
    normalize_symptom_codes,
    normalize_disease_label,
)

CLIMATE_FEATURE_COLUMNS: Sequence[str] = ('temperature', 'humidity', 'rainfall')
CLIMATE_DEFAULTS = {'temperature': 30.0, 'humidity': 70.0, 'rainfall': 0.0}
TARGET_COLUMN = 'disease_label'
DEFAULT_CLASSIFICATION_CONFIDENCE = 0.30


def resolve_syndromic_feature_columns(
    symptom_codes: Optional[Sequence[str]] = None,
) -> List[str]:
    columns = list(SYNDROMIC_FEATURE_COLUMNS)
    if symptom_codes:
        for code in normalize_symptom_codes(symptom_codes):
            if code not in columns:
                columns.append(code)
    return columns


def patient_case_to_feature_row(
    *,
    age,
    sex,
    symptom_codes: Sequence[str],
    extra_columns: Optional[Sequence[str]] = None,
    temperature: Optional[float] = None,
    humidity: Optional[float] = None,
    rainfall: Optional[float] = None,
) -> dict:
    row = {'age': age, 'sex': sex}
    active = set(normalize_symptom_codes(symptom_codes))
    for col in resolve_syndromic_feature_columns(extra_columns):
        row[col] = 1 if col in active else 0
    row['temperature'] = float(temperature if temperature is not None else CLIMATE_DEFAULTS['temperature'])
    row['humidity'] = float(humidity if humidity is not None else CLIMATE_DEFAULTS['humidity'])
    row['rainfall'] = float(rainfall if rainfall is not None else CLIMATE_DEFAULTS['rainfall'])
    return row


def ensure_climate_columns(df: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    for col, default in CLIMATE_DEFAULTS.items():
        if col not in working.columns:
            working[col] = default
        else:
            working[col] = pd.to_numeric(working[col], errors='coerce').fillna(default)
    return working


def _coerce_binary(series: pd.Series) -> pd.Series:
    return series.fillna(0).astype(float).clip(0, 1).astype(int)


def _encode_sex(series: pd.Series) -> pd.Series:
    mapping = {'male': 0.0, 'm': 0.0, 'female': 1.0, 'f': 1.0}
    return (
        series.fillna('')
        .astype(str)
        .str.strip()
        .str.lower()
        .map(lambda v: mapping.get(v, 0.5))
    )


def _prepare_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    if 'age' in working.columns:
        working['age'] = pd.to_numeric(working['age'], errors='coerce')
    else:
        working['age'] = np.nan

    working['sex_encoded'] = _encode_sex(working['sex']) if 'sex' in working.columns else 0.5
    working = ensure_climate_columns(working)

    feature_cols = ['age', 'sex_encoded'] + list(SYNDROMIC_FEATURE_COLUMNS) + list(CLIMATE_FEATURE_COLUMNS)
    for col in SYNDROMIC_FEATURE_COLUMNS:
        if col not in working.columns:
            working[col] = 0
        working[col] = _coerce_binary(working[col])

    for col in CLIMATE_FEATURE_COLUMNS:
        working[col] = pd.to_numeric(working[col], errors='coerce').fillna(CLIMATE_DEFAULTS[col])

    matrix = working[feature_cols].astype(float)
    imputer = SimpleImputer(strategy='median')
    imputed = imputer.fit_transform(matrix)
    return pd.DataFrame(imputed, columns=feature_cols, index=working.index)


def _exposure_profile_satisfied(disease_label: str, feature_row: dict) -> bool:
    required = DISEASE_EXPOSURE_REQUIREMENTS.get(disease_label)
    if not required:
        return True
    return any(int(feature_row.get(code, 0) or 0) == 1 for code in required)


def apply_exposure_gating(
    proba: np.ndarray,
    class_labels: Sequence[str],
    feature_row: dict,
) -> np.ndarray:
    """
    Penalize disease probabilities when Group E exposure history does not match.

    If no required exposure factor is present, scale probability down and cap at 50%.
    """
    adjusted = proba.copy().astype(float)
    for idx, label in enumerate(class_labels):
        if label not in DISEASE_EXPOSURE_REQUIREMENTS:
            continue
        if _exposure_profile_satisfied(label, feature_row):
            continue
        adjusted[idx] *= EXPOSURE_GATING_PENALTY_FACTOR
        adjusted[idx] = min(adjusted[idx], EXPOSURE_GATING_CONFIDENCE_CAP)
    total = adjusted.sum()
    if total > 0:
        adjusted /= total
    return adjusted


def _calibrate_anomaly_score(raw_score: float, active_cases: int) -> float:
    """
    Calibrate Isolation Forest score_samples to risk score [0, 1].
    Normal baseline scores ~ -0.48 -> mapped to 0.05-0.20
    Surge anomaly scores < -0.64 -> mapped to 0.80+
    """
    val = (-raw_score - 0.43) / 0.22
    val = float(max(0.0, min(1.0, val)))
    
    if active_cases <= 2:
        val = min(val, 0.20)
    elif active_cases >= 5:
        val = max(val, 0.80)
        
    return val


def detect_anomalies(
    data: pd.DataFrame,
    *,
    contamination: float = 0.08,
    random_state: int = 42,
) -> pd.DataFrame:
    if data.empty:
        result = data.copy()
        result['is_anomaly'] = pd.Series(dtype=int)
        result['anomaly_score'] = pd.Series(dtype=float)
        return result

    feature_cols = ['active_cases', 'rainfall_mm', 'temperature_c', 'humidity_pct']
    working = data.copy()
    
    if 'active_cases' not in working.columns:
        working['active_cases'] = 0
    working['active_cases'] = pd.to_numeric(working['active_cases'], errors='coerce').fillna(0)
    
    if 'rainfall_mm' not in working.columns:
        working['rainfall_mm'] = working.get('rainfall', CLIMATE_DEFAULTS['rainfall'])
    if 'temperature_c' not in working.columns:
        working['temperature_c'] = working.get('temperature', CLIMATE_DEFAULTS['temperature'])
    if 'humidity_pct' not in working.columns:
        working['humidity_pct'] = working.get('humidity', CLIMATE_DEFAULTS['humidity'])
        
    for col, default_key in [('rainfall_mm', 'rainfall'), ('temperature_c', 'temperature'), ('humidity_pct', 'humidity')]:
        working[col] = pd.to_numeric(working[col], errors='coerce').fillna(CLIMATE_DEFAULTS[default_key])

    features = working[feature_cols].astype(float)
    
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(features)
    
    result = data.copy()
    raw_scores = model.score_samples(features)
    result['is_anomaly'] = model.predict(features).astype(int)
    result['anomaly_score'] = [
        float(_calibrate_anomaly_score(s, c)) 
        for s, c in zip(raw_scores, working['active_cases'])
    ]
    return result


def train_and_classify_result(
    train_data: pd.DataFrame,
    incoming_patient: pd.DataFrame,
    *,
    random_state: int = 42,
    confidence_threshold: float = DEFAULT_CLASSIFICATION_CONFIDENCE,
    low_confidence_label: str = INCONCLUSIVE_SYNDROMIC_LABEL,
) -> dict:
    if train_data.empty:
        raise ValueError('train_data must contain at least one labeled row.')
    if TARGET_COLUMN not in train_data.columns:
        raise ValueError(f"train_data must include a '{TARGET_COLUMN}' column.")

    x_train = _prepare_feature_frame(train_data)
    y_raw = train_data[TARGET_COLUMN].astype(str).str.strip()
    label_encoder = LabelEncoder()
    y_train = label_encoder.fit_transform(y_raw)

    classifier = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        class_weight='balanced_subsample',
        random_state=random_state,
        n_jobs=-1,
    )
    classifier.fit(x_train, y_train)

    if incoming_patient.empty:
        return {
            'disease_label': low_confidence_label,
            'top_predicted_disease': '',
            'classification_confidence': None,
        }

    feature_row = incoming_patient.iloc[0].to_dict()
    x_infer = _prepare_feature_frame(incoming_patient.iloc[[0]])
    proba = classifier.predict_proba(x_infer)[0]
    class_labels = [str(label_encoder.inverse_transform([i])[0]) for i in range(len(proba))]
    gated_proba = apply_exposure_gating(proba, class_labels, feature_row)

    sorted_indices = np.argsort(gated_proba)[::-1]
    max_idx = int(sorted_indices[0])
    max_prob = float(gated_proba[max_idx])
    top_label = normalize_disease_label(class_labels[max_idx])

    secondary_label = None
    secondary_prob = None
    has_multiple_probable = False

    if len(sorted_indices) > 1:
        sec_idx = int(sorted_indices[1])
        sec_p = float(gated_proba[sec_idx])
        if sec_p >= 0.20 or (max_prob - sec_p) <= 0.20:
            secondary_label = normalize_disease_label(class_labels[sec_idx])
            secondary_prob = sec_p
            has_multiple_probable = True

    if max_prob < confidence_threshold:
        disease_label = low_confidence_label
    else:
        disease_label = top_label

    return {
        'disease_label': disease_label,
        'top_predicted_disease': top_label,
        'classification_confidence': max_prob,
        'secondary_predicted_disease': secondary_label,
        'secondary_classification_confidence': secondary_prob,
        'has_multiple_probable': has_multiple_probable,
        'exposure_gated': not np.allclose(proba, gated_proba),
    }


def train_and_classify(
    train_data: pd.DataFrame,
    incoming_patient: pd.DataFrame,
    **kwargs,
) -> str:
    return train_and_classify_result(train_data, incoming_patient, **kwargs)['disease_label']
