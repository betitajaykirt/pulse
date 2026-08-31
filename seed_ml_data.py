#!/usr/bin/env python
"""
PULSE PIDSR Historical Training Data Generator.

Builds a synthetic corpus using disease-specific symptom and
Group E exposure probabilities for PIDSR Category I and II diseases.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from ml_engine import TARGET_COLUMN, ensure_climate_columns
from reports.pidsr_schema import DISEASE_LABELS, SYNDROMIC_FEATURE_COLUMNS

RANDOM_SEED = 42
SAMPLES_PER_CLASS = 300
NUM_SAMPLES = SAMPLES_PER_CLASS * len(DISEASE_LABELS)
OUTPUT_CSV = Path(__file__).resolve().parent / 'historical_training_data.csv'
PIDSR_CSV = Path(__file__).resolve().parent / 'pidsr_ml_training_data.csv'

BARANGAYS = [
    'Poblacion', 'Ma-ao', 'Balingasag', 'Taloc', 'Alijis', 'Lag-asan',
    'Malingin', 'Pacol', 'Sagasa', 'Tabunan', 'Abuanan', 'Busay', 'Caridad',
]

# high = likely present, medium = sometimes, exposure = Group E flags
DISEASE_PROFILES = {
    'Acute Flaccid Paralysis': {
        'high': ['acute_flaccid_paralysis', 'marked_weakness'],
        'medium': ['fever', 'tingling_numbness', 'muscle_spasms'],
        'exposure': ['has_known_community_cases'],
        'climate': {'temperature': (26.0, 30.0), 'humidity': (70, 88), 'rainfall': (0.0, 6.0)},
    },
    'Adverse Event Following Immunization': {
        'high': ['fever', 'injection_site_reaction'],
        'medium': ['rash', 'body_malaise', 'vomiting', 'severe_restlessness'],
        'exposure': ['recent_immunization'],
        'climate': {'temperature': (26.0, 31.0), 'humidity': (60, 80), 'rainfall': (0.0, 4.0)},
    },
    'Anthrax': {
        'high': ['painless_skin_lesion', 'fever', 'chest_pain'],
        'medium': ['trouble_breathing', 'sore_throat', 'bloody_diarrhea', 'hemoptysis'],
        'exposure': ['has_livestock_wool_hides', 'has_animal_contact'],
        'climate': {'temperature': (27.0, 30.0), 'humidity': (60, 75), 'rainfall': (0.0, 2.0)},
    },
    'COVID-19': {
        'high': ['fever', 'dry_cough', 'loss_of_smell_taste'],
        'medium': ['sore_throat', 'trouble_breathing', 'body_malaise', 'headache', 'runny_nose'],
        'exposure': ['has_known_community_cases', 'has_recent_travel'],
        'climate': {'temperature': (26.0, 31.0), 'humidity': (65, 85), 'rainfall': (0.0, 8.0)},
    },
    'Hand, Foot, and Mouth Disease': {
        'high': ['vesicle_mouth_ulcers', 'palmar_plantar_vesicles', 'fever'],
        'medium': ['rash', 'itchy_skin', 'sore_throat', 'anorexia'],
        'exposure': ['has_known_community_cases'],
        'climate': {'temperature': (27.5, 30.5), 'humidity': (70, 85), 'rainfall': (0.0, 4.0)},
    },
    'Human Avian Influenza': {
        'high': ['fever', 'dry_cough', 'trouble_breathing'],
        'medium': ['sore_throat', 'body_malaise', 'diarrhea', 'conjunctival_suffusion'],
        'exposure': ['poultry_exposure'],
        'climate': {'temperature': (24.0, 29.0), 'humidity': (70, 90), 'rainfall': (0.0, 10.0)},
    },
    'Measles': {
        'high': ['fever', 'rash', 'koplik_spots', 'runny_nose'],
        'medium': ['dry_cough', 'conjunctival_suffusion', 'photophobia'],
        'exposure': ['has_known_community_cases'],
        'climate': {'temperature': (26.0, 31.0), 'humidity': (60, 80), 'rainfall': (0.0, 5.0)},
    },
    'Meningococcal Disease': {
        'high': ['fever', 'neck_stiffness', 'headache', 'petechiae'],
        'medium': ['drowsiness', 'seizure', 'altered_consciousness', 'photophobia', 'vomiting'],
        'exposure': ['has_known_community_cases'],
        'climate': {'temperature': (22.0, 26.5), 'humidity': (52, 70), 'rainfall': (0.0, 2.0)},
    },
    'Middle East Respiratory Syndrome': {
        'high': ['fever', 'dry_cough', 'trouble_breathing'],
        'medium': ['sore_throat', 'diarrhea', 'body_malaise', 'headache'],
        'exposure': ['has_recent_travel', 'has_animal_contact'],
        'climate': {'temperature': (28.0, 36.0), 'humidity': (30, 55), 'rainfall': (0.0, 1.0)},
    },
    'Neonatal Tetanus': {
        'high': ['inability_to_suck', 'trismus', 'muscle_spasms'],
        'medium': ['severe_restlessness', 'fever'],
        'exposure': ['unhygienic_cord_care'],
        'climate': {'temperature': (26.0, 31.0), 'humidity': (70, 90), 'rainfall': (0.0, 8.0)},
    },
    'Paralytic Shellfish Poisoning': {
        'high': ['tingling_numbness', 'acute_flaccid_paralysis', 'vomiting'],
        'medium': ['nausea', 'trouble_breathing', 'headache'],
        'exposure': ['shellfish_ingestion'],
        'climate': {'temperature': (27.0, 31.0), 'humidity': (70, 90), 'rainfall': (0.0, 6.0)},
    },
    'Rabies': {
        'high': ['hydrophobia', 'muscle_spasms', 'altered_consciousness'],
        'medium': ['fever', 'tingling_numbness', 'severe_restlessness', 'trouble_swallowing'],
        'exposure': ['animal_bite', 'has_animal_contact'],
        'climate': {'temperature': (26.0, 31.0), 'humidity': (65, 85), 'rainfall': (0.0, 6.0)},
    },
    'Severe Acute Respiratory Syndrome': {
        'high': ['fever', 'dry_cough', 'trouble_breathing'],
        'medium': ['headache', 'body_malaise', 'diarrhea', 'chills'],
        'exposure': ['has_recent_travel', 'has_known_community_cases'],
        'climate': {'temperature': (24.0, 30.0), 'humidity': (60, 85), 'rainfall': (0.0, 8.0)},
    },
    'Acute Bloody Diarrhea': {
        'high': ['bloody_diarrhea', 'fever', 'abdominal_colic'],
        'medium': ['diarrhea', 'tenesmus', 'mucus_in_stool', 'thirst'],
        'exposure': ['has_contaminated_food_water'],
        'climate': {'temperature': (28.0, 31.0), 'humidity': (65, 80), 'rainfall': (0.0, 5.0)},
    },
    'Acute Encephalitis Syndrome': {
        'high': ['fever', 'altered_consciousness', 'seizure'],
        'medium': ['headache', 'neck_stiffness', 'photophobia', 'vomiting'],
        'exposure': ['has_known_community_cases'],
        'climate': {'temperature': (26.0, 31.0), 'humidity': (70, 90), 'rainfall': (2.0, 15.0)},
    },
    'Acute Hemorrhagic Fever Syndrome': {
        'high': ['fever', 'petechiae', 'epistaxis_bleeding', 'gum_bleeding'],
        'medium': ['ecchymoses', 'easy_bruisability', 'hematemesis', 'body_malaise'],
        'exposure': ['has_stagnant_water', 'has_recent_travel'],
        'climate': {'temperature': (27.0, 32.0), 'humidity': (75, 95), 'rainfall': (1.0, 20.0)},
    },
    'Acute Viral Hepatitis': {
        'high': ['jaundice', 'dark_urine', 'anorexia'],
        'medium': ['pale_stools', 'right_upper_quadrant_pain', 'nausea', 'fever', 'extreme_tiredness'],
        'exposure': ['has_contaminated_food_water'],
        'climate': {'temperature': (26.0, 31.0), 'humidity': (65, 85), 'rainfall': (0.0, 8.0)},
    },
    'Bacterial Meningitis': {
        'high': ['fever', 'neck_stiffness', 'headache'],
        'medium': ['photophobia', 'altered_consciousness', 'vomiting', 'seizure'],
        'exposure': ['has_known_community_cases'],
        'climate': {'temperature': (24.0, 29.0), 'humidity': (55, 75), 'rainfall': (0.0, 4.0)},
    },
    'Cholera': {
        'high': ['rice_water_stool', 'loose_watery_stool', 'thirst'],
        'medium': ['vomiting', 'dry_moist_lips', 'marked_weakness', 'diarrhea'],
        'exposure': ['has_contaminated_food_water'],
        'climate': {'temperature': (28.0, 32.0), 'humidity': (70, 90), 'rainfall': (2.0, 18.0)},
    },
    'Dengue Fever': {
        'high': ['fever', 'headache', 'reticular_pain', 'myalgia', 'tourniquet_test_positive'],
        'medium': ['rash', 'petechiae', 'nausea', 'joint_swelling', 'gum_bleeding'],
        'exposure': ['has_stagnant_water'],
        'climate': {'temperature': (27.5, 31.5), 'humidity': (78, 96), 'rainfall': (0.5, 18.0)},
    },
    'Diphtheria': {
        'high': ['sore_throat', 'bull_neck', 'trouble_swallowing'],
        'medium': ['fever', 'stridor', 'dry_cough'],
        'exposure': ['has_known_community_cases'],
        'climate': {'temperature': (24.0, 29.0), 'humidity': (55, 75), 'rainfall': (0.0, 4.0)},
    },
    'Influenza-Like Illness': {
        'high': ['fever', 'dry_cough', 'sore_throat'],
        'medium': ['runny_nose', 'myalgia', 'headache', 'body_malaise'],
        'exposure': ['has_known_community_cases'],
        'climate': {'temperature': (23.0, 28.0), 'humidity': (55, 75), 'rainfall': (0.0, 6.0)},
    },
    'Leptospirosis': {
        'high': ['fever', 'chills', 'myalgia', 'conjunctival_suffusion'],
        'medium': ['jaundice', 'headache', 'sore_muscles', 'nausea'],
        'exposure': ['has_flood_exposure', 'has_stagnant_water'],
        'climate': {'temperature': (25.5, 28.5), 'humidity': (88, 97), 'rainfall': (10.0, 28.0)},
    },
    'Malaria': {
        'high': ['fever', 'chills', 'diaphoresis'],
        'medium': ['headache', 'body_malaise', 'nausea', 'extreme_tiredness'],
        'exposure': ['has_recent_travel', 'has_stagnant_water'],
        'climate': {'temperature': (26.0, 32.0), 'humidity': (75, 95), 'rainfall': (2.0, 20.0)},
    },
    'Non-Neonatal Tetanus': {
        'high': ['trismus', 'muscle_spasms'],
        'medium': ['trouble_swallowing', 'severe_restlessness', 'chest_pain'],
        'exposure': ['has_animal_contact'],
        'climate': {'temperature': (26.0, 31.0), 'humidity': (65, 85), 'rainfall': (0.0, 8.0)},
    },
    'Pertussis': {
        'high': ['cough_paroxysms', 'post_tussive_vomiting'],
        'medium': ['dry_cough', 'runny_nose', 'fever'],
        'exposure': ['has_known_community_cases'],
        'climate': {'temperature': (24.0, 29.0), 'humidity': (60, 80), 'rainfall': (0.0, 5.0)},
    },
    'Typhoid and Paratyphoid Fever': {
        'high': ['fever', 'headache', 'anorexia', 'constipation'],
        'medium': ['abdominal_discomfort', 'diarrhea', 'marked_weakness', 'nausea'],
        'exposure': ['has_contaminated_food_water'],
        'climate': {'temperature': (28.0, 31.0), 'humidity': (65, 78), 'rainfall': (0.0, 3.0)},
    },
}


def _rand(rng: np.random.Generator) -> float:
    return float(rng.random())


def _generate_symptom_row(disease: str, rng: np.random.Generator) -> dict:
    row = {col: 0 for col in SYNDROMIC_FEATURE_COLUMNS}
    profile = DISEASE_PROFILES.get(disease, {})
    high = set(profile.get('high') or ())
    medium = set(profile.get('medium') or ())
    exposure = set(profile.get('exposure') or ())

    for col in SYNDROMIC_FEATURE_COLUMNS:
        if col in high:
            row[col] = int(_rand(rng) > 0.18)
        elif col in medium:
            row[col] = int(_rand(rng) > 0.45)
        elif col in exposure:
            row[col] = int(_rand(rng) > 0.22)
        else:
            row[col] = int(_rand(rng) > 0.97)
    return row


def _attach_context(row: dict, disease: str, rng: np.random.Generator, start: date, end: date) -> dict:
    row['age'] = int(rng.integers(1, 73))
    if disease == 'Neonatal Tetanus':
        row['age'] = 0
    elif disease == 'Hand, Foot, and Mouth Disease':
        row['age'] = int(rng.integers(1, 13))
    elif disease == 'Pertussis':
        row['age'] = int(rng.integers(0, 10))
    row['sex'] = rng.choice(['Male', 'Female'])
    row['barangay'] = str(rng.choice(BARANGAYS))
    day_offset = int(rng.integers(0, max((end - start).days, 1)))
    row['submission_date'] = (start + timedelta(days=day_offset)).isoformat()
    climate = DISEASE_PROFILES.get(disease, {}).get('climate') or {
        'temperature': (26.0, 31.0),
        'humidity': (65, 85),
        'rainfall': (0.0, 6.0),
    }
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
    labels = list(DISEASE_LABELS)
    per_class = max(int(num_samples // max(len(labels), 1)), 1)
    records = []
    for disease in labels:
        for _ in range(per_class):
            row = _generate_symptom_row(str(disease), rng)
            records.append(_attach_context(row, str(disease), rng, start, end))
    remainder = int(num_samples) - len(records)
    if remainder > 0:
        extra = rng.choice(labels, size=remainder)
        for disease in extra:
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
    print(f'Symptom features: {len(SYNDROMIC_FEATURE_COLUMNS)}')
    print(f'Per class      : {SAMPLES_PER_CLASS}')
    print(f'Output (ML pipe): {OUTPUT_CSV}')
    print(f'Output (PIDSR)  : {PIDSR_CSV}')
    print('\nClass distribution:')
    print(frame[TARGET_COLUMN].value_counts().to_string())
    print('=' * 72)
