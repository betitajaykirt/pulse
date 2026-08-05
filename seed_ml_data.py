#!/usr/bin/env python
"""
PULSE PIDSR Historical Training Data Generator.

Builds a 1,000-row synthetic corpus using disease-specific symptom and
Group E exposure probabilities (official DOH PIDSR monitored diseases).
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from ml_engine import CLIMATE_DEFAULTS, TARGET_COLUMN, ensure_climate_columns
from reports.pidsr_schema import DISEASE_LABELS, SYNDROMIC_FEATURE_COLUMNS

RANDOM_SEED = 42
NUM_SAMPLES = 1000
OUTPUT_CSV = Path(__file__).resolve().parent / 'historical_training_data.csv'
PIDSR_CSV = Path(__file__).resolve().parent / 'pidsr_ml_training_data.csv'

BARANGAYS = [
    'Poblacion', 'Ma-ao', 'Balingasag', 'Taloc', 'Alijis', 'Lag-asan',
    'Malingin', 'Pacol', 'Sagasa', 'Tabunan', 'Abuanan', 'Busay', 'Caridad',
]

# Sampling weights aligned with user script (maps HFMD label to canonical name)
DISEASE_SAMPLE_LABELS = [
    'Dengue Fever',
    'Leptospirosis',
    'Typhoid Fever',
    'Anthrax',
    'Meningococcal Disease',
    'Diarrheal Disease',
    'Hand, Foot, and Mouth Disease',
]
DISEASE_SAMPLE_PROBS = [0.25, 0.20, 0.15, 0.05, 0.10, 0.15, 0.10]

CLIMATE_BY_DISEASE = {
    'Dengue Fever': {'temperature': (27.5, 31.5), 'humidity': (78, 96), 'rainfall': (0.5, 18.0)},
    'Leptospirosis': {'temperature': (25.5, 28.5), 'humidity': (88, 97), 'rainfall': (10.0, 28.0)},
    'Typhoid Fever': {'temperature': (28.0, 31.0), 'humidity': (65, 78), 'rainfall': (0.0, 3.0)},
    'Anthrax': {'temperature': (27.0, 30.0), 'humidity': (60, 75), 'rainfall': (0.0, 2.0)},
    'Meningococcal Disease': {'temperature': (22.0, 26.5), 'humidity': (52, 70), 'rainfall': (0.0, 2.0)},
    'Diarrheal Disease': {'temperature': (28.0, 31.0), 'humidity': (65, 80), 'rainfall': (0.0, 5.0)},
    'Hand, Foot, and Mouth Disease': {'temperature': (27.5, 30.5), 'humidity': (70, 85), 'rainfall': (0.0, 4.0)},
}


def _rand(rng: np.random.Generator) -> float:
    return float(rng.random())


def _generate_symptom_row(disease: str, rng: np.random.Generator) -> dict:
    """Disease-conditioned probabilistic symptom + exposure assignment."""
    row = {col: 0 for col in SYNDROMIC_FEATURE_COLUMNS}

    # Systemic
    row['fever'] = int(
        disease in ('Dengue Fever', 'Leptospirosis', 'Typhoid Fever', 'Meningococcal Disease')
        or _rand(rng) > 0.4
    )
    row['chills'] = int(
        disease in ('Leptospirosis', 'Typhoid Fever') and _rand(rng) > 0.3
    )
    row['diaphoresis'] = int(_rand(rng) > 0.7)
    row['body_malaise'] = int(_rand(rng) > 0.3)
    row['marked_weakness'] = int(
        disease in ('Typhoid Fever', 'Dengue Fever') and _rand(rng) > 0.4
    )
    row['extreme_tiredness'] = int(_rand(rng) > 0.6)
    row['drowsiness'] = int(
        disease == 'Meningococcal Disease' and _rand(rng) > 0.4
    )

    # Pain
    row['headache'] = int(
        disease in ('Dengue Fever', 'Leptospirosis', 'Meningococcal Disease', 'Typhoid Fever')
        and _rand(rng) > 0.2
    )
    row['reticular_pain'] = int(disease == 'Dengue Fever' and _rand(rng) > 0.3)
    row['joint_swelling'] = int(disease == 'Dengue Fever' and _rand(rng) > 0.5)
    row['myalgia'] = int(
        disease in ('Leptospirosis', 'Dengue Fever') and _rand(rng) > 0.2
    )
    row['sore_muscles'] = int(_rand(rng) > 0.6)
    row['neck_stiffness'] = int(
        disease == 'Meningococcal Disease' and _rand(rng) > 0.2
    )
    row['chest_pain'] = int(disease == 'Anthrax' and _rand(rng) > 0.5)

    # GI
    row['anorexia'] = int(
        disease in ('Typhoid Fever', 'Diarrheal Disease') and _rand(rng) > 0.3
    )
    row['nausea'] = int(
        disease in ('Typhoid Fever', 'Diarrheal Disease', 'Dengue Fever') and _rand(rng) > 0.3
    )
    row['vomiting'] = int(
        disease in ('Diarrheal Disease', 'Meningococcal Disease') and _rand(rng) > 0.4
    )
    row['hematemesis'] = int(disease == 'Dengue Fever' and _rand(rng) > 0.8)
    row['diarrhea'] = int(
        disease in ('Diarrheal Disease', 'Typhoid Fever') and _rand(rng) > 0.2
    )
    row['loose_watery_stool'] = int(
        disease == 'Diarrheal Disease' and _rand(rng) > 0.3
    )
    row['bloody_diarrhea'] = int(
        disease in ('Diarrheal Disease', 'Anthrax') and _rand(rng) > 0.7
    )
    row['mucus_in_stool'] = int(disease == 'Diarrheal Disease' and _rand(rng) > 0.6)
    row['tenesmus'] = int(disease == 'Diarrheal Disease' and _rand(rng) > 0.6)
    row['abdominal_discomfort'] = int(
        disease in ('Typhoid Fever', 'Diarrheal Disease') and _rand(rng) > 0.3
    )
    row['abdominal_colic'] = int(disease == 'Diarrheal Disease' and _rand(rng) > 0.5)
    row['constipation'] = int(disease == 'Typhoid Fever' and _rand(rng) > 0.5)
    row['thirst'] = int(disease == 'Diarrheal Disease' and _rand(rng) > 0.4)
    row['dry_moist_lips'] = int(disease == 'Diarrheal Disease' and _rand(rng) > 0.4)

    # Skin / vascular
    row['rash'] = int(
        disease in ('Dengue Fever', 'Hand, Foot, and Mouth Disease') and _rand(rng) > 0.3
    )
    row['petechiae'] = int(
        disease in ('Dengue Fever', 'Meningococcal Disease') and _rand(rng) > 0.4
    )
    row['ecchymoses'] = int(disease == 'Dengue Fever' and _rand(rng) > 0.7)
    row['easy_bruisability'] = int(disease == 'Dengue Fever' and _rand(rng) > 0.6)
    row['epistaxis_bleeding'] = int(disease == 'Dengue Fever' and _rand(rng) > 0.7)
    row['painless_skin_lesion'] = int(disease == 'Anthrax' and _rand(rng) > 0.2)
    row['itchy_skin'] = int(
        disease in ('Hand, Foot, and Mouth Disease', 'Dengue Fever') and _rand(rng) > 0.5
    )
    row['vesicle_mouth_ulcers'] = int(
        disease == 'Hand, Foot, and Mouth Disease' and _rand(rng) > 0.2
    )
    row['conjunctival_suffusion'] = int(disease == 'Leptospirosis' and _rand(rng) > 0.2)
    row['jaundice'] = int(disease == 'Leptospirosis' and _rand(rng) > 0.4)

    # Respiratory
    row['dry_cough'] = int(disease == 'Anthrax' and _rand(rng) > 0.5)
    row['sore_throat'] = int(
        disease in ('Hand, Foot, and Mouth Disease', 'Anthrax') and _rand(rng) > 0.4
    )
    row['runny_nose'] = int(_rand(rng) > 0.8)
    row['trouble_breathing'] = int(disease == 'Anthrax' and _rand(rng) > 0.5)
    row['trouble_swallowing'] = int(
        disease in ('Anthrax', 'Hand, Foot, and Mouth Disease') and _rand(rng) > 0.6
    )

    # Neurological
    row['seizure'] = int(disease == 'Meningococcal Disease' and _rand(rng) > 0.6)
    row['altered_consciousness'] = int(
        disease == 'Meningococcal Disease' and _rand(rng) > 0.5
    )
    row['severe_restlessness'] = int(_rand(rng) > 0.8)
    row['acute_flaccid_paralysis'] = int(
        disease == 'Hand, Foot, and Mouth Disease' and _rand(rng) > 0.8
    )
    row['tourniquet_test_positive'] = int(disease == 'Dengue Fever' and _rand(rng) > 0.3)

    # Group E exposure (gating features)
    row['has_flood_exposure'] = int(disease == 'Leptospirosis' and _rand(rng) > 0.15)
    row['has_stagnant_water'] = int(disease == 'Dengue Fever' and _rand(rng) > 0.2)
    row['has_animal_contact'] = int(
        disease in ('Leptospirosis', 'Anthrax') and _rand(rng) > 0.3
    )
    row['has_livestock_wool_hides'] = int(disease == 'Anthrax' and _rand(rng) > 0.2)
    row['has_contaminated_food_water'] = int(
        disease in ('Typhoid Fever', 'Diarrheal Disease') and _rand(rng) > 0.2
    )
    row['has_recent_travel'] = int(_rand(rng) > 0.7)
    row['has_known_community_cases'] = int(
        disease in ('Meningococcal Disease', 'Hand, Foot, and Mouth Disease', 'Dengue Fever')
        and _rand(rng) > 0.4
    )

    return row


def _attach_context(row: dict, disease: str, rng: np.random.Generator, start: date, end: date) -> dict:
    row['age'] = int(rng.integers(1, 73))
    row['sex'] = rng.choice(['Male', 'Female'])
    row['barangay'] = str(rng.choice(BARANGAYS))
    day_offset = int(rng.integers(0, max((end - start).days, 1)))
    row['submission_date'] = (start + timedelta(days=day_offset)).isoformat()
    climate = CLIMATE_BY_DISEASE.get(disease, CLIMATE_BY_DISEASE['Typhoid Fever'])
    row['temperature'] = round(float(rng.uniform(*climate['temperature'])), 1)
    row['humidity'] = round(float(rng.uniform(*climate['humidity'])), 1)
    row['rainfall'] = round(float(rng.uniform(*climate['rainfall'])), 2)
    row[TARGET_COLUMN] = disease
    return row


def build_historical_training_dataframe(
    *,
    num_samples: int = NUM_SAMPLES,
    random_seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    rng = np.random.default_rng(random_seed)
    end = date.today()
    start = end - timedelta(days=365)

    y_labels = rng.choice(DISEASE_SAMPLE_LABELS, size=num_samples, p=DISEASE_SAMPLE_PROBS)
    records = []
    for disease in y_labels:
        row = _generate_symptom_row(str(disease), rng)
        records.append(_attach_context(row, str(disease), rng, start, end))

    column_order = (
        ['age', 'sex', 'barangay', 'submission_date', 'temperature', 'humidity', 'rainfall']
        + list(SYNDROMIC_FEATURE_COLUMNS)
        + [TARGET_COLUMN]
    )
    return ensure_climate_columns(pd.DataFrame(records)[column_order])


def save_historical_training_csv(
    path: Path = OUTPUT_CSV,
    *,
    also_write_pidsr_copy: bool = True,
    **kwargs,
) -> pd.DataFrame:
    df = build_historical_training_dataframe(**kwargs)
    df.to_csv(path, index=False)
    if also_write_pidsr_copy:
        df.to_csv(PIDSR_CSV, index=False)
    return df


if __name__ == '__main__':
    frame = save_historical_training_csv()
    print('=' * 72)
    print('PULSE PIDSR Training Data Generator')
    print('=' * 72)
    print(f'Rows generated : {len(frame)}')
    print(f'Symptom features: {len(SYNDROMIC_FEATURE_COLUMNS)} (48 clinical + 7 exposure)')
    print(f'Disease classes : {len(DISEASE_LABELS)}')
    print(f'Output (ML pipe): {OUTPUT_CSV}')
    print(f'Output (PIDSR)  : {PIDSR_CSV}')
    print('\nClass distribution:')
    print(frame[TARGET_COLUMN].value_counts().to_string())
    print('=' * 72)
