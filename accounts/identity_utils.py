"""Shared email and contact uniqueness helpers across PULSE account tables."""

from __future__ import annotations

import re

from myapp.models import Admin, SuperAdmin, User

_ACCOUNT_MODELS = (
    ('super_admin', SuperAdmin),
    ('admin', Admin),
    ('user', User),
)


def normalize_email(email: str) -> str:
    return (email or '').strip().lower()


def normalize_contact_number(contact: str) -> str:
    digits = re.sub(r'\D', '', contact or '')
    if digits.startswith('63') and len(digits) >= 12:
        digits = '0' + digits[2:]
    return digits


def email_in_use(email: str, *, exclude_user_type: str | None = None, exclude_id: int | None = None) -> bool:
    normalized = normalize_email(email)
    if not normalized:
        return False
    for user_type, model in _ACCOUNT_MODELS:
        qs = model.objects.filter(email__iexact=normalized)
        if exclude_user_type == user_type and exclude_id:
            qs = qs.exclude(id=exclude_id)
        if qs.exists():
            return True
    return False


def contact_in_use(contact: str, *, exclude_user_type: str | None = None, exclude_id: int | None = None) -> bool:
    normalized = normalize_contact_number(contact)
    if not normalized:
        return False
    for user_type, model in _ACCOUNT_MODELS:
        rows = model.objects.exclude(contact_number__isnull=True).exclude(contact_number='')
        if exclude_user_type == user_type and exclude_id:
            rows = rows.exclude(id=exclude_id)
        for row in rows:
            if normalize_contact_number(row.contact_number) == normalized:
                return True
    return False


def is_valid_contact_number(contact: str) -> bool:
    normalized = normalize_contact_number(contact)
    return len(normalized) >= 10
