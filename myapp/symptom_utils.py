"""UI and API helpers for database-driven syndromic symptoms."""

from myapp.symptom_data import SYNDROMIC_GROUP_TITLES


def build_symptom_groups_for_ui():
    """
    Build grouped symptom payload for ``submit_report.html``.

    Symptoms are sorted alphabetically by ``name`` within each syndromic group.
    """
    from myapp.models import Symptom

    grouped = {letter: [] for letter in SYNDROMIC_GROUP_TITLES}
    for symptom in Symptom.objects.all().order_by('name'):
        grouped.setdefault(symptom.syndromic_group, []).append({
            'key': symptom.code,
            'label': symptom.name,
            'description': symptom.description or '',
        })

    return [
        {
            'id': letter,
            'title': title,
            'items': grouped.get(letter, []),
        }
        for letter, title in SYNDROMIC_GROUP_TITLES.items()
        if grouped.get(letter)
    ]


def symptom_label_map():
    """Return ``{code: name}`` for all active symptoms."""
    from myapp.models import Symptom

    return dict(Symptom.objects.values_list('code', 'name'))
