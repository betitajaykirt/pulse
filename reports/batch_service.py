"""Persist batch case-report sessions and per-patient child rows."""

import json

from decimal import Decimal



from django.utils import timezone

from myapp.models import (

    SurveillanceSession, PatientCase, SurveillanceReport, Barangay,

    PIDSR_SYMPTOM_LABELS, DEFAULT_SYNDROME_TYPE,

)

from myapp.symptom_utils import symptom_label_map

from .ml_service import analyze_batch_cases

from .risk_service import trigger_aptas_for_report





def format_symptoms_for_remarks(symptoms):

    labels = symptom_label_map()

    return ', '.join(labels.get(code, PIDSR_SYMPTOM_LABELS.get(code, code)) for code in symptoms)





def build_remarks(purok_street, symptoms, age=None, sex=None, disease_label=None, is_anomaly=False,
                  patient_name=None, detailed_address=None):

    parts = []

    if patient_name and patient_name != 'Unknown Resident':

        parts.append(f'Patient: {patient_name}')

    if age is not None:

        parts.append(f'Age: {age}')

    if sex:

        parts.append(f'Sex: {sex}')

    if detailed_address:

        parts.append(f'Address: {detailed_address}')

    elif purok_street:

        parts.append(f'Address: {purok_street}')

    if disease_label:

        parts.append(f'ML Classification: {disease_label}')

    if is_anomaly:

        parts.append('Outbreak anomaly flag: YES')

    if symptoms:

        parts.append(f'Symptoms: {format_symptoms_for_remarks(symptoms)}')

    return ' | '.join(parts) if parts else None





def resolve_barangay_id(barangay_value, locked_barangay=None):

    if locked_barangay:

        return locked_barangay.id

    if barangay_value is None or barangay_value == '':

        return None

    if str(barangay_value).isdigit():

        return int(barangay_value)

    row = Barangay.objects.filter(barangay_name=str(barangay_value)).first()

    return row.id if row else None





def _parse_optional_date(raw):

    if not raw:

        return None

    s = str(raw).strip()

    if not s:

        return None

    from datetime import datetime

    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y'):

        try:

            return datetime.strptime(s, fmt).date()

        except ValueError:

            continue

    return None





def _extract_demographics(case):

    patient_name = (case.get('patient_name') or '').strip() or 'Unknown Resident'

    civil_status = (case.get('civil_status') or '').strip() or None

    date_of_birth = _parse_optional_date(case.get('date_of_birth'))

    detailed_address = (case.get('detailed_address') or case.get('purok_street') or '').strip()

    is_student = bool(case.get('is_student'))

    grade_year_section = None

    school_name = None

    if is_student:

        grade_year_section = (case.get('grade_year_section') or '').strip() or None

        school_name = (case.get('school_name') or '').strip() or None

    return {

        'patient_name': patient_name,

        'civil_status': civil_status,

        'date_of_birth': date_of_birth,

        'detailed_address': detailed_address,

        'is_student': is_student,

        'grade_year_section': grade_year_section,

        'school_name': school_name,

    }





