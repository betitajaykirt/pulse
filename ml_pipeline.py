"""
PULSE Health Surveillance — ML pipeline (backward-compatible facade).

Core inference lives in ``ml_engine.py``; this module re-exports the public API
used by notebooks, tests, and legacy imports.
"""
from ml_engine import *  # noqa: F403
from reports.pidsr_schema import (
    DISEASE_LABELS,
    GROUP_A_SYSTEMIC,
    GROUP_B_PAIN,
    GROUP_C_GI,
    GROUP_D_SKIN_VASCULAR,
    GROUP_E_EXPOSURE,
    GROUP_N_NEUROLOGICAL,
    GROUP_R_RESPIRATORY,
    INCONCLUSIVE_SYNDROMIC_LABEL,
    SYNDROMIC_FEATURE_COLUMNS,
)

# Legacy aliases for notebooks / seed scripts
GROUP_A_SYMPTOMS = GROUP_A_SYSTEMIC
GROUP_B_SYMPTOMS = GROUP_B_PAIN
GROUP_C_SYMPTOMS = GROUP_C_GI
GROUP_D_SYMPTOMS = GROUP_D_SKIN_VASCULAR
GROUP_R_SYMPTOMS = GROUP_R_RESPIRATORY
GROUP_N_SYMPTOMS = GROUP_N_NEUROLOGICAL
GROUP_E_SYMPTOMS = GROUP_E_EXPOSURE


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
    rows[2]['disease_label'] = 'Acute Bloody Diarrhea'
    return ensure_climate_columns(pd.DataFrame(rows))
