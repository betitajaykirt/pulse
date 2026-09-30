"""Closed historical cases for the 1-year and 3-year presentation filters."""
from __future__ import annotations

import json
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models.signals import pre_delete
from django.utils import timezone

from mysite.command_safety import assert_safe_for_destructive_commands

from myapp.models import (
    Barangay,
    Patient,
    PatientCase,
    SurveillanceReport,
    SurveillanceSession,
    Symptom,
    User,
)
from reports.management.commands.seed_dummy_reports import SYMPTOMS_BY_DISEASE
from reports.pidsr_schema import PIDSR_SYMPTOM_LABELS
from reports.signals import reconcile_after_report_delete

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

FIRST_NAMES = {
    'Female': (
        'Ana', 'Diana', 'Elena', 'Gina', 'Ivy', 'Kara', 'Mia', 'Olive',
    ),
    'Male': (
        'Ben', 'Carlo', 'Felix', 'Hugo', 'Jose', 'Leo', 'Nico', 'Paolo',
    ),
}
LAST_NAMES = (
    'Santos', 'Reyes', 'Cruz', 'Bautista', 'Garcia', 'Lopez', 'Ramos', 'Flores',
)
MIDDLE_NAMES = (
    'Mae', 'Luis', 'Joy', 'Miguel', 'Rose', 'Andres', 'Liza', 'Carlo',
)
CIVIL_STATUSES = ('Single', 'Married', 'Widowed', 'Separated')


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


def _birthdate(age: int, onset: date, rng: random.Random) -> date:
    year = onset.year - max(age, 0)
    born = date(year, rng.randint(1, 12), rng.randint(1, 28))
    if date(onset.year, born.month, min(born.day, 28)) > onset:
        born = date(year - 1, born.month, born.day)
    return born


def _civil_status(age: int, rng: random.Random) -> str:
    if age < 18:
        return 'Single'
    if age < 25:
        return rng.choice(('Single', 'Single', 'Married'))
    if age > 60:
        return rng.choice(('Married', 'Married', 'Widowed'))
    return rng.choice(CIVIL_STATUSES[:3])


def _student_fields(age: int, barangay_name: str, rng: random.Random):
    if age > 21 or age < 5 or rng.random() < 0.2:
        return False, None, None
    if age <= 11:
        grade = f'Grade {rng.randint(1, 6)} - {rng.choice(("A", "B", "C"))}'
        school = f'{barangay_name} Elementary School'
    elif age <= 18:
        grade = f'Grade {rng.randint(7, 12)} - {rng.choice(("A", "B"))}'
        school = f'{barangay_name} National High School'
    else:
        grade = f'{rng.randint(1, 4)}th Year'
        school = 'Bago City College'
    return True, grade, school


def _symptoms_for(disease: str) -> list[str]:
    return list(SYMPTOMS_BY_DISEASE.get(disease) or ['fever', 'body_malaise'])


def _remarks(name, age, sex, purok, disease, symptoms, confidence) -> str:
    labels = ', '.join(PIDSR_SYMPTOM_LABELS.get(code, code) for code in symptoms)
    percent = f'{confidence * 100:.1f}'
    return (
        f'Patient: {name} | Age: {age} | Sex: {sex} | Address: {purok} | '
        f'ML Classification: {disease} | ML Top Prediction: {disease} | '
        f'ML Confidence: {percent}% | Symptoms: {labels} | {HISTORY_MARKER}'
    )


def _purge_history() -> None:
    pre_delete.disconnect(reconcile_after_report_delete, sender=SurveillanceReport)
    try:
        _purge_history_rows()
    finally:
        pre_delete.connect(reconcile_after_report_delete, sender=SurveillanceReport)


