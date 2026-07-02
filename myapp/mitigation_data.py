"""
Canonical mitigation protocol seed data for PULSE-AI disease response tracks.

Each row maps to ``MitigationProtocol`` and is keyed by ``disease_label`` for
dynamic lookup from map popups, sidebars, and APTAS alert workflows.
"""

MITIGATION_PROTOCOLS = [
    # ── Dengue ───────────────────────────────────────────────────────
    {
        'disease_label': 'Dengue',
        'action_text': (
            'Clear stagnant standing water containers and cut down long weeds '
            'acting as mosquito resting sites.'
        ),
        'priority': 'high',
        'action_category': 'environmental',
        'sort_order': 1,
    },
    {
        'disease_label': 'Dengue',
        'action_text': 'Apply safe larvicides to permanent community water storage setups.',
        'priority': 'medium',
        'action_category': 'environmental',
        'sort_order': 2,
    },
    {
        'disease_label': 'Dengue',
        'action_text': (
            'Mobilize BHWs to conduct structural 4S inspections and distribute bed nets.'
        ),
        'priority': 'high',
        'action_category': 'logistical',
        'sort_order': 3,
    },
    {
        'disease_label': 'Dengue',
        'action_text': (
            'Broadcast community SMS alerts advising residents to wear protective clothing.'
        ),
        'priority': 'medium',
        'action_category': 'public_warning',
        'sort_order': 4,
    },
    # ── Leptospirosis ────────────────────────────────────────────────
    {
        'disease_label': 'Leptospirosis',
        'action_text': (
            'Coordinate immediate rodent control sweeps in public markets and trash sectors.'
        ),
        'priority': 'high',
        'action_category': 'environmental',
        'sort_order': 1,
    },
    {
        'disease_label': 'Leptospirosis',
        'action_text': (
            'Dispatch prophylactic Doxycycline capsules to exposed individuals '
            'at the health center.'
        ),
        'priority': 'high',
        'action_category': 'medical',
        'sort_order': 2,
    },
    {
        'disease_label': 'Leptospirosis',
        'action_text': 'Clear clogged neighborhood drainage channels to lower flood levels.',
        'priority': 'medium',
        'action_category': 'environmental',
        'sort_order': 3,
    },
    {
        'disease_label': 'Leptospirosis',
        'action_text': (
            'Issue explicit public warnings to avoid wading or swimming in floodwaters.'
        ),
        'priority': 'high',
        'action_category': 'public_warning',
        'sort_order': 4,
    },
    # ── Acute Gastroenteritis ──────────────────────────────────────────
    {
        'disease_label': 'Acute Gastroenteritis',
        'action_text': (
            'Issue an immediate Boil Water Advisory for the affected Barangay coordinates.'
        ),
        'priority': 'high',
        'action_category': 'public_warning',
        'sort_order': 1,
    },
    {
        'disease_label': 'Acute Gastroenteritis',
        'action_text': (
            'Dispatch sanitarians to collect deep well and water pump samples '
            'for coliform testing.'
        ),
        'priority': 'high',
        'action_category': 'logistical',
        'sort_order': 2,
    },
    {
        'disease_label': 'Acute Gastroenteritis',
        'action_text': (
            'Deploy bulk quantities of Oral Rehydration Salts (ORS) and Zinc to local clinics.'
        ),
        'priority': 'high',
        'action_category': 'medical',
        'sort_order': 3,
    },
    {
        'disease_label': 'Acute Gastroenteritis',
        'action_text': (
            'Enforce strict food safety and hand hygiene campaigns at local neighborhood stalls.'
        ),
        'priority': 'medium',
        'action_category': 'public_warning',
        'sort_order': 4,
    },
    # ── Respiratory Illness ────────────────────────────────────────────
    {
        'disease_label': 'Respiratory Illness',
        'action_text': (
            'Implement temporary mandatory masking zones in public indoor spaces and schools.'
        ),
        'priority': 'high',
        'action_category': 'public_warning',
        'sort_order': 1,
    },
    {
        'disease_label': 'Respiratory Illness',
        'action_text': (
            'Advise symptomatic individuals to undergo a 5-to-7 day home isolation protocol.'
        ),
        'priority': 'medium',
        'action_category': 'medical',
        'sort_order': 2,
    },
    {
        'disease_label': 'Respiratory Illness',
        'action_text': (
            'Pre-position influenza therapeutics and respiratory testing swabs at the local clinic.'
        ),
        'priority': 'medium',
        'action_category': 'logistical',
        'sort_order': 3,
    },
    # ── Hand, Foot, and Mouth Disease ──────────────────────────────────
    {
        'disease_label': 'Hand, Foot, and Mouth Disease',
        'action_text': (
            'Enforce rigorous chlorine-based decontamination of surfaces, toys, and doorknobs.'
        ),
        'priority': 'high',
        'action_category': 'environmental',
        'sort_order': 1,
    },
    {
        'disease_label': 'Hand, Foot, and Mouth Disease',
        'action_text': (
            'Implement temporary classroom suspensions for daycare centers showing active clusters.'
        ),
        'priority': 'high',
        'action_category': 'logistical',
        'sort_order': 2,
    },
    {
        'disease_label': 'Hand, Foot, and Mouth Disease',
        'action_text': (
            "Train daycare staff to conduct visual checks on children's hands, feet, and mouths."
        ),
        'priority': 'medium',
        'action_category': 'medical',
        'sort_order': 3,
    },
]


def seed_mitigation_protocols(verbose=True):
    """Idempotently load all disease mitigation protocols."""
    from myapp.models import MitigationProtocol

    created = updated = 0
    for row in MITIGATION_PROTOCOLS:
        _, was_created = MitigationProtocol.objects.update_or_create(
            disease_label=row['disease_label'],
            sort_order=row['sort_order'],
            defaults={
                'action_text': row['action_text'],
                'priority': row['priority'],
                'action_category': row['action_category'],
                'is_active': True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    if verbose:
        total = MitigationProtocol.objects.count()
        tracks = MitigationProtocol.objects.values_list('disease_label', flat=True).distinct().count()
        print(
            f'Mitigation seed complete: {created} created, {updated} updated '
            f'({total} protocols across {tracks} disease tracks).'
        )
    return created, updated
