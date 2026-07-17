#!/usr/bin/env python
"""
PULSE-AI Historical Training Data Generator
===========================================

Standalone epidemiological simulator that builds a realistic synthetic baseline
(200–300 rows) for ``ml_pipeline.py`` — Random Forest classification and
Isolation Forest outbreak spike detection.

Outputs ``historical_training_data.csv`` at the project root with columns aligned
to ``ml_pipeline.SYNDROMIC_FEATURE_COLUMNS`` plus demographics, spatial-temporal
context, and ``disease_label``.

Usage (from djangotutorial/):
    python seed_ml_data.py
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from ml_pipeline import (
    SYNDROMIC_FEATURE_COLUMNS,
    TARGET_COLUMN,
    CLIMATE_FEATURE_COLUMNS,
    CLIMATE_DEFAULTS,
)

# ---------------------------------------------------------------------------
# Epidemiological configuration
# ---------------------------------------------------------------------------

RANDOM_SEED = 42
OUTPUT_CSV = Path(__file__).resolve().parent / 'historical_training_data.csv'
TARGET_ROW_COUNT = 365
OUTBREAK_ROW_COUNT = 18
ILI_MINOR_ROW_COUNT = 85

# Bago City barangays represented in map / intake workflows
BARANGAYS_BASELINE = [
    'Poblacion',
    'Ma-ao',
    'Balingasag',
    'Taloc',
    'Alijis',
    'Lag-asan',
    'Malingin',
    'Pacol',
    'Sagasa',
    'Tabunan',
    'Abuanan',
    'Busay',
    'Don Jorge Araneta',
    'Napoles',
    'Atipuluan',
]

OUTBREAK_BARANGAY = 'Caridad'

DISEASE_LABELS = (
    'Dengue',
    'Respiratory Illness',
    'Leptospirosis',
    'Acute Gastroenteritis',
    'Hand, Foot, and Mouth Disease',
    'Influenza-like Illness (ILI)',
    'Inconclusive Syndromic Pattern',
)

# Symptom activation profiles (keys must exist in SYNDROMIC_FEATURE_COLUMNS)
DENGUE_CORE = ('fever_high', 'headache', 'body_ache', 'fatigue', 'chills')
DENGUE_DERM = ('maculopapular_rash', 'petechiae_bleeding')

RESPIRATORY_CORE = ('cough_dry', 'runny_nose', 'sore_throat', 'dyspnea', 'fever_low')
RESPIRATORY_SEVERE = ('cough_paroxysms', 'fatigue')

LEPTO_CORE = ('fever_high', 'chills', 'headache', 'body_ache', 'fatigue')
LEPTO_EXPOSURE = ('floodwater_exposure', 'animal_bite')
LEPTO_HEPATIC = ('jaundice', 'abdominal_cramps', 'vomiting')

AGE_CORE = ('diarrhea_watery', 'vomiting', 'abdominal_cramps', 'fever_low')
AGE_SEVERE = ('fatigue',)

HFMD_CORE = ('fever_low', 'sore_throat', 'fatigue', 'headache')
HFMD_DERM = ('maculopapular_rash',)

INCONCLUSIVE_WEAK = (
    ('runny_nose',),
    ('fatigue',),
    ('headache',),
    ('fever_low', 'fatigue'),
    ('sore_throat',),
)

# Single or dual minor constitutional / ENT symptoms — normal baseline, not outbreak signals
ILI_MINOR_PROFILES = (
    ('chills',),
    ('cough_dry',),
    ('headache',),
    ('fever_low',),
    ('runny_nose',),
    ('sore_throat',),
    ('fatigue',),
    ('chills', 'headache'),
    ('cough_dry', 'runny_nose'),
    ('fever_low', 'fatigue'),
    ('chills', 'fatigue'),
    ('headache', 'fatigue'),
    ('sore_throat', 'runny_nose'),
)

OUTBREAK_SIGNATURE = (
    'fever_high', 'headache', 'body_ache', 'chills', 'fatigue',
    'maculopapular_rash', 'petechiae_bleeding',
)

# Seasonal climate profiles (°C, % humidity, mm rainfall)
CLIMATE_PROFILES = {
    'vector_outbreak': {'temperature': (28.5, 31.5), 'humidity': (86, 96), 'rainfall': (4.0, 18.0)},
    'vector_baseline': {'temperature': (27.5, 30.5), 'humidity': (78, 90), 'rainfall': (0.5, 8.0)},
    'flood_rainy': {'temperature': (25.5, 28.5), 'humidity': (88, 97), 'rainfall': (10.0, 28.0)},
    'respiratory_cool': {'temperature': (22.0, 26.5), 'humidity': (52, 70), 'rainfall': (0.0, 2.0)},
    'ili_mild': {'temperature': (23.5, 27.0), 'humidity': (58, 72), 'rainfall': (0.0, 1.5)},
    'neutral': {'temperature': (28.0, 31.0), 'humidity': (65, 78), 'rainfall': (0.0, 1.0)},
}

# Rainy / flood season months for Leptospirosis spatial-temporal clustering
RAINY_MONTHS = {6, 7, 8, 9, 10, 11}


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------


def _empty_feature_row() -> dict:
    row = {col: 0 for col in SYNDROMIC_FEATURE_COLUMNS}
    row['age'] = 0
    row['sex'] = 'Female'
    row['barangay'] = BARANGAYS_BASELINE[0]
    row['submission_date'] = date.today().isoformat()
    row[TARGET_COLUMN] = 'Inconclusive Syndromic Pattern'
    for col, default in CLIMATE_DEFAULTS.items():
        row[col] = default
    return row


def _activate(row: dict, codes: tuple[str, ...], probability: float = 0.88) -> None:
    for code in codes:
        if code in row and random.random() < probability:
            row[code] = 1


def _random_sex() -> str:
    return random.choice(['Male', 'Female'])


def _random_barangay(exclude: str | None = None) -> str:
    choices = [b for b in BARANGAYS_BASELINE if b != exclude]
    return random.choice(choices)


def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 0)))


def _assign_climate(row: dict, profile_key: str) -> None:
    """Attach realistic seasonal weather to a synthetic training row."""
    profile = CLIMATE_PROFILES.get(profile_key, CLIMATE_PROFILES['neutral'])
    row['temperature'] = round(random.uniform(*profile['temperature']), 1)
    row['humidity'] = round(random.uniform(*profile['humidity']), 1)
    row['rainfall'] = round(random.uniform(*profile['rainfall']), 2)


def _make_dengue_row(start: date, end: date) -> dict:
    row = _empty_feature_row()
    row[TARGET_COLUMN] = 'Dengue'
    row['age'] = random.randint(4, 55)
    row['sex'] = _random_sex()
    row['barangay'] = _random_barangay(exclude=OUTBREAK_BARANGAY)
    row['submission_date'] = _random_date(start, end).isoformat()
    _activate(row, DENGUE_CORE, 0.92)
    _activate(row, DENGUE_DERM, 0.75)
    _assign_climate(row, 'vector_baseline')
    return row


def _make_respiratory_row(start: date, end: date) -> dict:
    row = _empty_feature_row()
    row[TARGET_COLUMN] = 'Respiratory Illness'
    row['sex'] = _random_sex()
    row['barangay'] = _random_barangay(exclude=OUTBREAK_BARANGAY)
    row['submission_date'] = _random_date(start, end).isoformat()
    # Demographic skew: children and elderly
    band = random.random()
    if band < 0.40:
        row['age'] = random.randint(1, 12)
    elif band < 0.70:
        row['age'] = random.randint(65, 88)
    else:
        row['age'] = random.randint(18, 64)
    _activate(row, RESPIRATORY_CORE, 0.90)
    if row['age'] >= 65:
        _activate(row, RESPIRATORY_SEVERE, 0.55)
    _assign_climate(row, 'respiratory_cool')
    return row


def _make_leptospirosis_row(start: date, end: date) -> dict:
    row = _empty_feature_row()
    row[TARGET_COLUMN] = 'Leptospirosis'
    row['age'] = random.randint(16, 58)
    row['sex'] = _random_sex()
    row['barangay'] = _random_barangay(exclude=OUTBREAK_BARANGAY)
    # Bias toward rainy-season submission dates
    for _ in range(12):
        d = _random_date(start, end)
        if d.month in RAINY_MONTHS:
            row['submission_date'] = d.isoformat()
            break
    else:
        row['submission_date'] = _random_date(start, end).isoformat()
    _activate(row, LEPTO_CORE, 0.91)
    _activate(row, LEPTO_EXPOSURE, 0.82)
    _activate(row, LEPTO_HEPATIC, 0.45)
    _assign_climate(row, 'flood_rainy')
    return row


def _make_age_row(start: date, end: date) -> dict:
    row = _empty_feature_row()
    row[TARGET_COLUMN] = 'Acute Gastroenteritis'
    row['age'] = random.randint(1, 72)
    row['sex'] = _random_sex()
    row['barangay'] = _random_barangay(exclude=OUTBREAK_BARANGAY)
    row['submission_date'] = _random_date(start, end).isoformat()
    _activate(row, AGE_CORE, 0.94)
    _activate(row, AGE_SEVERE, 0.35)
    _assign_climate(row, 'neutral')
    return row


def _make_hfmd_row(start: date, end: date) -> dict:
    row = _empty_feature_row()
    row[TARGET_COLUMN] = 'Hand, Foot, and Mouth Disease'
    row['age'] = random.randint(1, 8)
    row['sex'] = _random_sex()
    row['barangay'] = _random_barangay(exclude=OUTBREAK_BARANGAY)
    row['submission_date'] = _random_date(start, end).isoformat()
    _activate(row, HFMD_CORE, 0.88)
    _activate(row, HFMD_DERM, 0.80)
    _assign_climate(row, 'neutral')
    return row


def _make_inconclusive_row(start: date, end: date) -> dict:
    row = _empty_feature_row()
    row[TARGET_COLUMN] = 'Inconclusive Syndromic Pattern'
    row['age'] = random.randint(5, 70)
    row['sex'] = _random_sex()
    row['barangay'] = _random_barangay(exclude=OUTBREAK_BARANGAY)
    row['submission_date'] = _random_date(start, end).isoformat()
    weak_set = random.choice(INCONCLUSIVE_WEAK)
    _activate(row, weak_set, 0.95)
    _assign_climate(row, 'neutral')
    return row


def _make_ili_minor_row(start: date, end: date) -> dict:
    """
    Sparse 1–2 symptom presentations mapped to ILI.

    Teaches Isolation Forest that isolated minor symptoms are baseline-normal
    (``is_anomaly == 1`` at inference) and keeps severe outbreak labels from
    being over-assigned by the Random Forest on weak evidence.
    """
    row = _empty_feature_row()
    row[TARGET_COLUMN] = 'Influenza-like Illness (ILI)'
    row['age'] = random.randint(3, 78)
    row['sex'] = _random_sex()
    row['barangay'] = _random_barangay(exclude=OUTBREAK_BARANGAY)
    row['submission_date'] = _random_date(start, end).isoformat()
    profile = random.choice(ILI_MINOR_PROFILES)
    for code in profile:
        row[code] = 1
    _assign_climate(row, 'ili_mild')
    return row


def _make_outbreak_spike_row(spike_day: date) -> dict:
    """Severe hemorrhagic-fever cluster — Isolation Forest training signal."""
    row = _empty_feature_row()
    row[TARGET_COLUMN] = 'Dengue'
    row['age'] = random.randint(6, 42)
    row['sex'] = _random_sex()
    row['barangay'] = OUTBREAK_BARANGAY
    row['submission_date'] = spike_day.isoformat()
    for code in OUTBREAK_SIGNATURE:
        row[code] = 1
    _assign_climate(row, 'vector_outbreak')
    return row


# ---------------------------------------------------------------------------
# Dataset assembly
# ---------------------------------------------------------------------------


def build_historical_training_dataframe(
    *,
    total_rows: int = TARGET_ROW_COUNT,
    outbreak_rows: int = OUTBREAK_ROW_COUNT,
    random_seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """
    Programmatically synthesize a multi-class epidemiological baseline with an
    embedded localized outbreak spike for unsupervised guardrail training.
    """
    random.seed(random_seed)
    np.random.seed(random_seed)

    baseline_rows = total_rows - outbreak_rows - ILI_MINOR_ROW_COUNT
    end = date.today()
    start = end - timedelta(days=365)

    # Class distribution for baseline (must sum to baseline_rows)
    counts = {
        'Dengue': 52,
        'Respiratory Illness': 52,
        'Leptospirosis': 44,
        'Acute Gastroenteritis': 44,
        'Hand, Foot, and Mouth Disease': 38,
        'Inconclusive Syndromic Pattern': baseline_rows - (52 + 52 + 44 + 44 + 38),
    }

    builders = {
        'Dengue': _make_dengue_row,
        'Respiratory Illness': _make_respiratory_row,
        'Leptospirosis': _make_leptospirosis_row,
        'Acute Gastroenteritis': _make_age_row,
        'Hand, Foot, and Mouth Disease': _make_hfmd_row,
        'Inconclusive Syndromic Pattern': _make_inconclusive_row,
    }

    records = []
    for label, n in counts.items():
        for _ in range(n):
            records.append(builders[label](start, end))

    for _ in range(ILI_MINOR_ROW_COUNT):
        records.append(_make_ili_minor_row(start, end))

    # Outbreak anomaly window — tight 3-day cluster in Caridad
    outbreak_start = end - timedelta(days=14)
    outbreak_days = [
        outbreak_start,
        outbreak_start + timedelta(days=1),
        outbreak_start + timedelta(days=2),
    ]
    for i in range(outbreak_rows):
        spike_day = outbreak_days[i % len(outbreak_days)]
        records.append(_make_outbreak_spike_row(spike_day))

    random.shuffle(records)
    df = pd.DataFrame(records)

    column_order = (
        ['age', 'sex', 'barangay', 'submission_date']
        + list(CLIMATE_FEATURE_COLUMNS)
        + list(SYNDROMIC_FEATURE_COLUMNS)
        + [TARGET_COLUMN]
    )
    return df[column_order]


def save_historical_training_csv(
    path: Path = OUTPUT_CSV,
    **kwargs,
) -> pd.DataFrame:
    df = build_historical_training_dataframe(**kwargs)
    df.to_csv(path, index=False)
    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


if __name__ == '__main__':
    print('=' * 72)
    print('PULSE-AI Historical Training Data Generator')
    print('=' * 72)

    frame = save_historical_training_csv()

    print(f'\nRows generated : {len(frame)}')
    print(f'Feature columns: {len(SYNDROMIC_FEATURE_COLUMNS)} syndromic + {len(CLIMATE_FEATURE_COLUMNS)} climate + age/sex/barangay/date')
    print(f'Output file    : {OUTPUT_CSV}')
    print('\nClass distribution:')
    print(frame[TARGET_COLUMN].value_counts().to_string())
    ili_only_chills = frame[
        (frame[TARGET_COLUMN] == 'Influenza-like Illness (ILI)')
        & (frame['chills'] == 1)
        & (frame[list(SYNDROMIC_FEATURE_COLUMNS)].sum(axis=1) == 1)
    ]
    print(f'\nILI rows with only chills: {len(ili_only_chills)}')
    print('\nOutbreak cluster (Caridad, last 3-day window):')
    outbreak_mask = (
        (frame['barangay'] == OUTBREAK_BARANGAY)
        & (frame['fever_high'] == 1)
        & (frame['petechiae_bleeding'] == 1)
    )
    print(frame.loc[outbreak_mask, ['submission_date', 'barangay', 'age', TARGET_COLUMN]].to_string(index=False))
    print('\nSample load in ml_pipeline:')
    print('  import pandas as pd')
    print('  from ml_pipeline import detect_anomalies, train_and_classify')
    print('  df = pd.read_csv("historical_training_data.csv")')
    print('=' * 72)
