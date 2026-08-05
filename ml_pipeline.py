"""
PULSE Health Surveillance — ML pipeline (backward-compatible facade).

Core inference lives in ``ml_engine.py``; this module re-exports the public API
used by notebooks, tests, and legacy imports.
"""
from ml_engine import *  # noqa: F403
from reports.pidsr_schema import DISEASE_LABELS, INCONCLUSIVE_SYNDROMIC_LABEL, SYNDROMIC_FEATURE_COLUMNS

# Legacy aliases for notebooks / seed scripts
GROUP_A_SYMPTOMS = SYNDROMIC_FEATURE_COLUMNS[:7]
GROUP_B_SYMPTOMS = SYNDROMIC_FEATURE_COLUMNS[7:14]
GROUP_C_SYMPTOMS = SYNDROMIC_FEATURE_COLUMNS[14:28]
GROUP_D_SYMPTOMS = SYNDROMIC_FEATURE_COLUMNS[28:38]
GROUP_R_SYMPTOMS = SYNDROMIC_FEATURE_COLUMNS[38:43]
GROUP_N_SYMPTOMS = SYNDROMIC_FEATURE_COLUMNS[43:48]
GROUP_E_SYMPTOMS = SYNDROMIC_FEATURE_COLUMNS[48:]


def _build_mock_training_set():
    """Minimal labeled corpus when historical_training_data.csv is missing."""
    import pandas as pd
    from ml_engine import ensure_climate_columns, patient_case_to_feature_row

    rows = [
        patient_case_to_feature_row(
            age=14, sex='Female',
            symptom_codes=['fever', 'headache', 'myalgia', 'rash', 'petechiae', 'has_stagnant_water'],
            temperature=29.5, humidity=88.0, rainfall=6.2,
        ),
        patient_case_to_feature_row(
            age=29, sex='Male',
            symptom_codes=['fever', 'chills', 'myalgia', 'jaundice', 'has_flood_exposure'],
            temperature=27.0, humidity=92.0, rainfall=18.5,
        ),
        patient_case_to_feature_row(
            age=5, sex='Male',
            symptom_codes=['loose_watery_stool', 'vomiting', 'abdominal_colic', 'has_contaminated_food_water'],
            temperature=29.0, humidity=75.0, rainfall=1.5,
        ),
    ]
    rows[0]['disease_label'] = 'Dengue Fever'
    rows[1]['disease_label'] = 'Leptospirosis'
    rows[2]['disease_label'] = 'Diarrheal Disease'
    return ensure_climate_columns(pd.DataFrame(rows))
