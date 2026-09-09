"""Shared case window for the map, analytics, and barangay shading."""
from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone

INACTIVE_CASE_STATUSES = ('Closed', 'Discarded')

NAMED_TIME_RANGES = (
    'all_active',
    'current_month',
    'last_30_days',
    'last_3_months',
    'last_6_months',
    'current_year',
)


def local_today(today=None) -> date:
    if today is not None:
        return today
    return timezone.localdate()


def named_time_window(time_range: str, today=None) -> tuple[date | None, date]:
    """Return (start, end) dates. start is None for all open cases."""
    today = local_today(today)
    key = (time_range or 'all_active').strip()
    if key == 'all_active':
        return None, today
    if key == 'current_month':
        return today.replace(day=1), today
    if key == 'last_30_days':
        return today - timedelta(days=30), today
    if key == 'last_3_months':
        return today - timedelta(days=90), today
    if key == 'last_6_months':
        return today - timedelta(days=183), today
    if key == 'current_year':
        return today.replace(month=1, day=1), today
    return None, today


def rolling_days_window(days: int, today=None) -> tuple[date, date]:
    today = local_today(today)
    return today - timedelta(days=int(days)), today


def parse_scope_time_range(value, *, default_days=30, today=None) -> tuple[date | None, date | None]:
    """
    Parse map ``time_range`` (``7`` / ``30`` / ``90`` / ``all_active``)
    or analytics named windows into an inclusive onset window.
    """
    raw = str(value or '').strip()
    folded = raw.casefold()
    if folded in {'all', 'all_active'}:
        return None, None
    if folded in NAMED_TIME_RANGES:
        start, end = named_time_window(folded, today=today)
        return start, end
    try:
        days = int(raw)
    except (TypeError, ValueError):
        days = default_days
    if days <= 0:
        return None, None
    start, end = rolling_days_window(days, today=today)
    return start, end


def _prefixed(name: str, prefix: str = '') -> str:
    if prefix and not prefix.endswith('__'):
        prefix = f'{prefix}__'
    return f'{prefix}{name}' if prefix else name


def event_date_window_q(start, end=None, prefix: str = '') -> Q:
    """
    Count a case in the window by date of onset.

    If onset is missing, fall back to the calendar date of report_date.
    """
    if start is None:
        return Q()
    if end is None:
        end = local_today()
    onset = _prefixed('date_of_onset', prefix)
    report = _prefixed('report_date', prefix)
    return (
        Q(**{f'{onset}__gte': start, f'{onset}__lte': end})
        | Q(**{
            f'{onset}__isnull': True,
            f'{report}__date__gte': start,
            f'{report}__date__lte': end,
        })
    )


def inactive_status_q(prefix: str = '') -> Q:
    status = _prefixed('status', prefix)
    return Q(**{f'{status}__in': INACTIVE_CASE_STATUSES})


def apply_open_case_scope(qs, *, start=None, end=None):
    """Open cases only (not Closed/Discarded), optionally limited by event date."""
    qs = qs.exclude(status__in=INACTIVE_CASE_STATUSES)
    window = event_date_window_q(start, end)
    if window:
        qs = qs.filter(window)
    return qs
