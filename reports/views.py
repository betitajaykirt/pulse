"""
Reports app — Sprint 2
Covers:
  - Syndromic Health Data Collection (case report submission)
  - Real-Time Data Ingestion (validation + storage pipeline)
  - Health Incident Reporting (admin incident report generation)
"""
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, F, Value, CharField, Sum
from django.db.models.functions import Concat
from datetime import datetime, timedelta
from accounts.auth_utils import login_required, role_required
from myapp.models import Barangay, User, SurveillanceReport, Admin, Patient, PatientCase, SYMPTOM_CATEGORY_CHOICES
from myapp.barangay_scope import (
    BARANGAY_SCOPED_ROLES, get_request_barangay, is_city_wide_role,
    resolve_user_barangay, barangay_queryset_filter,
)
from myapp.audit_utils import log_audit, log_system
from .risk_service import evaluate_report_risk
from .batch_service import save_batch_submission
from .threshold_service import process_confirmation_threshold_check
from myapp.symptom_utils import build_symptom_groups_for_ui


# ── Syndrome / disease reference data ────────────────────────────

SYNDROME_TYPES = [
    'Dengue',
    'Hand, Foot and Mouth Disease (HFMD)',
]

DISEASE_CATEGORIES = [
    'Communicable Disease', 'Vector-Borne Disease',
    'Water-Borne Disease', 'Respiratory Disease',
    'Vaccine-Preventable Disease', 'Zoonotic Disease', 'Other',
]


# ── Submit Case Report (Health Officer / BHW / Encoder) ──────────

