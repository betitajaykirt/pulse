"""
PIDSR disease → category mapping and default threshold seed data.
"""

# Maps ML / syndrome labels to PIDSR surveillance category levels
DISEASE_PIDSR_CATEGORY = {
    'Dengue': 'Category 2',
    'Respiratory Illness': 'Category 2',
    'Leptospirosis': 'Category 2',
    'Acute Gastroenteritis': 'Category 2',
    'Hand, Foot, and Mouth Disease': 'Category 2',
    'Hand, Foot and Mouth Disease (HFMD)': 'Category 2',
    'Cholera': 'Category 1',
    'Polio': 'Category 1',
    'Rabies': 'Category 1',
    'Influenza-like Illness (ILI)': 'Category 2',
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
