"""Bilingual PIDSR recommendation lookup and cluster resolution.

The JSON matrix is the single source of clinical response copy.  This module
keeps disease normalization, status escalation, ordering, and action
de-duplication out of views and templates.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from reports.pidsr_schema import (
    DISEASE_LABELS,
    INCONCLUSIVE_SYNDROMIC_LABEL,
    PIDSR_CATEGORY_I,
    normalize_disease_label,
)

MATRIX_PATH = Path(__file__).resolve().parent / 'data' / 'recommendations_matrix.json'
RECOMMENDATION_STATES = ('suspected', 'probable', 'confirmed', 'cluster')
STATUS_RANK = {'suspected': 1, 'probable': 2, 'confirmed': 3}
CATEGORY_RANK = {'Category I': 0, 'Category II': 1}
CLUSTER_RADIUS_METERS = 300
CLUSTER_WINDOW_DAYS = 7


def _value(item: Any, *names: str, default=None):
    for name in names:
        if isinstance(item, dict) and item.get(name) not in (None, ''):
            return item[name]
        value = getattr(item, name, None)
        if value not in (None, ''):
            return value
    return default


def canonical_disease_name(value: str | None) -> str:
    """Return a canonical monitored label, or an empty string if unsupported."""
    label = normalize_disease_label((value or '').strip())
    if label == INCONCLUSIVE_SYNDROMIC_LABEL or label not in DISEASE_LABELS:
        return ''
    return label


def normalize_case_status(value: str | None) -> str:
    text = (value or '').strip().casefold()
    if text == 'confirmed':
        return 'confirmed'
    if text == 'probable':
        return 'probable'
    return 'suspected'


def disease_for_case(case: Any) -> str:
    """Resolve official disease identity from a model or map API dictionary."""
    status = status_for_case(case)
    candidates = []
    if status == 'confirmed':
        candidates.append(_value(case, 'confirmed_disease'))
    candidates.extend([
        _value(case, 'disease_name'),
        _value(case, 'disease_label'),
        _value(case, 'ml_top_predicted_disease'),
        _value(case, 'ml_predicted_disease'),
        _value(case, 'syndrome_type'),
        _value(case, 'suspected_disease'),
    ])
    for candidate in candidates:
        label = canonical_disease_name(candidate)
        if label:
            return label
    return ''


def status_for_case(case: Any) -> str:
    status = _value(case, 'status', default='')
    if normalize_case_status(status) != 'suspected' or str(status).casefold() == 'suspected':
        return normalize_case_status(status)
    return normalize_case_status(_value(case, 'case_classification', default='suspected'))


def _validate_action(action: dict, disease: str, state: str) -> None:
    required = ('code', 'en', 'local', 'targets')
    missing = [key for key in required if not action.get(key)]
    if missing:
        raise ValueError(
            f'{disease}/{state} action is missing: {", ".join(missing)}'
        )
    if not isinstance(action['targets'], list) or not all(action['targets']):
        raise ValueError(f'{disease}/{state} targets must be a non-empty list.')


def validate_recommendation_matrix(payload: dict) -> None:
    """Fail fast when catalog labels or action contracts drift."""
    diseases = payload.get('diseases')
    if not isinstance(diseases, list):
        raise ValueError('Recommendation matrix must contain a diseases list.')
    labels = [row.get('label') for row in diseases]
    if len(labels) != len(set(labels)):
        raise ValueError('Recommendation matrix contains duplicate disease labels.')
    if set(labels) != set(DISEASE_LABELS):
        missing = sorted(set(DISEASE_LABELS) - set(labels))
        extra = sorted(set(labels) - set(DISEASE_LABELS))
        raise ValueError(f'Recommendation catalog mismatch; missing={missing}, extra={extra}')

    expected_states = set(RECOMMENDATION_STATES)
    for row in diseases:
        label = row['label']
        expected_category = 'Category I' if label in PIDSR_CATEGORY_I else 'Category II'
        if row.get('category') != expected_category:
            raise ValueError(f'{label} must be {expected_category}.')
        actions = row.get('actions') or {}
        if set(actions) != expected_states:
            raise ValueError(f'{label} must define all four recommendation states.')
        for state, state_actions in actions.items():
            if not isinstance(state_actions, list) or not state_actions:
                raise ValueError(f'{label}/{state} must contain at least one action.')
            for action in state_actions:
                _validate_action(action, label, state)


@lru_cache(maxsize=1)
def recommendation_matrix() -> dict[str, dict]:
    payload = json.loads(MATRIX_PATH.read_text(encoding='utf-8'))
    validate_recommendation_matrix(payload)
    return {row['label']: row for row in payload['diseases']}


def _serialize_actions(actions: Iterable[dict]) -> list[dict]:
    return [
        {
            'code': action['code'],
            'text_en': action['en'],
            'text_local': action['local'],
            'target_units': list(action['targets']),
        }
        for action in actions
    ]


def resolve_case_recommendation(
    disease_name: str,
    status: str,
    *,
    include_cluster_actions: bool = True,
) -> dict | None:
    disease = canonical_disease_name(disease_name)
    row = recommendation_matrix().get(disease)
    if not row:
        return None
    state = normalize_case_status(status)
    result = {
        'disease': disease,
        'disease_code': row['code'],
        'category': row['category'],
        'highest_status': state.title(),
        'case_count': 1,
        'is_cluster': False,
        'actions': _serialize_actions(row['actions'][state]),
        'target_units': sorted({
            target
            for action in row['actions'][state]
            for target in action['targets']
        }),
    }
    if include_cluster_actions:
        result['cluster_actions'] = _serialize_actions(row['actions']['cluster'])
    return result


def _dedupe_actions(actions: Iterable[dict]) -> list[dict]:
    combined: dict[str, dict] = {}
    for action in actions:
        code = action['code']
        if code not in combined:
            combined[code] = {
                **action,
                'target_units': list(action.get('target_units') or []),
            }
            continue
        existing = combined[code]['target_units']
        for target in action.get('target_units') or []:
            if target not in existing:
                existing.append(target)
    return list(combined.values())


def resolve_cluster_recommendations(cases_array: Iterable[Any]) -> dict:
    """Resolve sorted pathogen cards and one deduplicated BHW field summary."""
    grouped: dict[str, list[Any]] = defaultdict(list)
    for case in cases_array or []:
        disease = disease_for_case(case)
        if disease:
            grouped[disease].append(case)

    cards = []
    for disease, cases in grouped.items():
        statuses = [status_for_case(case) for case in cases]
        highest = max(statuses, key=lambda item: STATUS_RANK[item])
        card = resolve_case_recommendation(disease, highest)
        if not card:
            continue
        card['case_count'] = sum(
            max(1, int(_value(case, 'case_count', default=1) or 1))
            for case in cases
        )
        card['is_cluster'] = True
        card['actions'] = _dedupe_actions(
            list(card['actions']) + list(card.pop('cluster_actions', []))
        )
        card['target_units'] = sorted({
            target
            for action in card['actions']
            for target in action.get('target_units') or []
        })
        cards.append(card)

    cards.sort(key=lambda card: (
        CATEGORY_RANK.get(card['category'], 9),
        -STATUS_RANK[card['highest_status'].casefold()],
        -card['case_count'],
        card['disease'],
    ))
    summary = _dedupe_actions(
        action
        for card in cards
        for action in card['actions']
    )
    return {
        'has_category_i': any(card['category'] == 'Category I' for card in cards),
        'is_cluster': len(cases_array or []) > 1 if hasattr(cases_array, '__len__') else bool(cards),
        'disease_cards': cards,
        'field_action_summary': summary,
    }


def _as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or '').strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def haversine_meters(lat1, lon1, lat2, lon2) -> float:
    """Distance helper shared by tests and any future server-side clustering."""
    radius = 6_371_000.0
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    d_phi = math.radians(float(lat2) - float(lat1))
    d_lambda = math.radians(float(lon2) - float(lon1))
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def cases_share_cluster(
    left: Any,
    right: Any,
    *,
    radius_meters: int = CLUSTER_RADIUS_METERS,
    window_days: int = CLUSTER_WINDOW_DAYS,
) -> bool:
    """True when cases are within both the spatial and onset-time thresholds."""
    coordinates = [
        _value(left, 'latitude'),
        _value(left, 'longitude'),
        _value(right, 'latitude'),
        _value(right, 'longitude'),
    ]
    if any(value in (None, '') for value in coordinates):
        return False
    left_date = _as_date(_value(left, 'date_of_onset', 'reported_at', 'report_date'))
    right_date = _as_date(_value(right, 'date_of_onset', 'reported_at', 'report_date'))
    if not left_date or not right_date:
        return False
    if abs((left_date - right_date).days) > window_days:
        return False
    return haversine_meters(*coordinates) <= radius_meters

