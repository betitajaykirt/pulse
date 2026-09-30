"""Closed historical cases for the 1-year and 3-year presentation filters."""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from mysite.command_safety import assert_safe_for_destructive_commands

from myapp.models import Barangay, SurveillanceReport

HISTORY_MARKER = '[PULSE-HISTORY]'

DISEASE_WEIGHTS = (
    ('Dengue Fever', 10),
    ('Influenza-Like Illness', 6),
    ('Acute Bloody Diarrhea', 4),
    ('COVID-19', 4),
    ('Leptospirosis', 3),
    ('Typhoid and Paratyphoid Fever', 3),
    ('Hand, Foot, and Mouth Disease', 2),
    ('Measles', 2),
    ('Cholera', 1),
    ('Malaria', 1),
)

FIRST_NAMES = (
    'Ana', 'Ben', 'Carlo', 'Diana', 'Elena', 'Felix', 'Gina', 'Hugo',
    'Ivy', 'Jose', 'Kara', 'Leo', 'Mia', 'Nico', 'Olive', 'Paolo',
)
LAST_NAMES = (
    'Santos', 'Reyes', 'Cruz', 'Bautista', 'Garcia', 'Lopez', 'Ramos', 'Flores',
)


def _month_starts(start: date, end: date):
    cursor = start.replace(day=1)
    while cursor <= end:
        nxt = date(cursor.year + 1, 1, 1) if cursor.month == 12 else date(cursor.year, cursor.month + 1, 1)
        yield cursor, min(end, nxt - timedelta(days=1))
        cursor = nxt


def _weighted_disease(rng: random.Random, month: int) -> str:
    pool = []
    for label, weight in DISEASE_WEIGHTS:
        adjusted = weight
        if label == 'Dengue Fever':
            adjusted = 16 if month in (6, 7, 8, 9, 10, 11) else 4
        elif label == 'Leptospirosis':
            adjusted = 8 if month in (7, 8, 9, 10) else 1
        elif label == 'Influenza-Like Illness':
            adjusted = 9 if month in (1, 2, 6, 7, 8) else 4
        pool.extend([label] * adjusted)
    return rng.choice(pool)


def _classification(rng: random.Random) -> str:
    roll = rng.random()
    if roll < 0.62:
        return 'confirmed'
    if roll < 0.87:
        return 'probable'
    return 'suspected'


def seed_presentation_history(*, years: int = 3, today: date | None = None) -> int:
    """Replace prior presentation history and insert closed cases across the window."""
    today = today or timezone.localdate()
    start = today - timedelta(days=365 * years)
    end = today - timedelta(days=31)
    rng = random.Random(20261001)

    SurveillanceReport.objects.filter(remarks__icontains=HISTORY_MARKER).delete()

    barangays = []
    for barangay in Barangay.objects.all():
        if barangay.latitude is None or barangay.longitude is None:
            continue
        barangays.append(barangay)
    if not barangays:
        return 0

    zone = timezone.get_current_timezone()
    reports = []
    for month_start, month_end in _month_starts(start, end):
        window_start = max(start, month_start)
        window_end = min(end, month_end)
        if window_start > window_end:
            continue
        span = (window_end - window_start).days
        target = 28 if month_start.month in (6, 7, 8, 9, 10, 11) else 16
        target += rng.randint(-3, 5)
        for _ in range(max(target, 1)):
            onset = window_start + timedelta(days=rng.randint(0, span))
            barangay = rng.choice(barangays)
            lat = float(barangay.latitude) + rng.uniform(-0.004, 0.004)
            lng = float(barangay.longitude) + rng.uniform(-0.004, 0.004)
            disease = _weighted_disease(rng, onset.month)
            classification = _classification(rng)
            age = rng.randint(1, 72)
            sex = rng.choice(('Male', 'Female'))
            reported = timezone.make_aware(datetime.combine(onset, time(8, 0)), zone)
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            reports.append(SurveillanceReport(
                barangay=barangay,
                source_type='historical',
                syndrome_type=disease,
                suspected_disease=disease,
                case_count=1,
                patient_name=f'{first} {last}',
                date_of_onset=onset,
                report_date=reported,
                case_classification=classification,
                status='Closed',
                latitude=Decimal(f'{lat:.7f}'),
                longitude=Decimal(f'{lng:.7f}'),
                validation_status='validated' if classification == 'confirmed' else 'pending',
                resolution_outcome='recovered',
                closed_at=reported + timedelta(days=7),
                detailed_address=f'Purok {rng.randint(1, 8)}, {barangay.barangay_name}',
                remarks=(
                    f'Age: {age} | Sex: {sex} | {HISTORY_MARKER} '
                    'Closed presentation history for the longer date filters.'
                ),
                created_at=reported,
                updated_at=reported,
            ))

    SurveillanceReport.objects.bulk_create(reports, batch_size=400)
    return len(reports)


class Command(BaseCommand):
    help = 'Load three years of closed cases for the analytics and map date filters.'

    def handle(self, *args, **options):
        assert_safe_for_destructive_commands('seed_presentation_history')
        created = seed_presentation_history()
        self.stdout.write(self.style.SUCCESS(
            f'Loaded {created} closed historical cases for the 3-year filters.'
        ))