def _purge_history_rows() -> None:
    report_ids = list(
        SurveillanceReport.objects.filter(remarks__icontains=HISTORY_MARKER)
        .values_list('id', flat=True)
    )
    cases = PatientCase.objects.filter(surveillance_report_id__in=report_ids)
    case_ids = list(cases.values_list('id', flat=True))
    through = PatientCase.symptoms.through
    case_field = next(
        field.name for field in through._meta.fields
        if getattr(field, 'related_model', None) is PatientCase
    )
    if case_ids:
        through.objects.filter(**{f'{case_field}_id__in': case_ids}).delete()
    patient_ids = list(
        SurveillanceReport.objects.filter(id__in=report_ids)
        .exclude(patient_id=None)
        .values_list('patient_id', flat=True)
    )
    cases.delete()
    SurveillanceReport.objects.filter(id__in=report_ids).delete()
    if patient_ids:
        Patient.objects.filter(id__in=patient_ids).delete()
    SurveillanceSession.objects.filter(syndrome_type=HISTORY_MARKER).delete()


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

    _purge_history()
    submitter = User.objects.filter(status='active').order_by('id').first()
    if submitter is None:
        raise RuntimeError('No active user is available to own the history session.')

    barangays = []
    for barangay in Barangay.objects.all():
        if barangay.latitude is None or barangay.longitude is None:
            continue
        barangays.append(barangay)
    if not barangays:
        return 0

    zone = timezone.get_current_timezone()
    drafted = []
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
            if disease in ('Hand, Foot, and Mouth Disease', 'Measles'):
                age = rng.randint(1, 12)
            elif rng.random() < 0.25:
                age = rng.randint(1, 17)
            else:
                age = rng.randint(18, 72)
            sex = rng.choice(('Male', 'Female'))
            first = rng.choice(FIRST_NAMES[sex])
            middle = rng.choice(MIDDLE_NAMES) if rng.random() < 0.7 else ''
            last = rng.choice(LAST_NAMES)
            full_name = ' '.join(part for part in (first, middle, last) if part)
            purok = f'Purok {rng.randint(1, 8)}, {barangay.barangay_name}'
            is_student, grade, school = _student_fields(age, barangay.barangay_name, rng)
            symptoms = _symptoms_for(disease)
            born = _birthdate(age, onset, rng)
            reported = timezone.make_aware(datetime.combine(onset, time(8, 0)), zone)
            confidence = {
                'confirmed': rng.uniform(0.82, 0.96),
                'probable': rng.uniform(0.55, 0.78),
                'suspected': rng.uniform(0.32, 0.48),
            }[classification]
            remarks = _remarks(full_name, age, sex, purok, disease, symptoms, confidence)
            drafted.append({
                'barangay': barangay,
                'disease': disease,
                'classification': classification,
                'full_name': full_name,
                'sex': sex,
                'age': age,
                'born': born,
                'purok': purok,
                'civil_status': _civil_status(age, rng),
                'is_student': is_student,
                'grade': grade,
                'school': school,
                'symptoms': symptoms,
                'lat': Decimal(f'{lat:.7f}'),
                'lng': Decimal(f'{lng:.7f}'),
                'onset': onset,
                'reported': reported,
                'remarks': remarks,
                'confidence': confidence,
            })

    if not drafted:
        return 0

    anchor = drafted[-1]['reported']
    session = SurveillanceSession.objects.create(
        submitted_by=submitter,
        case_classification='confirmed',
        syndrome_type=HISTORY_MARKER,
        source_type='historical',
        patient_count=len(drafted),
        session_date=anchor,
        created_at=anchor,
        updated_at=anchor,
    )
    patients = Patient.objects.bulk_create([
        Patient(
            full_name=row['full_name'],
            sex=row['sex'],
            address=row['purok'],
            birthdate=row['born'],
            barangay=row['barangay'],
        )
        for row in drafted
    ], batch_size=400)
    reports = SurveillanceReport.objects.bulk_create([
        SurveillanceReport(
            barangay=row['barangay'],
            patient=patient,
            submitted_by=submitter,
            session=session,
            source_type='historical',
            syndrome_type=row['disease'],
            suspected_disease=row['disease'],
            case_count=1,
            patient_name=row['full_name'],
            civil_status=row['civil_status'],
            date_of_birth=row['born'],
            detailed_address=row['purok'],
            is_student=row['is_student'],
            grade_year_section=row['grade'],
            school_name=row['school'],
            date_of_onset=row['onset'],
            report_date=row['reported'],
            case_classification=row['classification'],
            status='Closed',
            latitude=row['lat'],
            longitude=row['lng'],
            validation_status='validated' if row['classification'] == 'confirmed' else 'pending',
            resolution_outcome='recovered',
            closed_at=row['reported'] + timedelta(days=7),
            remarks=row['remarks'],
            created_at=row['reported'],
            updated_at=row['reported'],
        )
        for row, patient in zip(drafted, patients)
    ], batch_size=400)
    cases = PatientCase.objects.bulk_create([
        PatientCase(
            session=session,
            barangay=row['barangay'],
            surveillance_report=report,
            sequence_no=index,
            patient_name=row['full_name'],
            civil_status=row['civil_status'],
            date_of_birth=row['born'],
            detailed_address=row['purok'],
            is_student=row['is_student'],
            grade_year_section=row['grade'],
            school_name=row['school'],
            age=row['age'],
            sex=row['sex'],
            purok_street=row['purok'],
            latitude=row['lat'],
            longitude=row['lng'],
            date_of_onset=row['onset'],
            symptoms_json=json.dumps(row['symptoms']),
            fever_duration=rng.randint(2, 5) if 'fever' in row['symptoms'] else None,
            created_at=row['reported'],
        )
        for index, (row, report) in enumerate(zip(drafted, reports), start=1)
    ], batch_size=400)

    symptom_ids = {
        code: symptom_id
        for code, symptom_id in Symptom.objects.values_list('code', 'id')
    }
    through = PatientCase.symptoms.through
    case_field = next(
        field.name for field in through._meta.fields
        if getattr(field, 'related_model', None) is PatientCase
    )
    symptom_field = next(
        field.name for field in through._meta.fields
        if getattr(field, 'related_model', None) is Symptom
    )
    links = []
    for case, row in zip(cases, drafted):
        for code in row['symptoms']:
            symptom_id = symptom_ids.get(code)
            if symptom_id:
                links.append(through(**{
                    f'{case_field}_id': case.id,
                    f'{symptom_field}_id': symptom_id,
                }))
    if links:
        through.objects.bulk_create(links, batch_size=1000)
    return len(reports)


class Command(BaseCommand):
    help = 'Load three years of closed cases for the analytics and map date filters.'

    def handle(self, *args, **options):
        assert_safe_for_destructive_commands('seed_presentation_history')
        created = seed_presentation_history()
        self.stdout.write(self.style.SUCCESS(
            f'Loaded {created} closed historical cases for the 3-year filters.'
        ))