@login_required
def submit_report(request):
    role = request.session.get('role')
    if role not in ('health_officer', 'barangay_health_worker', 'encoder'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    uid = request.session['user_id']
    user = User.objects.filter(id=uid).first()
    locked_barangay = None
    assigned_barangay = None

    if role in BARANGAY_SCOPED_ROLES:
        locked_barangay = resolve_user_barangay(user)
        if locked_barangay:
            assigned_barangay = locked_barangay.barangay_name
            barangays = Barangay.objects.filter(id=locked_barangay.id)
        else:
            barangays = Barangay.objects.none()
            messages.warning(request, 'No barangay is assigned to your account. Contact an administrator.')
    else:
        barangays = Barangay.objects.all().order_by('barangay_name')

    if request.method == 'POST':
        content_type = (request.content_type or '').split(';')[0].strip().lower()
        if content_type == 'application/json' or request.body.strip().startswith(b'{'):
            return _process_batch_submission(request, locked_barangay=locked_barangay)
        return _process_report_submission(request, barangays, locked_barangay=locked_barangay)

    barangay_options = [
        {'id': b.id, 'name': b.barangay_name} for b in barangays
    ]

    return render(request, 'reports/submit_report.html', {
        'barangays': barangays,
        'barangay_options_json': json.dumps(barangay_options),
        'symptom_groups_json': json.dumps(build_symptom_groups_for_ui()),
        'assigned_barangay': assigned_barangay,
        'barangay_locked': locked_barangay is not None,
        'default_barangay_id': locked_barangay.id if locked_barangay else '',
    })


def _process_batch_submission(request, locked_barangay=None):
    """Handle JSON batch payload from the dynamic patient accordion form."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON payload.'}, status=400)

    if not isinstance(payload.get('cases'), list):
        return JsonResponse({'ok': False, 'error': 'Payload must include a "cases" array.'}, status=400)

    uid = request.session['user_id']
    try:
        session, reports = save_batch_submission(
            payload=payload,
            submitted_by_id=uid,
            locked_barangay=locked_barangay,
        )
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': f'Server error while saving: {exc}'}, status=500)

    log_system(
        'batch_report_submitted',
        f'Session #{session.id} with {len(reports)} patient case(s) submitted.',
        user_role=request.session.get('role'),
        user_id=uid,
        module='reports',
        ip_address=request.META.get('REMOTE_ADDR'),
        request=request,
    )

    return JsonResponse({
        'ok': True,
        'session_id': session.id,
        'report_ids': [r.id for r in reports],
        'message': (
            f'Successfully submitted {len(reports)} patient case(s). '
            f'ML pipeline classified each as Probable pending lab confirmation.'
        ),
        'redirect': '/reports/my/',
    })


def _process_report_submission(request, barangays, locked_barangay=None):
    """Validate and store a submitted case report."""
    uid      = request.session['user_id']
    classif  = request.POST.get('case_classification', 'suspected').strip()

    # Confirmed uses separate field names to avoid required-attr conflicts
    if classif == 'confirmed':
        case_count  = request.POST.get('case_count_confirmed', '1').strip()
        onset_date  = request.POST.get('date_of_onset_confirmed', '').strip()
        patient_addr_key = 'patient_address_confirmed'
    else:
        case_count  = request.POST.get('case_count', '1').strip()
        onset_date  = request.POST.get('date_of_onset', '').strip()
        patient_addr_key = 'patient_address'

    if locked_barangay:
        barangay_id = str(locked_barangay.id)
    elif classif == 'confirmed':
        barangay_id = request.POST.get('barangay_id_confirmed', '').strip()
    else:
        barangay_id = request.POST.get('barangay_id', '').strip()

    syndrome    = request.POST.get('syndrome_type', '').strip()
    source_type = request.POST.get('source_type', 'BHW').strip()
    remarks     = request.POST.get('remarks', '').strip()
    lat         = request.POST.get('latitude', '').strip()
    lng         = request.POST.get('longitude', '').strip()

    if source_type not in ('BHW', 'manual', 'environmental_feed'):
        source_type = 'BHW'

    # Build symptom summary from checkboxes
    symptom_fields = {
        'sym_fever': 'Fever', 'sym_petechiae': 'Petechiae', 'sym_reticular_pain': 'Reticular pain',
        'sym_acchymoses': 'Acchymoses', 'sym_diaphoresis': 'Diaphoresis',
        'sym_maculo_rash': 'Maculo-popular rash', 'sym_joint_swelling': 'Joint swelling',
        'sym_hepatomegaly': 'Hepatomegaly', 'sym_body_malaise': 'Body malaise',
        'sym_lymphadenopthy': 'Lymphadenopthy', 'sym_mild_urti': 'Mild URTI',
        'sym_leucopenia': 'Leucopenia', 'sym_nausea': 'Nausea/vomiting',
        'sym_epistaxis': 'Epistaxis', 'sym_weakness': 'Marked weakness',
        'sym_hematemesis': 'Hematemesis', 'sym_diarrhea': 'Diarrhea',
        'sym_restlessness': 'Severe restlessness', 'sym_tourniquet': '(+) Tourniquet',
        'sym_easy_bruising': 'Easy bruisability',
        'hfmd_oral_ulcers': 'Oral ulcers', 'hfmd_loss_appetite': 'Loss of appetite',
        'hfmd_body_malaise': 'Body malaise', 'hfmd_sore_throat': 'Sore throat',
        'hfmd_nausea': 'Nausea/vomiting', 'hfmd_difficulty_breathing': 'Difficulty breathing',
        'hfmd_afp': 'Acute Flaccid Paralysis', 'hfmd_meningeal': 'Meningeal irritation',
    }
    symptoms_present = [label for field, label in symptom_fields.items() if request.POST.get(field)]

    patient_name = f"{request.POST.get('patient_first_name','').strip()} {request.POST.get('patient_last_name','').strip()}".strip()
    patient_age  = request.POST.get('patient_age', '').strip()
    patient_sex  = request.POST.get('patient_sex', '').strip()
    patient_addr = request.POST.get(patient_addr_key, '').strip()
    outcome      = request.POST.get('patient_outcome', '').strip()

    summary_parts = []
    if patient_name: summary_parts.append(f"Patient: {patient_name}")
    if patient_age:  summary_parts.append(f"Age: {patient_age}")
    if patient_sex:  summary_parts.append(f"Sex: {patient_sex}")
    if patient_addr: summary_parts.append(f"Address: {patient_addr}")
    if symptoms_present: summary_parts.append(f"Symptoms: {', '.join(symptoms_present)}")
    if outcome:      summary_parts.append(f"Outcome: {outcome}")
    if remarks:      summary_parts.append(f"Notes: {remarks}")
    full_remarks = ' | '.join(summary_parts)

    errors = []
    if not barangay_id:  errors.append('Barangay is required.')
    if not syndrome:     errors.append('Disease type is required.')
    if not case_count.isdigit() or int(case_count) < 1:
        errors.append('Case count must be a positive number.')
    if classif not in ('suspected', 'probable', 'confirmed'):
        errors.append('Invalid case classification.')

    if errors:
        for e in errors:
            messages.error(request, e)
        return render(request, 'reports/submit_report.html', {
            'barangays': barangays,
            'syndrome_types': SYNDROME_TYPES,
            'disease_categories': DISEASE_CATEGORIES,
            'assigned_barangay': locked_barangay.barangay_name if locked_barangay else request.POST.get('assigned_barangay', ''),
            'barangay_locked': locked_barangay is not None,
            'old': request.POST,
        })

    birthdate = _parse_patient_birthdate(request.POST.get('patient_dob', '').strip())
    patient = _get_or_create_patient(
        barangay_id=int(barangay_id),
        full_name=patient_name,
        sex=patient_sex,
        birthdate=birthdate,
        address=patient_addr,
    )

    report = SurveillanceReport.objects.create(
        barangay_id=barangay_id,
        patient=patient,
        submitted_by_id=uid,
        source_type=source_type,
        syndrome_type=syndrome,
        case_count=int(case_count),
        patient_name=patient_name or 'Unknown Resident',
        date_of_birth=birthdate,
        detailed_address=patient_addr or '',
        date_of_onset=onset_date or None,
        case_classification=classif,
        status='Suspected',
        validation_status='pending',
        remarks=full_remarks or None,
        latitude=float(lat) if lat else None,
        longitude=float(lng) if lng else None,
        report_date=timezone.now(),
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )

    log_system(
        'report_submitted',
        f'Report #{report.id} submitted for barangay #{barangay_id}.',
        user_role=request.session.get('role'),
        user_id=uid,
        module='reports',
        ip_address=request.META.get('REMOTE_ADDR'),
        request=request,
    )

    messages.success(request, 'Case report submitted successfully. It is now pending validation.')
    return redirect('my_reports')


def _parse_patient_birthdate(raw):
    if not raw:
        return None
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        return None


def _get_or_create_patient(barangay_id, full_name, sex, birthdate, address):
    """Find an existing patient by exact name + birthdate, or create a new record."""
    if not full_name or not birthdate:
        return None

    patient = Patient.objects.filter(
        full_name=full_name,
        birthdate=birthdate,
    ).first()
    if patient:
        return patient

    return Patient.objects.create(
        full_name=full_name,
        sex=sex or '',
        address=address or '',
        birthdate=birthdate,
        barangay_id=barangay_id,
    )


# ── My Reports (submitted by current user) ───────────────────────

@login_required
def my_reports(request):
    uid = request.session['user_id']
    reports = SurveillanceReport.objects.filter(submitted_by_id=uid)
    reports = barangay_queryset_filter(request, reports).select_related('barangay').annotate(
        barangay_name=F('barangay__barangay_name')
    ).order_by('-report_date')
    return render(request, 'reports/my_reports.html', {'reports': reports})


# ── Case Records — validate/update/search ─────────────────────────

@role_required(
    'admin', 'super_admin', 'surveillance_officer', 'health_officer',
    'barangay_health_worker', 'encoder',
)
def case_records(request):
    search          = request.GET.get('search', '').strip()
    validation      = request.GET.get('validation', '').strip()
    case_status     = request.GET.get('case_status', '').strip()
    barangay        = request.GET.get('barangay', '').strip()
    symptom_category = request.GET.get('symptom_category', '').strip()
    role            = request.session.get('role')
    city_wide       = is_city_wide_role(role)
    scoped_barangay = get_request_barangay(request)

    q = Q()
    if search:
        q &= (Q(syndrome_type__icontains=search) |
              Q(suspected_disease__icontains=search) |
              Q(barangay__barangay_name__icontains=search) |
              Q(patient_name__icontains=search) |
              Q(remarks__icontains=search))
    if validation:
        q &= Q(validation_status=validation)
    if case_status:
        q &= Q(status=case_status)
    if scoped_barangay:
        q &= Q(barangay_id=scoped_barangay.id)
    elif barangay and city_wide:
        q &= Q(barangay_id=barangay)
    if symptom_category:
        filter_barangay_id = scoped_barangay.id if scoped_barangay else (
            int(barangay) if barangay and str(barangay).isdigit() else None
        )
        report_ids = PatientCase.surveillance_report_ids_for_category(
            symptom_category,
            barangay_id=filter_barangay_id,
        )
        q &= Q(id__in=report_ids)

    records = SurveillanceReport.objects.filter(q).select_related('barangay', 'submitted_by').annotate(
        barangay_name=F('barangay__barangay_name'),
        submitted_by_name=Concat(
            F('submitted_by__first_name'),
            Value(' '),
            F('submitted_by__last_name'),
            output_field=CharField()
        )
    ).order_by('-report_date')[:200]

    if city_wide:
        barangays = Barangay.objects.all().order_by('barangay_name')
    elif scoped_barangay:
        barangays = Barangay.objects.filter(id=scoped_barangay.id)
    else:
        barangays = Barangay.objects.none()

    return render(request, 'reports/case_records.html', {
        'records': records,
        'barangays': barangays,
        'symptom_category_choices': SYMPTOM_CATEGORY_CHOICES,
        'search': search,
        'validation': validation,
        'case_status': case_status,
        'barangay': barangay,
        'symptom_category': symptom_category,
        'city_wide': city_wide,
        'can_confirm': role in ('admin', 'super_admin', 'health_officer'),
        'can_validate': False,
    })


def _extract_patient_name_from_remarks(remarks: str) -> str:
    if not remarks:
        return ''
    for part in remarks.split(' | '):
        if part.startswith('Patient:'):
            return part.replace('Patient:', '', 1).strip()
    return ''


def _patient_display_for_report(report) -> dict:
    """Build patient label and ID display for confirmation queue rows."""
    patient_cases = list(report.patient_case.all()) if hasattr(report, 'patient_case') else []
    pc = patient_cases[0] if patient_cases else None

    stored_name = (getattr(report, 'patient_name', None) or '').strip()
    if stored_name and stored_name != 'Unknown Resident':
        return {
            'name': stored_name,
            'id_display': str(report.patient_id or report.id),
            'onset_date': report.date_of_onset,
        }

    if report.patient_id and report.patient:
        return {
            'name': report.patient.full_name,
            'id_display': str(report.patient_id),
            'onset_date': report.date_of_onset,
        }

    name_from_remarks = _extract_patient_name_from_remarks(report.remarks or '')
    if name_from_remarks:
        return {
            'name': name_from_remarks,
            'id_display': str(report.id),
            'onset_date': report.date_of_onset,
        }

    if pc:
        pc_name = (getattr(pc, 'patient_name', None) or '').strip()
        if pc_name and pc_name != 'Unknown Resident':
            display_name = pc_name
        else:
            display_name = f'Resident — {pc.age}y, {pc.sex}'
        return {
            'name': display_name,
            'id_display': f'R-{report.id}',
            'onset_date': pc.date_of_onset or report.date_of_onset,
        }

    return {
        'name': f'Case #{report.id}',
        'id_display': str(report.id),
        'onset_date': report.date_of_onset,
    }


def _perform_case_confirmation(
    report,
    *,
    actor_id,
    lab_control_number='',
    test_type='',
    confirmed_disease='',
    actor_type='admin',
    request=None,
):
    """Confirm a probable/suspected report and run threshold evaluation."""
    now = timezone.now()
    update_fields = {
        'status': 'Confirmed',
        'case_classification': 'confirmed',
        'confirmed_at': now,
        'updated_at': now,
    }

    if confirmed_disease:
        update_fields['syndrome_type'] = confirmed_disease

    lab_notes = []
    if lab_control_number:
        lab_notes.append(f'Lab Control #: {lab_control_number}')
    if test_type:
        lab_notes.append(f'Test Type: {test_type}')
    if lab_notes:
        existing = (report.remarks or '').strip()
        lab_line = ' | '.join(lab_notes)
        update_fields['remarks'] = f'{existing} | {lab_line}'.strip(' |') if existing else lab_line

    SurveillanceReport.objects.filter(id=report.id).update(**update_fields)
    report.refresh_from_db()

    threshold_result = process_confirmation_threshold_check(
        report,
        actor_id=actor_id,
    )

    log_audit(
        actor_id=actor_id,
        actor_type=actor_type,
        action='case_confirmed',
        target_id=report.id,
        request=request,
    )
    return threshold_result


@role_required('admin', 'super_admin')
def admin_confirmation_panel(request):
    """Dedicated queue for admin lab confirmation of ML-classified probable cases."""
    search = request.GET.get('search', '').strip()

    q = Q(
        validation_status='validated',
        status__in=('Probable', 'Suspected'),
    )
    if search:
        search_q = (
            Q(barangay__barangay_name__icontains=search) |
            Q(patient__full_name__icontains=search) |
            Q(patient_name__icontains=search) |
            Q(syndrome_type__icontains=search) |
            Q(suspected_disease__icontains=search)
        )
        if search.isdigit():
            search_q |= Q(id=int(search)) | Q(patient_id=int(search))
        q &= search_q

    reports = (
        SurveillanceReport.objects.filter(q)
        .select_related('barangay', 'patient')
        .prefetch_related('patient_case')
        .annotate(barangay_name=F('barangay__barangay_name'))
        .order_by('-report_date')[:200]
    )

    pending_cases = []
    for report in reports:
        patient = _patient_display_for_report(report)
        pending_cases.append({
            'report': report,
            'patient_name': patient['name'],
            'patient_id_display': patient['id_display'],
            'onset_date': patient.get('onset_date'),
            'ml_disease': report.syndrome_type or report.suspected_disease or '—',
        })

    return render(request, 'reports/confirmation_panel.html', {
        'pending_cases': pending_cases,
        'search': search,
        'queue_count': len(pending_cases),
        'syndrome_types': SYNDROME_TYPES,
    })


@require_POST
@role_required('admin', 'super_admin', 'health_officer')
def confirm_case(request, report_id):
    report = SurveillanceReport.objects.filter(id=report_id)
    report = barangay_queryset_filter(request, report).first()
    if not report:
        messages.error(request, 'Report not found.')
        return redirect(_confirm_redirect_target(request))

    if report.status not in ('Suspected', 'Probable'):
        messages.error(request, f'Only suspected or probable cases can be confirmed (current status: {report.status}).')
        return redirect(_confirm_redirect_target(request))

    lab_control_number = request.POST.get('lab_control_number', '').strip()
    test_type = request.POST.get('test_type', '').strip()
    confirmed_disease = request.POST.get('confirmed_disease', '').strip()

    threshold_result = _perform_case_confirmation(
        report,
        actor_id=request.session.get('user_id'),
        lab_control_number=lab_control_number,
        test_type=test_type,
        confirmed_disease=confirmed_disease,
        actor_type=request.session.get('user_type', 'admin'),
        request=request,
    )

    status_msg = threshold_result.get('status', 'NORMAL')
    if status_msg in ('PROBABLE_OUTBREAK', 'OUTBREAK_CONFIRMED'):
        messages.warning(
            request,
            f'Case #{report_id} confirmed. Threshold evaluation: {status_msg} '
            f'({threshold_result.get("confirmed_count")} confirmed '
            f'{threshold_result.get("disease_label")} in '
            f'{threshold_result.get("time_window_days")} days). '
            f'System alert escalated.',
        )
    else:
        messages.success(request, f'Case #{report_id} confirmed by CHO.')
    return redirect(_confirm_redirect_target(request))


def _confirm_redirect_target(request):
    target = request.POST.get('redirect_to', '').strip()
    if target == 'admin_confirmation_panel':
        return 'admin_confirmation_panel'
    return 'case_records'


@require_POST
@role_required('admin', 'super_admin', 'surveillance_officer')
def validate_report(request, report_id):
    """Legacy manual validation — superseded by live ML auto-validation on submit."""
    messages.info(
        request,
        'Reports are now auto-validated by the ML pipeline on submission. '
        'Use Confirm to upgrade Probable cases after laboratory verification.',
    )
    return redirect('case_records')


# Outbreak thresholds — confirmed cases within 30 days triggers escalation
OUTBREAK_THRESHOLDS = {
    'Dengue':                              3,
    'Hand, Foot and Mouth Disease (HFMD)': 5,
}
DEFAULT_THRESHOLD = 5


def _update_barangay_risk(barangay_id):
    """Recalculate and update barangay risk_status based on confirmed case counts."""
    cutoff = timezone.now() - timedelta(days=30)
    rows = SurveillanceReport.objects.filter(
        barangay_id=barangay_id,
        validation_status='validated',
        case_classification='confirmed',
        report_date__gte=cutoff
    ).values('syndrome_type').annotate(total=Sum('case_count'))

    max_ratio = 0.0
    for r in rows:
        threshold = OUTBREAK_THRESHOLDS.get(r['syndrome_type'], DEFAULT_THRESHOLD)
        ratio = r['total'] / threshold
        if ratio > max_ratio:
            max_ratio = ratio

    # Also count all validated cases (any classification) for general risk
    total_val = SurveillanceReport.objects.filter(
        barangay_id=barangay_id,
        validation_status='validated',
        report_date__gte=cutoff
    ).aggregate(total=Sum('case_count'))
    
    total_cases = total_val['total'] or 0

    if max_ratio >= 3.0 or total_cases >= 30:
        risk = 'critical'
    elif max_ratio >= 2.0 or total_cases >= 20:
        risk = 'high'
    elif max_ratio >= 1.0 or total_cases >= 10:
        risk = 'moderate'
    else:
        risk = 'low'

    # Legacy barangays table has no risk_status column — risk level is computed only


# ── Incident Reports (Admin) ──────────────────────────────────────

@role_required('admin', 'super_admin', 'surveillance_officer')
def incident_reports(request):
    """Generate structured health incident reports from validated data."""
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')
    syndrome  = request.GET.get('syndrome', '')
    barangay  = request.GET.get('barangay', '')

    q = Q(validation_status='validated')

    if date_from:
        q &= Q(report_date__date__gte=date_from)
    if date_to:
        q &= Q(report_date__date__lte=date_to)
    if syndrome:
        q &= Q(syndrome_type=syndrome)
    if barangay:
        q &= Q(barangay_id=barangay)

    reports = SurveillanceReport.objects.filter(q).select_related('barangay', 'submitted_by').annotate(
        barangay_name=F('barangay__barangay_name'),
        risk_status=Value('low', output_field=CharField()),
        reporter=Concat(
            F('submitted_by__first_name'),
            Value(' '),
            F('submitted_by__last_name'),
            output_field=CharField()
        )
    ).order_by('-report_date')

    # Summary stats
    total_cases = sum(r.case_count for r in reports)
    by_disease  = {}
    by_barangay = {}
    by_classif  = {'suspected': 0, 'probable': 0, 'confirmed': 0}

    for r in reports:
        by_disease[r.syndrome_type]  = by_disease.get(r.syndrome_type, 0) + r.case_count
        by_barangay[r.barangay_name] = by_barangay.get(r.barangay_name, 0) + r.case_count
        by_classif[r.case_classification] = by_classif.get(r.case_classification, 0) + r.case_count

    barangays = Barangay.objects.all().order_by('barangay_name')

    return render(request, 'reports/incident_reports.html', {
        'reports': reports,
        'total_cases': total_cases,
        'by_disease':  sorted(by_disease.items(),  key=lambda x: -x[1]),
        'by_barangay': sorted(by_barangay.items(), key=lambda x: -x[1]),
        'by_classif':  by_classif,
        'barangays':   barangays,
        'syndrome_types': SYNDROME_TYPES,
        'date_from': date_from, 'date_to': date_to,
        'syndrome': syndrome, 'barangay': barangay,
    })


# ── AJAX: real-time data feed for dashboard widgets ───────────────

@require_GET
@login_required
def api_recent_reports(request):
    """Returns last 10 validated reports as JSON for dashboard widgets."""
    rows = SurveillanceReport.objects.filter(validation_status='validated')
    rows = barangay_queryset_filter(request, rows)
    rows = rows.select_related('barangay').annotate(
        barangay_name=F('barangay__barangay_name')
    ).order_by('-report_date')[:10]

    reports_data = []
    for r in rows:
        reports_data.append({
            'syndrome_type': r.syndrome_type,
            'case_count': r.case_count,
            'case_classification': r.case_classification,
            'report_date': r.report_date.strftime('%Y-%m-%d %H:%M:%S') if r.report_date else '',
            'barangay_name': r.barangay_name or '',
        })
    return JsonResponse({'reports': reports_data})


# ── APTAS choropleth feed for geospatial map ──────────────────────

@require_GET
@login_required
def get_barangay_risk_map_data(request):
    """Return latest ``BarangayRiskLog`` score per barangay for Leaflet boundaries."""
    from reports.aptas_service import get_barangay_risk_map_matrix

    matrix = get_barangay_risk_map_matrix()
    scoped_barangay = get_request_barangay(request)

    if scoped_barangay:
        scoped_name = scoped_barangay.barangay_name
        matrix = {
            name: payload
            for name, payload in matrix.items()
            if name.casefold() == scoped_name.casefold()
        }
    elif not is_city_wide_role(request.session.get('role', '')):
        matrix = {}

    return JsonResponse(matrix)
