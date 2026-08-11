"""
Shared US-style date parsing and display helpers (mm/dd/yyyy).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Union

DateLike = Union[date, datetime, str, None]

DISPLAY_DATE_FORMAT = '%m/%d/%Y'
DISPLAY_DATETIME_FORMAT = '%m/%d/%Y %I:%M %p'
INPUT_DATE_FORMATS = (
    '%m/%d/%Y',
    '%m/%d/%y',
    '%m-%d-%Y',
    '%Y-%m-%d',
)


def parse_user_date(value: DateLike) -> Optional[date]:
    """Parse a user-entered date string into a ``date`` object."""
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None

    for fmt in INPUT_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def format_display_date(value: DateLike, empty: str = '—') -> str:
    """Format a date for UI display as mm/dd/yyyy."""
    if value is None or value == '':
        return empty
    if isinstance(value, datetime):
        return value.strftime(DISPLAY_DATE_FORMAT)
    if isinstance(value, date):
        return value.strftime(DISPLAY_DATE_FORMAT)

    parsed = parse_user_date(value)
    if parsed:
        return parsed.strftime(DISPLAY_DATE_FORMAT)
    return str(value)


def format_display_datetime(value: DateLike, empty: str = '—') -> str:
    """Format a datetime for UI display as mm/dd/yyyy hh:mm AM/PM."""
    if value is None or value == '':
        return empty
    if isinstance(value, datetime):
        return value.strftime(DISPLAY_DATETIME_FORMAT)
    if isinstance(value, date):
        return value.strftime(DISPLAY_DATE_FORMAT)

    parsed = parse_user_date(value)
    if parsed:
        return parsed.strftime(DISPLAY_DATE_FORMAT)
    return str(value)
