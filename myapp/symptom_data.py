"""Canonical PIDSR symptom seed data — maps ML codes to syndromic groups A–E."""

from myapp.models import PIDSR_SYMPTOM_LABELS

# Stable ML/API identifier → syndromic group letter
SYMPTOM_CODE_TO_GROUP = {
    # Group A: Systemic & Constitutional
    'fever_high': 'A',
    'fever_low': 'A',
    'fever_step_ladder': 'A',
    'chills': 'A',
    'headache': 'A',
    'body_ache': 'A',
    'calf_tenderness': 'A',
    'fatigue': 'A',
    'limb_weakness': 'A',
    'body_spasms': 'A',
    # Group B: Respiratory & ENT
    'cough_dry': 'B',
    'cough_paroxysms': 'B',
    'inspiratory_whoop': 'B',
    'sore_throat': 'B',
    'runny_nose': 'B',
    'conjunctivitis': 'B',
    'conjunctival_suffusion': 'B',
    'dyspnea': 'B',
    'throat_pseudomembrane': 'B',
    'bull_neck': 'B',
    # Group C: Gastrointestinal & Hepatic
    'diarrhea_watery': 'C',
    'diarrhea_bloody': 'C',
    'vomiting': 'C',
    'post_tussive_vomiting': 'C',
    'abdominal_cramps': 'C',
    'jaundice': 'C',
    'dark_urine': 'C',
    # Group D: Dermatological & Specialized Triggers
    'mouth_sores': 'D',
    'hand_foot_blisters': 'D',
    'maculopapular_rash': 'D',
    'petechiae_bleeding': 'D',
    'black_eschar': 'D',
    'hydrophobia': 'D',
    # Group E: Contextual Exposure
    'animal_bite': 'E',
    'floodwater_exposure': 'E',
    'endemic_travel': 'E',
    'poultry_exposure': 'E',
    'post_vaccine': 'E',
    'neonatal_suck_failure': 'E',
}

SYNDROMIC_GROUP_TITLES = {
    'A': 'Systemic & Constitutional',
    'B': 'Respiratory & ENT',
    'C': 'Gastrointestinal & Hepatic',
    'D': 'Dermatological & Specialized Triggers',
    'E': 'Contextual Exposure Checkboxes (ML Features)',
}


def seed_all_symptoms(verbose=True):
    """
    Idempotently populate the ``Symptom`` table from PIDSR reference data.

    Safe to run on every deploy: uses ``update_or_create`` keyed by ``code``.
    """
    from myapp.models import Symptom

    created = updated = 0
    for code, group in SYMPTOM_CODE_TO_GROUP.items():
        name = PIDSR_SYMPTOM_LABELS.get(code, code.replace('_', ' ').title())
        _, was_created = Symptom.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'syndromic_group': group,
                'description': '',
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    if verbose:
        print(f'Symptom seed complete: {created} created, {updated} updated '
              f'({Symptom.objects.count()} total).')
    return created, updated