def save_batch_submission(*, payload, submitted_by_id, locked_barangay=None):

    """

    Create a SurveillanceSession parent and PatientCase + SurveillanceReport children.



    Each case is analyzed live via ``ml_pipeline.py`` (Isolation Forest + Random Forest)

    before persistence. Reports are stored as auto-validated **Probable** cases.

    """

    cases = payload.get('cases') or []

    if not cases:

        raise ValueError('At least one patient case is required.')



    # Resolve barangay names for spatial-temporal ML features

    barangay_name_map = {

        str(b.id): b.barangay_name for b in Barangay.objects.all()

    }

    if locked_barangay:

        barangay_name_map[str(locked_barangay.id)] = locked_barangay.barangay_name



    ml_results = analyze_batch_cases(cases, barangay_names=barangay_name_map)



    now = timezone.now()

    session = SurveillanceSession.objects.create(

        submitted_by_id=submitted_by_id,

        case_classification='probable',

        syndrome_type=DEFAULT_SYNDROME_TYPE,

        source_type='BHW',

        patient_count=len(cases),

        session_date=now,

        created_at=now,

        updated_at=now,

    )



    created_reports = []

    for idx, case in enumerate(cases, start=1):

        ml = ml_results[idx - 1]

        disease_label = ml['disease_label']

        case_classif = ml['case_classification']



        barangay_id = resolve_barangay_id(

            case.get('barangay') or case.get('barangay_id'),

            locked_barangay=locked_barangay,

        )

        if not barangay_id:

            raise ValueError(f'Patient #{idx}: barangay is required.')



        if locked_barangay and barangay_id != locked_barangay.id:

            raise ValueError(f'Patient #{idx}: barangay must match your assigned barangay.')



        purok = (case.get('purok_street') or '').strip()

        if not purok:

            raise ValueError(f'Patient #{idx}: purok / street / landmark is required.')



        onset = _parse_optional_date(case.get('date_of_onset') or case.get('onset_date'))

        if not onset:

            raise ValueError(f'Patient #{idx}: date of onset is required.')

        demographics = _extract_demographics(case)

        demographics['detailed_address'] = purok



        age_raw = case.get('age')

        if age_raw is None or age_raw == '':

            raise ValueError(f'Patient #{idx}: age is required.')

        try:

            age = int(age_raw)

        except (TypeError, ValueError):

            raise ValueError(f'Patient #{idx}: age must be a valid number.')

        if age < 0 or age > 120:

            raise ValueError(f'Patient #{idx}: age must be between 0 and 120.')



        sex = (case.get('sex') or '').strip()

        if sex not in ('Male', 'Female'):

            raise ValueError(f'Patient #{idx}: sex must be Male or Female.')



        try:

            symptoms = PatientCase.normalize_symptoms(case.get('symptoms') or [])

        except ValueError as exc:

            raise ValueError(f'Patient #{idx}: {exc}') from exc



        lat = case.get('latitude')

        lng = case.get('longitude')

        remarks = build_remarks(

            purok, symptoms, age=age, sex=sex,

            disease_label=disease_label, is_anomaly=ml['is_anomaly'],

            patient_name=demographics['patient_name'],

            detailed_address=demographics['detailed_address'] or purok,

        )



        report = SurveillanceReport.objects.create(

            barangay_id=barangay_id,

            submitted_by_id=submitted_by_id,

            session=session,

            source_type='BHW',

            syndrome_type=disease_label,

            suspected_disease=disease_label,

            case_count=1,

            patient_name=demographics['patient_name'],

            civil_status=demographics['civil_status'],

            date_of_birth=demographics['date_of_birth'],

            detailed_address=purok,

            is_student=demographics['is_student'],

            grade_year_section=demographics['grade_year_section'],

            school_name=demographics['school_name'],

            date_of_onset=onset,

            case_classification=case_classif,

            status='Probable',

            validation_status='validated',

            is_anomaly=ml['is_anomaly'],

            ml_anomaly_score=Decimal(str(round(ml['anomaly_score'], 4))),

            remarks=remarks,

            latitude=float(lat) if lat not in (None, '') else None,

            longitude=float(lng) if lng not in (None, '') else None,

            report_date=now,

            created_at=now,

            updated_at=now,

        )

        created_reports.append(report)



        patient_case = PatientCase.objects.create(

            session=session,

            barangay_id=barangay_id,

            surveillance_report=report,

            sequence_no=idx,

            patient_name=demographics['patient_name'],

            civil_status=demographics['civil_status'],

            date_of_birth=demographics['date_of_birth'],

            detailed_address=purok,

            is_student=demographics['is_student'],

            grade_year_section=demographics['grade_year_section'],

            school_name=demographics['school_name'],

            age=age,

            sex=sex,

            purok_street=purok,

            latitude=float(lat) if lat not in (None, '') else None,

            longitude=float(lng) if lng not in (None, '') else None,

            date_of_onset=onset,

            symptoms_json=json.dumps(symptoms),

            fever_duration=None,

            created_at=now,

        )

        patient_case.sync_symptoms_m2m(symptoms)



        trigger_aptas_for_report(report.id, is_anomaly=ml['is_anomaly'])



    # Update session summary with dominant ML label

    if created_reports:

        session.syndrome_type = created_reports[0].syndrome_type

        session.case_classification = created_reports[0].case_classification

        session.updated_at = now

        session.save(update_fields=['syndrome_type', 'case_classification', 'updated_at'])



    return session, created_reports


