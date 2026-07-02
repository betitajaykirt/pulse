"""Query helpers for disease mitigation protocols (map popups, sidebars, alerts)."""

from typing import Any, Dict, List, Optional

from myapp.models import MitigationProtocol

# Canonical label aliases from ML / legacy syndrome strings
DISEASE_LABEL_ALIASES = {
    'Hand, Foot and Mouth Disease (HFMD)': 'Hand, Foot, and Mouth Disease',
    'Hand, Foot and Mouth Disease': 'Hand, Foot, and Mouth Disease',
    'HFMD': 'Hand, Foot, and Mouth Disease',
    'Acute Gastroenteritis (AGE)': 'Acute Gastroenteritis',
}

# Tier groups requested for dual-layer decision support
PROBABLE_ALERT_LEVELS = ('probable', 'warning')
CONFIRMED_ALERT_LEVELS = ('confirmed', 'outbreak')

# Priority → response tier (maps existing seed rows without schema migration)
PRIORITY_TIER_MAP = {
    'high': 'outbreak',
    'medium': 'warning',
    'low': 'warning',
}


def normalize_disease_label(disease_label: str) -> str:
    if not disease_label:
        return ''
    label = disease_label.strip()
    return DISEASE_LABEL_ALIASES.get(label, label)


def protocols_for_disease(disease_label: str):
    """Return active mitigation rows for a given ML / surveillance disease label."""
    label = normalize_disease_label(disease_label)
    qs = MitigationProtocol.objects.filter(disease_label=label, is_active=True)
    if not qs.exists() and label:
        qs = MitigationProtocol.objects.filter(
            disease_label__icontains=label.split(',')[0].strip(),
            is_active=True,
        )
    return qs.order_by('-priority', 'sort_order')


def _serialize_protocol(row) -> dict:
    tier = PRIORITY_TIER_MAP.get(row.priority, 'warning')
    return {
        'disease_label': row.disease_label,
        'action_text': row.action_text,
        'priority': row.priority,
        'action_category': row.action_category,
        'sort_order': row.sort_order,
        'alert_level': tier,
    }


def protocols_for_alert_tier(disease_label: str, alert_levels: tuple) -> List[dict]:
    """
    Filter protocols by conceptual alert tier.

    ``warning`` / ``probable`` → medium & low priority early containment steps.
    ``confirmed`` / ``outbreak`` → high priority suppression actions.
    """
    rows = list(protocols_for_disease(disease_label))
    if not rows:
        return []

    want_warning = any(level in ('warning', 'probable') for level in alert_levels)
    want_outbreak = any(level in ('confirmed', 'outbreak') for level in alert_levels)

    selected = []
    for row in rows:
        tier = PRIORITY_TIER_MAP.get(row.priority, 'warning')
        if want_warning and tier == 'warning':
            selected.append(row)
        elif want_outbreak and tier == 'outbreak':
            selected.append(row)

    if not selected:
        if want_outbreak:
            selected = [r for r in rows if r.priority == 'high'] or rows[:3]
        else:
            selected = [r for r in rows if r.priority in ('medium', 'low')] or rows[:3]

    return [_serialize_protocol(r) for r in selected]


def protocols_as_dicts(disease_label: str):
    """Serialize all active protocols for a disease label."""
    return [_serialize_protocol(r) for r in protocols_for_disease(disease_label)]


def mitigation_suggestions_for_report(report) -> Optional[Dict[str, Any]]:
    """
    Build map-popup mitigation payload for PROBABLE (ML) or CONFIRMED (admin) cases.
    """
    status = (report.status or '').strip()
    classification = (report.case_classification or '').strip().lower()
    threshold_status = (getattr(report, 'epidemic_threshold_status', '') or '').strip()

    if status == 'Confirmed' or classification == 'confirmed':
        disease_label = (report.syndrome_type or report.suspected_disease or '').strip()
        if not disease_label:
            return None
        alert_levels = list(CONFIRMED_ALERT_LEVELS)
        banner_type = 'outbreak_critical'
        tier = 'confirmed'
        if threshold_status in ('OUTBREAK_CONFIRMED', 'PROBABLE_OUTBREAK'):
            tier = 'outbreak'
        steps = protocols_for_alert_tier(disease_label, tuple(alert_levels))
        return {
            'tier': tier,
            'banner_type': banner_type,
            'alert_levels': alert_levels,
            'disease_label': normalize_disease_label(disease_label),
            'threshold_status': threshold_status,
            'steps': steps,
        }

    if status == 'Probable' or classification == 'probable':
        disease_label = (report.syndrome_type or report.suspected_disease or '').strip()
        if not disease_label:
            return None
        steps = protocols_for_alert_tier(disease_label, PROBABLE_ALERT_LEVELS)
        return {
            'tier': 'probable',
            'banner_type': 'early_warning',
            'alert_levels': list(PROBABLE_ALERT_LEVELS),
            'disease_label': normalize_disease_label(disease_label),
            'steps': steps,
        }

    return None
