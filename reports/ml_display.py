"""Format Random Forest predictions for surveillance UI."""

from __future__ import annotations

import re

_INCONCLUSIVE_DISEASE_LABELS = frozenset({
    'inconclusive syndromic pattern',
    'insufficient data for prediction',
    'undetermined',
    '',
})

_ML_TOP_RE = re.compile(r'ML Top Prediction:\s*([^|]+)', re.IGNORECASE)
_ML_CONF_RE = re.compile(r'ML Confidence:\s*([\d.]+)\s*%?', re.IGNORECASE)


def is_inconclusive_disease_label(label: str) -> bool:
    return (label or '').strip().lower() in _INCONCLUSIVE_DISEASE_LABELS


def parse_ml_top_prediction(remarks: str) -> str:
    if not remarks:
        return ''
    match = _ML_TOP_RE.search(remarks)
    return match.group(1).strip() if match else ''


def parse_ml_confidence(remarks: str):
    if not remarks:
        return None
    match = _ML_CONF_RE.search(remarks)
    if not match:
        return None
    value = float(match.group(1))
    if value > 1.0:
        return value / 100.0
    return value


def ml_top_prediction_for_report(report) -> str:
    top = parse_ml_top_prediction(getattr(report, 'remarks', None) or '')
    if top and not is_inconclusive_disease_label(top):
        return top
    for candidate in (
        getattr(report, 'suspected_disease', None),
        getattr(report, 'syndrome_type', None),
    ):
        if candidate and not is_inconclusive_disease_label(candidate):
            return candidate.strip()
    return ''


def predicted_disease_display(report):
    """
    Return dict for templates/API:
      primary: main label text
      confidence_pct: float or None
      is_lab_confirmed: bool
    """
    status = (getattr(report, 'status', None) or '').strip()
    conf = parse_ml_confidence(getattr(report, 'remarks', None) or '')
    confidence_pct = round(conf * 100, 1) if conf is not None else None

    if status == 'Confirmed':
        name = (
            (getattr(report, 'syndrome_type', None) or '')
            or (getattr(report, 'suspected_disease', None) or '')
        ).strip() or '—'
        return {
            'primary': name,
            'confidence_pct': None,
            'is_lab_confirmed': True,
        }

    top = ml_top_prediction_for_report(report)
    stored = (
        (getattr(report, 'suspected_disease', None) or '')
        or (getattr(report, 'syndrome_type', None) or '')
    ).strip()

    if top and not is_inconclusive_disease_label(top):
        return {
            'primary': top,
            'confidence_pct': confidence_pct,
            'is_lab_confirmed': False,
        }

    if stored and not is_inconclusive_disease_label(stored):
        return {
            'primary': stored,
            'confidence_pct': confidence_pct,
            'is_lab_confirmed': False,
        }

    return {
        'primary': 'Inconclusive Syndromic Pattern',
        'confidence_pct': confidence_pct,
        'is_lab_confirmed': False,
    }
