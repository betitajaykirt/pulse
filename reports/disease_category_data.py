"""
DOH disease transmission categories for case and map filtering.
"""
from __future__ import annotations

from django.db.models import Q

from reports.pidsr_schema import LEGACY_DISEASE_LABEL_MAP, DISEASE_LABELS, normalize_disease_label

DISEASE_CATEGORY_CHOICES = [
    ('', 'All Disease Categories'),
    ('vector_borne', 'Vector-Borne Diseases'),
    ('airborne', 'Airborne / Respiratory Diseases'),
    ('waterborne_foodborne', 'Waterborne & Foodborne Diseases'),
    ('zoonotic_vpd', 'Zoonotic & Vaccine-Preventable'),
]

VALID_DISEASE_CATEGORIES = frozenset(
    value for value, _ in DISEASE_CATEGORY_CHOICES if value
)

MONITORED_DISEASE_CHOICES = [('', 'All Diseases')] + [
    (label, label) for label in DISEASE_LABELS
]

VALID_MONITORED_DISEASES = frozenset(DISEASE_LABELS)

# Monitored + legacy labels grouped by transmission route
CATEGORY_DISEASE_LABELS: dict[str, tuple[str, ...]] = {
    'vector_borne': (
        'Dengue Fever',
        'Dengue',
        'Malaria',
        'Acute Hemorrhagic Fever Syndrome',
    ),
    'airborne': (
        'COVID-19',
        'Human Avian Influenza',
        'Measles',
        'Meningococcal Disease',
        'Middle East Respiratory Syndrome',
        'Severe Acute Respiratory Syndrome',
        'Bacterial Meningitis',
        'Diphtheria',
        'Influenza-Like Illness',
        'Influenza-like Illness (ILI)',
        'Pertussis',
        'Respiratory Illness',
        'Acute Encephalitis Syndrome',
    ),
    'waterborne_foodborne': (
        'Leptospirosis',
        'Typhoid and Paratyphoid Fever',
        'Typhoid Fever',
        'Acute Bloody Diarrhea',
        'Diarrheal Disease',
        'Acute Gastroenteritis',
        'Cholera',
        'Acute Viral Hepatitis',
        'Paralytic Shellfish Poisoning',
        'Hand, Foot, and Mouth Disease',
        'Hand, Foot and Mouth Disease (HFMD)',
    ),
    'zoonotic_vpd': (
        'Anthrax',
        'Rabies',
        'Adverse Event Following Immunization',
        'Acute Flaccid Paralysis',
        'Neonatal Tetanus',
        'Non-Neonatal Tetanus',
    ),
}

# Flat lookup: canonical disease label → category slug
DISEASE_TRANSMISSION_CATEGORY: dict[str, str] = {}
for category, labels in CATEGORY_DISEASE_LABELS.items():
    for label in labels:
        DISEASE_TRANSMISSION_CATEGORY[label] = category
        DISEASE_TRANSMISSION_CATEGORY[normalize_disease_label(label)] = category


def resolve_disease_category(disease_label: str) -> str:
    """Return transmission category slug for a disease label, or empty string."""
    text = (disease_label or '').strip()
    if not text:
        return ''
    if text in DISEASE_TRANSMISSION_CATEGORY:
        return DISEASE_TRANSMISSION_CATEGORY[text]
    normalized = normalize_disease_label(text)
    if normalized in DISEASE_TRANSMISSION_CATEGORY:
        return DISEASE_TRANSMISSION_CATEGORY[normalized]
    if text in LEGACY_DISEASE_LABEL_MAP:
        return DISEASE_TRANSMISSION_CATEGORY.get(
            LEGACY_DISEASE_LABEL_MAP[text], '',
        )
    lowered = text.lower()
    for label, category in DISEASE_TRANSMISSION_CATEGORY.items():
        if label.lower() in lowered or lowered in label.lower():
            return category
    return ''


def _disease_label_match_q(label: str) -> Q:
    """Match a surveillance report by syndrome, suspected disease, or ML remarks."""
    label = (label or '').strip()
    if not label:
        return Q()

    terms = {label, label.lower(), label.title()}
    primary = label.split()[0]
    if primary:
        terms.add(primary)
        terms.add(primary.lower())

    q = Q()
    for term in terms:
        if len(term) < 3 and term.lower() not in ('age',):
            continue
        q |= Q(syndrome_type__icontains=term)
        q |= Q(suspected_disease__icontains=term)
        q |= Q(remarks__icontains=f'ML Top Prediction: {term}')
        q |= Q(remarks__icontains=f'ML Classification: {term}')
    return q


def disease_category_filter_q(disease_category: str) -> Q:
    """Build a queryset ``Q`` object for the selected transmission category."""
    category = (disease_category or '').strip()
    if not category or category not in VALID_DISEASE_CATEGORIES:
        return Q()

    labels = CATEGORY_DISEASE_LABELS.get(category, ())
    if not labels:
        return Q(pk__in=[])

    combined = Q()
    for label in labels:
        combined |= _disease_label_match_q(label)
    return combined


def filter_surveillance_reports_by_disease_category(qs, disease_category: str):
    """Filter a ``SurveillanceReport`` queryset by transmission category."""
    clause = disease_category_filter_q(disease_category)
    if not clause:
        return qs
    return qs.filter(clause).distinct()


def _legacy_aliases_for_disease(canonical_label: str) -> tuple[str, ...]:
    """Return legacy syndrome labels that map to the canonical PIDSR disease."""
    aliases: set[str] = set()
    canonical = normalize_disease_label(canonical_label)
    for legacy, mapped in LEGACY_DISEASE_LABEL_MAP.items():
        if mapped == canonical:
            aliases.add(legacy)
    return tuple(aliases)


def disease_label_filter_q(disease_label: str) -> Q:
    """Build a queryset ``Q`` object for a single monitored disease."""
    label = (disease_label or '').strip()
    canonical = normalize_disease_label(label)
    if canonical not in VALID_MONITORED_DISEASES and label not in VALID_MONITORED_DISEASES:
        return Q()

    match_root = canonical if canonical in VALID_MONITORED_DISEASES else label
    combined = Q()
    for match_label in (match_root, *_legacy_aliases_for_disease(match_root)):
        combined |= _disease_label_match_q(match_label)
    return combined


def filter_surveillance_reports_by_disease_label(qs, disease_label: str):
    """Filter a ``SurveillanceReport`` queryset by monitored disease label."""
    clause = disease_label_filter_q(disease_label)
    if not clause:
        return qs
    return qs.filter(clause).distinct()
