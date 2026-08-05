"""
Official DOH PIDSR symptom catalog and monitored disease labels.

Single source of truth for intake forms, ORM validation, and ML feature columns.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Sequence, Tuple

# ---------------------------------------------------------------------------
# Clinical symptom boolean fields (48 de-duplicated PIDSR indicators)
# ---------------------------------------------------------------------------

GROUP_A_SYSTEMIC: Tuple[str, ...] = (
    'fever',
    'chills',
    'diaphoresis',
    'body_malaise',
    'marked_weakness',
    'extreme_tiredness',
    'drowsiness',
)

GROUP_B_PAIN: Tuple[str, ...] = (
    'headache',
    'reticular_pain',
    'joint_swelling',
    'myalgia',
    'sore_muscles',
    'neck_stiffness',
    'chest_pain',
)

GROUP_C_GI: Tuple[str, ...] = (
    'anorexia',
    'nausea',
    'vomiting',
    'hematemesis',
    'diarrhea',
    'loose_watery_stool',
    'bloody_diarrhea',
    'mucus_in_stool',
    'tenesmus',
    'abdominal_discomfort',
    'abdominal_colic',
    'constipation',
    'thirst',
    'dry_moist_lips',
)

GROUP_D_SKIN_VASCULAR: Tuple[str, ...] = (
    'rash',
    'petechiae',
    'ecchymoses',
    'easy_bruisability',
    'epistaxis_bleeding',
    'painless_skin_lesion',
    'itchy_skin',
    'vesicle_mouth_ulcers',
    'conjunctival_suffusion',
    'jaundice',
)

GROUP_R_RESPIRATORY: Tuple[str, ...] = (
    'dry_cough',
    'sore_throat',
    'runny_nose',
    'trouble_breathing',
    'trouble_swallowing',
)

GROUP_N_NEUROLOGICAL: Tuple[str, ...] = (
    'seizure',
    'altered_consciousness',
    'severe_restlessness',
    'acute_flaccid_paralysis',
    'tourniquet_test_positive',
)

CLINICAL_SYMPTOM_COLUMNS: Tuple[str, ...] = (
    GROUP_A_SYSTEMIC
    + GROUP_B_PAIN
    + GROUP_C_GI
    + GROUP_D_SKIN_VASCULAR
    + GROUP_R_RESPIRATORY
    + GROUP_N_NEUROLOGICAL
)

# Group E — exposure history (distinct ML features)
GROUP_E_EXPOSURE: Tuple[str, ...] = (
    'has_flood_exposure',
    'has_stagnant_water',
    'has_animal_contact',
    'has_livestock_wool_hides',
    'has_contaminated_food_water',
    'has_recent_travel',
    'has_known_community_cases',
)

SYNDROMIC_FEATURE_COLUMNS: Tuple[str, ...] = CLINICAL_SYMPTOM_COLUMNS + GROUP_E_EXPOSURE

SYMPTOM_CODE_TO_GROUP: Dict[str, str] = {
    **{code: 'A' for code in GROUP_A_SYSTEMIC},
    **{code: 'B' for code in GROUP_B_PAIN},
    **{code: 'C' for code in GROUP_C_GI},
    **{code: 'D' for code in GROUP_D_SKIN_VASCULAR},
    **{code: 'R' for code in GROUP_R_RESPIRATORY},
    **{code: 'N' for code in GROUP_N_NEUROLOGICAL},
    **{code: 'E' for code in GROUP_E_EXPOSURE},
}

SYNDROMIC_GROUP_TITLES: Dict[str, str] = {
    'A': 'Systemic',
    'B': 'Pain',
    'C': 'Gastrointestinal (GI)',
    'D': 'Skin / Vascular',
    'R': 'Respiratory',
    'N': 'Neurological',
    'E': 'Group E — Exposure History',
}

PIDSR_SYMPTOM_LABELS: Dict[str, str] = {
    'fever': 'Fever',
    'chills': 'Chills',
    'diaphoresis': 'Diaphoresis (profuse sweating)',
    'body_malaise': 'Body malaise',
    'marked_weakness': 'Marked weakness',
    'extreme_tiredness': 'Extreme tiredness / fatigue',
    'drowsiness': 'Drowsiness',
    'headache': 'Headache',
    'reticular_pain': 'Reticular / retro-orbital pain',
    'joint_swelling': 'Joint swelling',
    'myalgia': 'Myalgia',
    'sore_muscles': 'Sore muscles',
    'neck_stiffness': 'Neck stiffness',
    'chest_pain': 'Chest pain',
    'anorexia': 'Anorexia / loss of appetite',
    'nausea': 'Nausea',
    'vomiting': 'Vomiting',
    'hematemesis': 'Hematemesis (vomiting blood)',
    'diarrhea': 'Diarrhea',
    'loose_watery_stool': 'Loose / watery stool',
    'bloody_diarrhea': 'Bloody diarrhea',
    'mucus_in_stool': 'Mucus in stool',
    'tenesmus': 'Tenesmus',
    'abdominal_discomfort': 'Abdominal discomfort',
    'abdominal_colic': 'Abdominal colic',
    'constipation': 'Constipation',
    'thirst': 'Thirst',
    'dry_moist_lips': 'Dry or moist lips',
    'rash': 'Rash',
    'petechiae': 'Petechiae',
    'ecchymoses': 'Ecchymoses',
    'easy_bruisability': 'Easy bruisability',
    'epistaxis_bleeding': 'Epistaxis / bleeding',
    'painless_skin_lesion': 'Painless skin lesion',
    'itchy_skin': 'Itchy skin',
    'vesicle_mouth_ulcers': 'Vesicles / mouth ulcers',
    'conjunctival_suffusion': 'Conjunctival suffusion',
    'jaundice': 'Jaundice',
    'dry_cough': 'Dry cough',
    'sore_throat': 'Sore throat',
    'runny_nose': 'Runny nose',
    'trouble_breathing': 'Trouble breathing',
    'trouble_swallowing': 'Trouble swallowing',
    'seizure': 'Seizure',
    'altered_consciousness': 'Altered consciousness',
    'severe_restlessness': 'Severe restlessness / irritability',
    'acute_flaccid_paralysis': 'Acute flaccid paralysis',
    'tourniquet_test_positive': 'Positive tourniquet test',
    'has_flood_exposure': 'Wading in floodwater, river, canals, or lake',
    'has_stagnant_water': 'Stagnant water / containers nearby',
    'has_animal_contact': 'Contact with rats, swine, cattle, dogs, or raccoons',
    'has_livestock_wool_hides': 'Exposure to livestock wool, hides, or animal products',
    'has_contaminated_food_water': 'Unsafe water, street food, or unboiled water',
    'has_recent_travel': 'Travel to endemic area within 2–12 weeks',
    'has_known_community_cases': 'Contact with similar cases (household / school / daycare)',
}

PIDSR_SYMPTOM_CODES: FrozenSet[str] = frozenset(SYNDROMIC_FEATURE_COLUMNS)

SYMPTOM_CATEGORY_CODES: Dict[str, FrozenSet[str]] = {
    'systemic': frozenset(GROUP_A_SYSTEMIC),
    'pain': frozenset(GROUP_B_PAIN),
    'gastrointestinal': frozenset(GROUP_C_GI),
    'dermatological': frozenset(GROUP_D_SKIN_VASCULAR),
    'respiratory': frozenset(GROUP_R_RESPIRATORY),
    'neurological': frozenset(GROUP_N_NEUROLOGICAL),
    'exposure': frozenset(GROUP_E_EXPOSURE),
}

SYMPTOM_CATEGORY_GROUP_MAP: Dict[str, Tuple[str, ...]] = {
    'systemic': ('A',),
    'pain': ('B',),
    'gastrointestinal': ('C',),
    'dermatological': ('D',),
    'respiratory': ('R',),
    'neurological': ('N',),
    'exposure': ('E',),
}

# Map legacy catalog codes → unified PIDSR field names
LEGACY_SYMPTOM_CODE_MAP: Dict[str, str] = {
    'fever_high': 'fever',
    'fever_low': 'fever',
    'fever_step_ladder': 'fever',
    'body_ache': 'myalgia',
    'fatigue': 'extreme_tiredness',
    'limb_weakness': 'marked_weakness',
    'body_spasms': 'severe_restlessness',
    'calf_tenderness': 'sore_muscles',
    'cough_dry': 'dry_cough',
    'cough_paroxysms': 'dry_cough',
    'dyspnea': 'trouble_breathing',
    'diarrhea_watery': 'loose_watery_stool',
    'diarrhea_bloody': 'bloody_diarrhea',
    'abdominal_cramps': 'abdominal_colic',
    'maculopapular_rash': 'rash',
    'petechiae_bleeding': 'petechiae',
    'mouth_sores': 'vesicle_mouth_ulcers',
    'hand_foot_blisters': 'vesicle_mouth_ulcers',
    'black_eschar': 'painless_skin_lesion',
    'hydrophobia': 'trouble_swallowing',
    'animal_bite': 'has_animal_contact',
    'floodwater_exposure': 'has_flood_exposure',
    'endemic_travel': 'has_recent_travel',
    'poultry_exposure': 'has_animal_contact',
    'post_vaccine': 'has_known_community_cases',
    'neonatal_suck_failure': 'altered_consciousness',
}

# ---------------------------------------------------------------------------
# Monitored diseases (7 official DOH PIDSR targets)
# ---------------------------------------------------------------------------

DISEASE_LABELS: Tuple[str, ...] = (
    'Dengue Fever',
    'Leptospirosis',
    'Typhoid Fever',
    'Anthrax',
    'Meningococcal Disease',
    'Diarrheal Disease',
    'Hand, Foot, and Mouth Disease',
)

DISEASE_ICD10: Dict[str, str] = {
    'Dengue Fever': 'A90 / A91',
    'Leptospirosis': 'A27.9',
    'Typhoid Fever': 'A01.0',
    'Anthrax': 'A22',
    'Meningococcal Disease': 'A39',
    'Diarrheal Disease': 'A09',
    'Hand, Foot, and Mouth Disease': 'B08.4',
}

INCONCLUSIVE_SYNDROMIC_LABEL = 'Inconclusive Syndromic Pattern'

# Exposure factors that support each disease profile (any match = satisfied)
DISEASE_EXPOSURE_REQUIREMENTS: Dict[str, FrozenSet[str]] = {
    'Leptospirosis': frozenset({'has_flood_exposure', 'has_stagnant_water'}),
    'Anthrax': frozenset({'has_livestock_wool_hides', 'has_animal_contact'}),
    'Typhoid Fever': frozenset({'has_contaminated_food_water'}),
    'Diarrheal Disease': frozenset({'has_contaminated_food_water'}),
    'Hand, Foot, and Mouth Disease': frozenset({'has_known_community_cases'}),
    'Meningococcal Disease': frozenset({'has_known_community_cases'}),
    'Dengue Fever': frozenset({'has_stagnant_water', 'has_known_community_cases'}),
}

EXPOSURE_GATING_CONFIDENCE_CAP = 0.50
EXPOSURE_GATING_PENALTY_FACTOR = 0.65

# Aliases for legacy disease strings in thresholds / mitigation data
LEGACY_DISEASE_LABEL_MAP: Dict[str, str] = {
    'Dengue': 'Dengue Fever',
    'Acute Gastroenteritis': 'Diarrheal Disease',
    'Acute Gastroenteritis (AGE)': 'Diarrheal Disease',
    'Respiratory Illness': 'Meningococcal Disease',
    'Influenza-like Illness (ILI)': 'Meningococcal Disease',
    'Hand, Foot and Mouth Disease (HFMD)': 'Hand, Foot, and Mouth Disease',
}


def normalize_symptom_codes(codes: Sequence[str]) -> list[str]:
    """Map legacy symptom codes to unified PIDSR fields and dedupe."""
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in codes or []:
        code = str(raw).strip()
        if not code:
            continue
        code = LEGACY_SYMPTOM_CODE_MAP.get(code, code)
        if code in seen:
            continue
        if code in PIDSR_SYMPTOM_CODES:
            normalized.append(code)
            seen.add(code)
    return normalized


def normalize_disease_label(label: str) -> str:
    text = (label or '').strip()
    return LEGACY_DISEASE_LABEL_MAP.get(text, text)
