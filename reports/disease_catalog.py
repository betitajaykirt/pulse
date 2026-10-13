"""Office-added diseases that staff can record before the next model training."""
from __future__ import annotations

import re

from reports.pidsr_schema import (
    DISEASE_LABELS,
    INCONCLUSIVE_SYNDROMIC_LABEL,
    PIDSR_SYMPTOM_CODES,
    PIDSR_SYMPTOM_LABELS,
    SYMPTOM_CODE_TO_GROUP,
    SYNDROMIC_GROUP_TITLES,
)

OTHER_DISEASE_LABEL = 'Other / Non-specific'
RESERVED_DISEASE_NAMES = frozenset(
    {label.casefold() for label in DISEASE_LABELS}
    | {
        INCONCLUSIVE_SYNDROMIC_LABEL.casefold(),
        OTHER_DISEASE_LABEL.casefold(),
        'unknown',
        'insufficient data for prediction',
    }
)
_GROUP_ORDER = ('A', 'B', 'C', 'D', 'R', 'N', 'E')
_NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 ,./&()\-]{1,149}$')


def active_added_disease_labels() -> tuple[str, ...]:
    return tuple(_active_added_names())


def selectable_disease_labels() -> tuple[str, ...]:
    """Built-in diseases, then active diseases the office added."""
    labels = list(DISEASE_LABELS)
    seen = {label.casefold() for label in labels}
    for name in _active_added_names():
        key = name.casefold()
        if key in seen:
            continue
        labels.append(name)
        seen.add(key)
    return tuple(labels)


def is_confirmable_disease(label: str) -> bool:
    text = (label or '').strip()
    if not text:
        return False
    if text == OTHER_DISEASE_LABEL or text in DISEASE_LABELS:
        return True
    return _added_name_is_active(text)


def catalog_category_level(label: str) -> str:
    """Return Category 1 or Category 2 for an added disease, including inactive rows."""
    text = (label or '').strip()
    if not text:
        return ''
    try:
        from myapp.models import AddedDisease

        row = (
            AddedDisease.objects.filter(name__iexact=text)
            .only('category')
            .first()
        )
    except Exception:
        return ''
    if row and row.category in ('Category 1', 'Category 2'):
        return row.category
    return ''


def clean_new_symptoms(names, groups, *, existing_names=()) -> list[tuple[str, str]]:
    """Return new symptom names and groups. Blank rows are ignored."""
    existing = {str(item).casefold() for item in existing_names}
    cleaned = []
    seen = set()
    name_list = list(names or [])
    group_list = list(groups or [])
    for index, raw_name in enumerate(name_list):
        symptom_name = ' '.join(str(raw_name or '').split())
        if not symptom_name:
            continue
        if not _NAME_RE.match(symptom_name):
            raise ValueError('Enter each new symptom with letters, numbers, and simple punctuation.')
        group = group_list[index].strip() if index < len(group_list) else ''
        if group not in _GROUP_ORDER:
            raise ValueError(f'Choose a symptom group for {symptom_name}.')
        key = symptom_name.casefold()
        if key in existing or key in seen:
            raise ValueError(f'{symptom_name} is already on the symptom checklist. Tick it instead of adding it again.')
        seen.add(key)
        cleaned.append((symptom_name, group))
    return cleaned


def code_for_new_symptom(name: str, taken_codes=()) -> str:
    """Stable code for an office-added symptom. The added_ prefix keeps it off the trained feature list."""
    slug = re.sub(r'[^a-z0-9]+', '_', name.casefold()).strip('_') or 'symptom'
    base = f'added_{slug}'[:64].strip('_')
    taken = {str(code) for code in taken_codes}
    code = base
    suffix = 2
    while code in taken or code in PIDSR_SYMPTOM_CODES:
        tail = f'_{suffix}'
        code = f'{base[:64 - len(tail)]}{tail}'
        suffix += 1
    return code


def validate_added_disease(
    name: str,
    category: str,
    symptom_codes,
    *,
    taken_names=(),
    extra_allowed_codes=(),
) -> tuple[str, str, list[str]]:
    """Return a cleaned name, category, and symptom codes, or raise ValueError."""
    cleaned = ' '.join((name or '').split())
    if not cleaned or not _NAME_RE.match(cleaned):
        raise ValueError('Enter a disease name using letters, numbers, and simple punctuation.')
    if cleaned.casefold() in RESERVED_DISEASE_NAMES:
        raise ValueError(f'{cleaned} is already one of the trained diseases.')
    taken = {str(item).casefold() for item in taken_names}
    if cleaned.casefold() in taken:
        raise ValueError(f'{cleaned} is already in the added-disease list.')
    if category not in ('Category 1', 'Category 2'):
        raise ValueError('Choose Category I or Category II.')
    codes = []
    seen = set()
    allowed_extra = set(extra_allowed_codes or ())
    for raw in symptom_codes or []:
        code = str(raw).strip()
        if not code or code in seen:
            continue
        if code not in PIDSR_SYMPTOM_CODES and code not in allowed_extra:
            raise ValueError('Choose a checklist symptom or add a new symptom name.')
        seen.add(code)
        codes.append(code)
    if not codes:
        raise ValueError('Select at least one symptom that goes with this disease.')
    return cleaned, category, codes


def symptom_groups(selected_codes=()):
    """Symptom checklist grouped for the add-disease form."""
    selected = set(selected_codes or [])
    grouped = {key: [] for key in _GROUP_ORDER}
    for code, name, group in _symptom_rows():
        bucket = grouped.setdefault(group, [])
        bucket.append({
            'code': code,
            'name': name,
            'checked': code in selected,
        })
    result = []
    for key in _GROUP_ORDER:
        items = grouped.get(key) or []
        if not items:
            continue
        result.append({
            'title': SYNDROMIC_GROUP_TITLES.get(key, key),
            'items': items,
        })
    return result


def _symptom_rows():
    try:
        from myapp.models import Symptom

        rows = list(Symptom.objects.order_by('syndromic_group', 'name').values_list(
            'code', 'name', 'syndromic_group',
        ))
    except Exception:
        rows = []
    if rows:
        return [
            (code, name, group)
            for code, name, group in rows
            if code in PIDSR_SYMPTOM_CODES
        ]
    return [
        (code, PIDSR_SYMPTOM_LABELS.get(code, code), SYMPTOM_CODE_TO_GROUP.get(code, 'A'))
        for code in PIDSR_SYMPTOM_CODES
    ]


def _active_added_names():
    try:
        from myapp.models import AddedDisease

        return list(
            AddedDisease.objects.filter(is_active=True)
            .order_by('name')
            .values_list('name', flat=True)
        )
    except Exception:
        return []


def _added_name_is_active(name: str) -> bool:
    try:
        from myapp.models import AddedDisease

        return AddedDisease.objects.filter(name__iexact=name, is_active=True).exists()
    except Exception:
        return False
