"""
Official DOH PIDSR symptom catalog and monitored disease labels.

Covers PIDSR Category I and Category II notifiable diseases/syndromes.
Single source of truth for intake forms, ORM validation, and ML feature columns.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Sequence, Tuple

# ---------------------------------------------------------------------------
# Clinical symptom boolean fields (PIDSR Category I + II indicators)
# ---------------------------------------------------------------------------

GROUP_A_SYSTEMIC: Tuple[str, ...] = (
    'fever',
    'chills',
    'diaphoresis',
    'body_malaise',
    'marked_weakness',
    'extreme_tiredness',
    'drowsiness',
    'photophobia',
)

GROUP_B_PAIN: Tuple[str, ...] = (
    'headache',
    'reticular_pain',
    'joint_swelling',
    'myalgia',
    'sore_muscles',
    'neck_stiffness',
    'chest_pain',
    'trismus',
    'right_upper_quadrant_pain',
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
    'dark_urine',
    'pale_stools',
    'rice_water_stool',
    'post_tussive_vomiting',
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
    'koplik_spots',
    'injection_site_reaction',
    'palmar_plantar_vesicles',
    'gum_bleeding',
    'bull_neck',
)

GROUP_R_RESPIRATORY: Tuple[str, ...] = (
    'dry_cough',
    'sore_throat',
    'runny_nose',
    'trouble_breathing',
    'trouble_swallowing',
    'cough_paroxysms',
    'loss_of_smell_taste',
    'hemoptysis',
    'stridor',
)

GROUP_N_NEUROLOGICAL: Tuple[str, ...] = (
    'seizure',
    'altered_consciousness',
    'severe_restlessness',
    'acute_flaccid_paralysis',
    'tourniquet_test_positive',
    'hydrophobia',
    'muscle_spasms',
    'tingling_numbness',
    'inability_to_suck',
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
    'recent_immunization',
    'animal_bite',
    'poultry_exposure',
    'shellfish_ingestion',
    'unhygienic_cord_care',
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
    'photophobia': 'Photophobia (light sensitivity)',
    'headache': 'Headache',
    'reticular_pain': 'Reticular / retro-orbital pain',
    'joint_swelling': 'Joint swelling',
    'myalgia': 'Myalgia',
    'sore_muscles': 'Sore muscles',
    'neck_stiffness': 'Neck stiffness',
    'chest_pain': 'Chest pain',
    'trismus': 'Trismus / lockjaw',
    'right_upper_quadrant_pain': 'Right-upper-quadrant abdominal pain',
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
    'dark_urine': 'Dark urine',
    'pale_stools': 'Pale / clay-colored stools',
    'rice_water_stool': 'Rice-water stool',
    'post_tussive_vomiting': 'Vomiting after coughing spells',
    'rash': 'Rash',
    'petechiae': 'Petechiae',
    'ecchymoses': 'Ecchymoses',
    'easy_bruisability': 'Easy bruisability',
    'epistaxis_bleeding': 'Epistaxis / bleeding',
    'painless_skin_lesion': 'Painless skin lesion / eschar',
    'itchy_skin': 'Itchy skin',
    'vesicle_mouth_ulcers': 'Vesicles / mouth ulcers',
    'conjunctival_suffusion': 'Conjunctival suffusion',
    'jaundice': 'Jaundice',
    'koplik_spots': 'Koplik spots',
    'injection_site_reaction': 'Injection-site swelling / redness',
    'palmar_plantar_vesicles': 'Vesicles on palms or soles',
    'gum_bleeding': 'Bleeding gums',
    'bull_neck': 'Bull neck swelling',
    'dry_cough': 'Dry cough',
    'sore_throat': 'Sore throat',
    'runny_nose': 'Runny nose / coryza',
    'trouble_breathing': 'Trouble breathing',
    'trouble_swallowing': 'Trouble swallowing',
    'cough_paroxysms': 'Coughing paroxysms / whoop',
    'loss_of_smell_taste': 'Loss of smell or taste',
    'hemoptysis': 'Coughing up blood',
    'stridor': 'Stridor / noisy breathing',
    'seizure': 'Seizure',
    'altered_consciousness': 'Altered consciousness',
    'severe_restlessness': 'Severe restlessness / irritability',
    'acute_flaccid_paralysis': 'Acute flaccid paralysis',
    'tourniquet_test_positive': 'Positive tourniquet test',
    'hydrophobia': 'Hydrophobia (fear of water)',
    'muscle_spasms': 'Muscle spasms / rigidity',
    'tingling_numbness': 'Tingling or numbness of limbs',
    'inability_to_suck': 'Inability to suck (newborn)',
    'has_flood_exposure': 'Wading in floodwater, river, canals, or lake',
    'has_stagnant_water': 'Stagnant water / containers nearby',
    'has_animal_contact': 'Contact with rats, swine, cattle, dogs, or raccoons',
    'has_livestock_wool_hides': 'Exposure to livestock wool, hides, or animal products',
    'has_contaminated_food_water': 'Unsafe water, street food, or unboiled water',
    'has_recent_travel': 'Travel to endemic area within 2–12 weeks',
    'has_known_community_cases': 'Contact with similar cases (household / school / daycare)',
    'recent_immunization': 'Immunization within the past 4 weeks',
    'animal_bite': 'Animal bite or scratch',
    'poultry_exposure': 'Contact with poultry or wild birds',
    'shellfish_ingestion': 'Ate shellfish or other seafood before onset',
    'unhygienic_cord_care': 'Unhygienic umbilical cord care (newborn)',
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
    'body_spasms': 'muscle_spasms',
    'calf_tenderness': 'sore_muscles',
    'cough_dry': 'dry_cough',
    'cough_paroxysms': 'cough_paroxysms',
    'dyspnea': 'trouble_breathing',
    'diarrhea_watery': 'loose_watery_stool',
    'diarrhea_bloody': 'bloody_diarrhea',
    'abdominal_cramps': 'abdominal_colic',
    'maculopapular_rash': 'rash',
    'petechiae_bleeding': 'petechiae',
    'mouth_sores': 'vesicle_mouth_ulcers',
    'hand_foot_blisters': 'palmar_plantar_vesicles',
    'black_eschar': 'painless_skin_lesion',
    'hydrophobia': 'hydrophobia',
    'animal_bite': 'animal_bite',
    'floodwater_exposure': 'has_flood_exposure',
    'endemic_travel': 'has_recent_travel',
    'poultry_exposure': 'poultry_exposure',
    'post_vaccine': 'recent_immunization',
    'neonatal_suck_failure': 'inability_to_suck',
}

# ---------------------------------------------------------------------------
# Monitored diseases — full PIDSR Category I + Category II list
# ---------------------------------------------------------------------------

PIDSR_CATEGORY_I: Tuple[str, ...] = (
    'Acute Flaccid Paralysis',
    'Adverse Event Following Immunization',
    'Anthrax',
    'COVID-19',
    'Hand, Foot, and Mouth Disease',
    'Human Avian Influenza',
    'Measles',
    'Meningococcal Disease',
    'Middle East Respiratory Syndrome',
    'Neonatal Tetanus',
    'Paralytic Shellfish Poisoning',
    'Rabies',
    'Severe Acute Respiratory Syndrome',
)

PIDSR_CATEGORY_II: Tuple[str, ...] = (
    'Acute Bloody Diarrhea',
    'Acute Encephalitis Syndrome',
    'Acute Hemorrhagic Fever Syndrome',
    'Acute Viral Hepatitis',
    'Bacterial Meningitis',
    'Cholera',
    'Dengue Fever',
    'Diphtheria',
    'Influenza-Like Illness',
    'Leptospirosis',
    'Malaria',
    'Non-Neonatal Tetanus',
    'Pertussis',
    'Typhoid and Paratyphoid Fever',
)

DISEASE_LABELS: Tuple[str, ...] = PIDSR_CATEGORY_I + PIDSR_CATEGORY_II

DISEASE_ICD10: Dict[str, str] = {
    'Acute Flaccid Paralysis': 'G83.9 / A80',
    'Adverse Event Following Immunization': 'T88.1',
    'Anthrax': 'A22',
    'COVID-19': 'U07.1',
    'Hand, Foot, and Mouth Disease': 'B08.4',
    'Human Avian Influenza': 'J09',
    'Measles': 'B05',
    'Meningococcal Disease': 'A39',
    'Middle East Respiratory Syndrome': 'B34.2',
    'Neonatal Tetanus': 'A33',
    'Paralytic Shellfish Poisoning': 'T61.2',
    'Rabies': 'A82',
    'Severe Acute Respiratory Syndrome': 'U04.9',
    'Acute Bloody Diarrhea': 'A09',
    'Acute Encephalitis Syndrome': 'A86',
    'Acute Hemorrhagic Fever Syndrome': 'A99',
    'Acute Viral Hepatitis': 'B19',
    'Bacterial Meningitis': 'G00.9',
    'Cholera': 'A00',
    'Dengue Fever': 'A90 / A91',
    'Diphtheria': 'A36',
    'Influenza-Like Illness': 'J11',
    'Leptospirosis': 'A27.9',
    'Malaria': 'B54',
    'Non-Neonatal Tetanus': 'A35',
    'Pertussis': 'A37',
    'Typhoid and Paratyphoid Fever': 'A01',
}

INCONCLUSIVE_SYNDROMIC_LABEL = 'Inconclusive Syndromic Pattern'

# Exposure factors that support each disease profile (any match = satisfied)
DISEASE_EXPOSURE_REQUIREMENTS: Dict[str, FrozenSet[str]] = {
    'Leptospirosis': frozenset({'has_flood_exposure', 'has_stagnant_water'}),
    'Anthrax': frozenset({'has_livestock_wool_hides', 'has_animal_contact'}),
    'Typhoid and Paratyphoid Fever': frozenset({'has_contaminated_food_water'}),
    'Acute Bloody Diarrhea': frozenset({'has_contaminated_food_water'}),
    'Cholera': frozenset({'has_contaminated_food_water'}),
    'Hand, Foot, and Mouth Disease': frozenset({'has_known_community_cases'}),
    'Meningococcal Disease': frozenset({'has_known_community_cases'}),
    'Bacterial Meningitis': frozenset({'has_known_community_cases'}),
    'Dengue Fever': frozenset({'has_stagnant_water', 'has_known_community_cases'}),
    'Rabies': frozenset({'animal_bite', 'has_animal_contact'}),
    'Adverse Event Following Immunization': frozenset({'recent_immunization'}),
    'Human Avian Influenza': frozenset({'poultry_exposure'}),
    'Paralytic Shellfish Poisoning': frozenset({'shellfish_ingestion'}),
    'Neonatal Tetanus': frozenset({'unhygienic_cord_care'}),
    'Measles': frozenset({'has_known_community_cases'}),
    'Malaria': frozenset({'has_recent_travel', 'has_stagnant_water'}),
}

EXPOSURE_GATING_CONFIDENCE_CAP = 0.50
EXPOSURE_GATING_PENALTY_FACTOR = 0.65

# Aliases for legacy disease strings in thresholds / mitigation data
LEGACY_DISEASE_LABEL_MAP: Dict[str, str] = {
    'Dengue': 'Dengue Fever',
    'Acute Gastroenteritis': 'Acute Bloody Diarrhea',
    'Acute Gastroenteritis (AGE)': 'Acute Bloody Diarrhea',
    'Diarrheal Disease': 'Acute Bloody Diarrhea',
    'Respiratory Illness': 'Influenza-Like Illness',
    'Influenza-like Illness (ILI)': 'Influenza-Like Illness',
    'Influenza-Like Illness (ILI)': 'Influenza-Like Illness',
    'Hand, Foot and Mouth Disease (HFMD)': 'Hand, Foot, and Mouth Disease',
    'Typhoid Fever': 'Typhoid and Paratyphoid Fever',
    'COVID19': 'COVID-19',
    'Covid-19': 'COVID-19',
    'Avian Influenza': 'Human Avian Influenza',
    'MERS': 'Middle East Respiratory Syndrome',
    'MERS-CoV': 'Middle East Respiratory Syndrome',
    'SARS': 'Severe Acute Respiratory Syndrome',
    'AEFI': 'Adverse Event Following Immunization',
    'AFP': 'Acute Flaccid Paralysis',
    'PSP': 'Paralytic Shellfish Poisoning',
    'HFMD': 'Hand, Foot, and Mouth Disease',
    'Whooping Cough': 'Pertussis',
    'Polio': 'Acute Flaccid Paralysis',
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
    if not label:
        return 'Unknown'
    text = str(label).strip()
    if text in DISEASE_LABELS:
        return text
    if text in LEGACY_DISEASE_LABEL_MAP:
        return LEGACY_DISEASE_LABEL_MAP[text]
    cleaned = text.lower()
    aliases = {
        'dengue': 'Dengue Fever',
        'dengue fever': 'Dengue Fever',
        'typhoid': 'Typhoid and Paratyphoid Fever',
        'typhoid fever': 'Typhoid and Paratyphoid Fever',
        'cholera': 'Cholera',
        'measles': 'Measles',
        'rabies': 'Rabies',
        'malaria': 'Malaria',
        'covid-19': 'COVID-19',
        'covid19': 'COVID-19',
        'pertussis': 'Pertussis',
        'diphtheria': 'Diphtheria',
        'hepatitis': 'Acute Viral Hepatitis',
        'ili': 'Influenza-Like Illness',
    }
    if cleaned in aliases:
        return aliases[cleaned]
    return text
