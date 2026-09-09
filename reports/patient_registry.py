"""Link submitted cases to a Patient row and block duplicate open cases."""
from __future__ import annotations

from datetime import date

from reports.case_scope import INACTIVE_CASE_STATUSES as CLOSED_CASE_STATUSES
from myapp.models import Patient, SurveillanceReport
UNKNOWN_PATIENT_NAME = 'unknown resident'


class DuplicatePatientCaseError(ValueError):
    """Raised when name + birthdate + barangay already has an open case."""

    code = 'duplicate_patient'

    def __init__(self, message: str, duplicates: list[dict]):
        super().__init__(message)
        self.duplicates = duplicates

    def as_list(self) -> list[dict]:
        return list(self.duplicates)


def normalize_patient_name(name: str | None) -> str:
    return ' '.join((name or '').casefold().split())


def patient_identity_key(full_name: str, birthdate: date, barangay_id: int) -> tuple:
    return (normalize_patient_name(full_name), birthdate, int(barangay_id))


def names_match(left: str | None, right: str | None) -> bool:
    a = normalize_patient_name(left)
    b = normalize_patient_name(right)
    return bool(a) and a == b and a != UNKNOWN_PATIENT_NAME


def find_matching_patients(full_name: str, birthdate: date, barangay_id: int) -> list:
    qs = Patient.objects.filter(birthdate=birthdate, barangay_id=barangay_id)
    return [row for row in qs if names_match(row.full_name, full_name)]


def find_open_duplicate_cases(full_name: str, birthdate: date, barangay_id: int) -> list:
    """Open reports in this barangay with the same name and birthdate."""
    matches = find_matching_patients(full_name, birthdate, barangay_id)
    patient_ids = [row.id for row in matches]
    found = {}

    by_fields = (
        SurveillanceReport.objects.filter(
            barangay_id=barangay_id,
            date_of_birth=birthdate,
        )
        .exclude(status__in=CLOSED_CASE_STATUSES)
        .only('id', 'status', 'patient_id', 'patient_name', 'date_of_onset', 'syndrome_type')
    )
    for report in by_fields:
        if names_match(report.patient_name, full_name):
            found[report.id] = report

    if patient_ids:
        by_patient = (
            SurveillanceReport.objects.filter(
                barangay_id=barangay_id,
                patient_id__in=patient_ids,
            )
            .exclude(status__in=CLOSED_CASE_STATUSES)
            .only('id', 'status', 'patient_id', 'patient_name', 'date_of_onset', 'syndrome_type')
        )
        for report in by_patient:
            found[report.id] = report

    return list(found.values())


def serialize_duplicate(report, *, case_index: int, patient_name: str) -> dict:
    onset = getattr(report, 'date_of_onset', None)
    return {
        'case_index': case_index,
        'patient_name': patient_name,
        'report_id': report.id,
        'status': report.status,
        'patient_id': report.patient_id,
        'syndrome_type': report.syndrome_type or '',
        'date_of_onset': onset.isoformat() if onset else '',
    }


def assert_no_duplicate_case(
    *,
    full_name: str,
    birthdate: date,
    barangay_id: int,
    case_index: int,
    allow_duplicate: bool,
    seen_keys: set | None = None,
) -> None:
    if allow_duplicate:
        return

    key = patient_identity_key(full_name, birthdate, barangay_id)
    if seen_keys is not None and key in seen_keys:
        raise DuplicatePatientCaseError(
            (
                f'Patient #{case_index} matches another case in this batch '
                f'({full_name}). Remove the duplicate or submit with staff override '
                'if these are distinct additional cases.'
            ),
            [{
                'case_index': case_index,
                'patient_name': full_name,
                'report_id': None,
                'status': 'In this batch',
                'patient_id': None,
                'syndrome_type': '',
                'date_of_onset': '',
            }],
        )

    open_cases = find_open_duplicate_cases(full_name, birthdate, barangay_id)
    if not open_cases:
        return

    duplicates = [
        serialize_duplicate(report, case_index=case_index, patient_name=full_name)
        for report in open_cases
    ]
    first = duplicates[0]
    report_label = f"#{first['report_id']}" if first['report_id'] else 'an existing case'
    raise DuplicatePatientCaseError(
        (
            f'Patient #{case_index} {full_name} already has an open case '
            f"({report_label}, {first['status']}) in this barangay. "
            'Submit with staff override only if this is an additional case for the same resident.'
        ),
        duplicates,
    )


def get_or_create_patient(
    *,
    full_name: str,
    birthdate: date,
    barangay_id: int,
    sex: str = '',
    address: str = '',
) -> Patient:
    matches = find_matching_patients(full_name, birthdate, barangay_id)
    if matches:
        patient = matches[0]
        updates = []
        if address and not (patient.address or '').strip():
            patient.address = address
            updates.append('address')
        if sex and not (patient.sex or '').strip():
            patient.sex = sex
            updates.append('sex')
        if updates:
            patient.save(update_fields=updates)
        return patient

    return Patient.objects.create(
        full_name=full_name.strip(),
        sex=sex or '',
        address=address or '',
        birthdate=birthdate,
        barangay_id=barangay_id,
    )


def link_or_create_patient(
    *,
    full_name: str,
    birthdate: date | None,
    barangay_id: int,
    sex: str = '',
    address: str = '',
    allow_duplicate: bool = False,
    case_index: int = 1,
    seen_keys: set | None = None,
) -> Patient:
    name = (full_name or '').strip()
    if not name or normalize_patient_name(name) == UNKNOWN_PATIENT_NAME:
        raise ValueError(f'Patient #{case_index}: patient name is required.')
    if birthdate is None:
        raise ValueError(f'Patient #{case_index}: date of birth is required.')

    assert_no_duplicate_case(
        full_name=name,
        birthdate=birthdate,
        barangay_id=barangay_id,
        case_index=case_index,
        allow_duplicate=allow_duplicate,
        seen_keys=seen_keys,
    )
    if seen_keys is not None:
        seen_keys.add(patient_identity_key(name, birthdate, barangay_id))
    return get_or_create_patient(
        full_name=name,
        birthdate=birthdate,
        barangay_id=barangay_id,
        sex=sex,
        address=address,
    )
