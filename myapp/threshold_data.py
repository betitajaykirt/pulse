"""
PIDSR disease → category mapping and default threshold seed data.
"""

from reports.pidsr_schema import DISEASE_LABELS, PIDSR_CATEGORY_I, PIDSR_CATEGORY_II

# Maps ML / syndrome labels to PIDSR surveillance category levels
DISEASE_PIDSR_CATEGORY = {
    **{label: 'Category 1' for label in PIDSR_CATEGORY_I},
    **{label: 'Category 2' for label in PIDSR_CATEGORY_II},
    'Dengue': 'Category 2',
    'Typhoid Fever': 'Category 2',
    'Diarrheal Disease': 'Category 2',
    'Hand, Foot and Mouth Disease (HFMD)': 'Category 1',
    'Respiratory Illness': 'Category 2',
    'Acute Gastroenteritis': 'Category 2',
    'Polio': 'Category 1',
    'Influenza-like Illness (ILI)': 'Category 2',
    'AEFI': 'Category 1',
    'AFP': 'Category 1',
    'PSP': 'Category 1',
    'MERS': 'Category 1',
    'SARS': 'Category 1',
    'Inconclusive Syndromic Pattern': 'Category 2',
    'Insufficient Data for Prediction': 'Category 2',
}

DEFAULT_THRESHOLD_ROWS = [
    {
        'category_level': 'Category 1',
        'warning_threshold': 1,
        'outbreak_threshold': 1,
        'time_window_days': 7,
    },
    {
        'category_level': 'Category 2',
        'warning_threshold': 2,
        'outbreak_threshold': 3,
        'time_window_days': 7,
    },
]


def resolve_pidsr_category(disease_label: str) -> str:
    """Return PIDSR category level for a disease label (defaults to Category 2)."""
    if not disease_label:
        return 'Category 2'
    return DISEASE_PIDSR_CATEGORY.get(disease_label.strip(), 'Category 2')


def seed_disease_category_thresholds(verbose=True):
    from myapp.models import DiseaseCategoryThreshold

    created = updated = 0
    for row in DEFAULT_THRESHOLD_ROWS:
        _, was_created = DiseaseCategoryThreshold.objects.update_or_create(
            category_level=row['category_level'],
            defaults={
                'warning_threshold': row['warning_threshold'],
                'outbreak_threshold': row['outbreak_threshold'],
                'time_window_days': row['time_window_days'],
                'is_active': True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    if verbose:
        print(
            f'Threshold seed complete: {created} created, {updated} updated '
            f'({DiseaseCategoryThreshold.objects.count()} active configs).'
        )
    return created, updated


# Legacy outbreak-threshold labels superseded by the full PIDSR disease list
LEGACY_OUTBREAK_LABELS = (
    'Acute Gastroenteritis',
    'Acute Gastroenteritis (AGE)',
    'Dengue',
    'Influenza-like Illness (ILI)',
    'Respiratory Illness',
    'Hand, Foot and Mouth Disease (HFMD)',
    'Diarrheal Disease',
    'Typhoid Fever',
)

# Default per-disease outbreak thresholds (case count / rolling window days)
_CATEGORY_1_CASE_THRESHOLD = 1
_CATEGORY_2_CASE_THRESHOLD = 3
_SPECIAL_CASE_THRESHOLDS = {
    'Meningococcal Disease': 2,
    'Hand, Foot, and Mouth Disease': 5,
    'Bacterial Meningitis': 2,
}

DEFAULT_OUTBREAK_THRESHOLDS = [
    {
        'disease_label': label,
        'case_threshold': _SPECIAL_CASE_THRESHOLDS.get(
            label,
            _CATEGORY_1_CASE_THRESHOLD if label in PIDSR_CATEGORY_I else _CATEGORY_2_CASE_THRESHOLD,
        ),
        'rolling_window_days': 7,
    }
    for label in DISEASE_LABELS
]


def seed_outbreak_thresholds(verbose=True):
    """Sync disease-specific outbreak thresholds to the PIDSR Category I + II list."""
    from myapp.models import OutbreakThreshold

    removed, _ = OutbreakThreshold.objects.filter(
        disease_label__in=LEGACY_OUTBREAK_LABELS,
    ).delete()

    created = updated = 0
    for row in DEFAULT_OUTBREAK_THRESHOLDS:
        _, was_created = OutbreakThreshold.objects.update_or_create(
            disease_label=row['disease_label'],
            defaults={
                'case_threshold': row['case_threshold'],
                'rolling_window_days': row['rolling_window_days'],
                'is_active': True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    if verbose:
        print(
            f'Outbreak threshold seed complete: {created} created, {updated} updated, '
            f'{removed} legacy rows removed '
            f'({OutbreakThreshold.objects.count()} total configs).'
        )
    return created, updated, removed


def outbreak_threshold_display_order():
    """Return disease labels in canonical PIDSR display order."""
    return list(DISEASE_LABELS)
