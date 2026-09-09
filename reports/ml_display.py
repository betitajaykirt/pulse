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
_ML_CLASS_RE = re.compile(r'ML Classification:\s*([^|]+)', re.IGNORECASE)
_ML_CONF_RE = re.compile(r'ML Confidence:\s*([\d.]+)\s*%?', re.IGNORECASE)
_ML_SEC_TOP_RE = re.compile(r'ML Secondary Prediction:\s*([^|]+)', re.IGNORECASE)
_ML_SEC_CONF_RE = re.compile(r'ML Secondary Confidence:\s*([\d.]+)\s*%?', re.IGNORECASE)


def is_inconclusive_disease_label(label: str) -> bool:
    return (label or '').strip().lower() in _INCONCLUSIVE_DISEASE_LABELS


def is_alertable_disease_label(label: str) -> bool:
    """Alerts require a specific disease, not an inconclusive ML placeholder."""
    return not is_inconclusive_disease_label(label)


def stored_disease_identity_from_ml(ml: dict | None) -> str:
    """Disease written to syndrome_type / suspected_disease on submit."""
    ml = ml or {}
    top = (ml.get('top_predicted_disease') or '').strip()
    gated = (ml.get('disease_label') or '').strip()
    if top and not is_inconclusive_disease_label(top):
        return top
    return gated or 'Inconclusive Syndromic Pattern'


def official_disease_label(report) -> str:
    """
    Single disease identity for storage, APTAS, map, analytics, and confirmation.

    Lab-confirmed cases use the stored confirmed disease. Open cases use the ML
    top prediction when it is a specific disease, including legacy rows that
    stored Inconclusive Syndromic Pattern on syndrome_type.
    """
    status = (getattr(report, 'status', None) or '').strip()
    stored = (getattr(report, 'syndrome_type', None) or '').strip()
    suspected = (getattr(report, 'suspected_disease', None) or '').strip()

    if status == 'Confirmed':
        for candidate in (stored, suspected, ml_top_prediction_for_report(report)):
            if candidate and not is_inconclusive_disease_label(candidate):
                return candidate
        return stored or suspected or '—'

    top = ml_top_prediction_for_report(report)
    if top:
        return top
    for candidate in (suspected, stored):
        if candidate and not is_inconclusive_disease_label(candidate):
            return candidate
    return stored or 'Inconclusive Syndromic Pattern'


def report_ml_classification_inconclusive(report) -> bool:
    """True when RF gated the case as inconclusive (alerts must stay off)."""
    if (getattr(report, 'status', None) or '').strip() == 'Confirmed':
        return False
    remarks_class = parse_ml_classification(getattr(report, 'remarks', None) or '')
    if remarks_class:
        return is_inconclusive_disease_label(remarks_class)
    return is_inconclusive_disease_label(getattr(report, 'syndrome_type', None) or '')


def report_has_alertable_disease(report) -> bool:
    if report_ml_classification_inconclusive(report):
        return False
    return is_alertable_disease_label(official_disease_label(report))


def parse_ml_top_prediction(remarks: str) -> str:
    if not remarks:
        return ''
    match = _ML_TOP_RE.search(remarks)
    return match.group(1).strip() if match else ''


def parse_ml_classification(remarks: str) -> str:
    if not remarks:
        return ''
    match = _ML_CLASS_RE.search(remarks)
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


def parse_ml_secondary_prediction(remarks: str) -> str:
    if not remarks:
        return ''
    match = _ML_SEC_TOP_RE.search(remarks)
    return match.group(1).strip() if match else ''


def parse_ml_secondary_confidence(remarks: str):
    if not remarks:
        return None
    match = _ML_SEC_CONF_RE.search(remarks)
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
      secondary: secondary label text or ''
      secondary_confidence_pct: float or None
      is_lab_confirmed: bool
    """
    status = (getattr(report, 'status', None) or '').strip()
    remarks = getattr(report, 'remarks', None) or ''
    conf = parse_ml_confidence(remarks)
    confidence_pct = round(conf * 100, 1) if conf is not None else None
    
    sec_pred = parse_ml_secondary_prediction(remarks)
    sec_conf = parse_ml_secondary_confidence(remarks)
    sec_confidence_pct = round(sec_conf * 100, 1) if sec_conf is not None else None
    
    if is_inconclusive_disease_label(sec_pred):
        sec_pred = ''
        sec_confidence_pct = None

    base_response = {
        'secondary': sec_pred,
        'secondary_confidence_pct': sec_confidence_pct,
        'is_lab_confirmed': False,
    }

    if status == 'Confirmed':
        name = official_disease_label(report)
        base_response.update({
            'primary': name,
            'confidence_pct': None,
            'is_lab_confirmed': True,
        })
        return base_response

    name = official_disease_label(report)
    base_response.update({
        'primary': name or 'Inconclusive Syndromic Pattern',
        'confidence_pct': confidence_pct,
    })
    return base_response
