from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.db.models import OuterRef, Subquery, Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from accounts.auth_utils import login_required
from myapp.models import (
    Barangay, User, SurveillanceReport, PatientCase, RiskAssessment,
    SYMPTOM_CATEGORY_CHOICES, SYMPTOM_CATEGORY_CODES, BarangayEpidemicStatus,
)
from myapp.barangay_scope import (
    is_city_wide_role, get_request_barangay, resolve_user_barangay,
    is_barangay_scoped_role,
)
from myapp.mitigation_utils import mitigation_suggestions_for_report
from reports.ml_display import (
    ml_top_prediction_for_report,
    parse_ml_confidence,
    predicted_disease_display,
)
from reports.aptas_service import compute_aptas_breakdown, normalize_anomaly_score


THRESHOLD_RISK_MAP = {
    'OUTBREAK_CONFIRMED': 'critical',
    'PROBABLE_OUTBREAK': 'high',
    'ISOLATED_CASE': 'moderate',
    'NORMAL': 'low',
}

_INCONCLUSIVE_DISEASE_LABELS = frozenset({
    'inconclusive syndromic pattern',
    'insufficient data for prediction',
    'undetermined',
    '',
})


def _is_inconclusive_disease_label(label):
    return (label or '').strip().lower() in _INCONCLUSIVE_DISEASE_LABELS


def _ml_predicted_disease(report):
    for candidate in (report.suspected_disease, report.syndrome_type):
        if candidate and not _is_inconclusive_disease_label(candidate):
            return candidate.strip()
    return ''


def _confirmed_disease_name(report):
    for candidate in (report.syndrome_type, report.suspected_disease):
        if candidate and not _is_inconclusive_disease_label(candidate):
            return candidate.strip()
    return ''


def _ml_confidence_high(report, ml_predicted):
    if not ml_predicted:
        return False
    if (report.case_classification or '').lower() == 'probable':
        return True
    if report.suspected_disease and not _is_inconclusive_disease_label(report.suspected_disease):
        return True
    return False


def _canonical_disease_for_actions(report, status_norm, ml_predicted, confirmed_name):
    if status_norm == 'Confirmed' and confirmed_name:
        return confirmed_name
    if ml_predicted:
        return ml_predicted
    for candidate in (report.suspected_disease, report.syndrome_type):
        if candidate and not _is_inconclusive_disease_label(candidate):
            return candidate.strip()
    return 'the reported illness'


def _barangay_epidemic_summary(barangay_ids):
    """Return worst epidemic threshold status per barangay for map indicators."""
    summary = {}
    if not barangay_ids:
        return summary

    severity = {
        'OUTBREAK_CONFIRMED': 4,
        'PROBABLE_OUTBREAK': 3,
        'ISOLATED_CASE': 2,
        'NORMAL': 1,
    }

    rows = BarangayEpidemicStatus.objects.filter(
        barangay_id__in=barangay_ids,
    ).values('barangay_id', 'threshold_status', 'disease_label', 'confirmed_count')

    for row in rows:
        bid = row['barangay_id']
        current = summary.get(bid)
        score = severity.get(row['threshold_status'], 0)
        if not current or score > current['score']:
            summary[bid] = {
                'score': score,
                'threshold_status': row['threshold_status'],
                'disease_label': row['disease_label'],
                'confirmed_count': row['confirmed_count'],
            }
    return summary


@login_required
def map_view(request):
    try:
        role = request.session.get('role', '')
        scoped_barangay = get_request_barangay(request)

        if is_barangay_scoped_role(role) and scoped_barangay:
            requested = request.GET.get('barangay', '').strip()
            if requested.casefold() != scoped_barangay.barangay_name.casefold():
                params = request.GET.copy()
                params['barangay'] = scoped_barangay.barangay_name
                return redirect(reverse('map_view') + '?' + params.urlencode())

        if is_city_wide_role(role):
            barangays = Barangay.objects.all().order_by('barangay_name')
            user_barangay = ''
        elif scoped_barangay:
            barangays = Barangay.objects.filter(id=scoped_barangay.id)
            user_barangay = scoped_barangay.barangay_name
        else:
            barangays = Barangay.objects.none()
            user_barangay = request.session.get('barangay_text', '')

        return render(request, 'mapping/map.html', {
            'user_role':     role,
            'user_barangay': user_barangay,
            'barangays':     barangays,
            'city_wide':     is_city_wide_role(role),
            'barangay_scoped': is_barangay_scoped_role(role),
            'symptom_category_choices': SYMPTOM_CATEGORY_CHOICES,
            'disease_category_choices': DISEASE_CATEGORY_CHOICES,
        })
    except Exception as e:
        return HttpResponse(f'<h1>Map Error</h1><pre>{e}</pre>', status=500)


@require_GET
@login_required
def api_barangay_data(request):
    time_range  = request.GET.get('time_range', '30')
    risk_filter = request.GET.get('risk', '')
    try:
        days = int(time_range)
    except ValueError:
        days = 30

    cutoff = timezone.now() - timedelta(days=days)
    scoped_barangay = get_request_barangay(request)

    top_syndrome_qs = SurveillanceReport.objects.filter(
        barangay_id=OuterRef('id'),
        validation_status='validated',
        report_date__gte=cutoff
    ).values('syndrome_type').annotate(
        total_cases=Sum('case_count')
    ).order_by('-total_cases')

    top_syndrome_subquery = Subquery(top_syndrome_qs.values('syndrome_type')[:1])

    barangays_qs = Barangay.objects.annotate(
        report_count=Count(
            'surveillancereport',
            filter=Q(
                surveillancereport__validation_status='validated',
                surveillancereport__report_date__gte=cutoff
            )
        ),
        total_cases_sum=Sum(
            'surveillancereport__case_count',
            filter=Q(
                surveillancereport__validation_status='validated',
                surveillancereport__report_date__gte=cutoff
            )
        ),
        top_syndrome=top_syndrome_subquery
    )

    if scoped_barangay:
        barangays_qs = barangays_qs.filter(id=scoped_barangay.id)
    elif not is_city_wide_role(request.session.get('role', '')):
        barangays_qs = barangays_qs.none()

    if risk_filter:
        pass  # legacy barangays table has no risk_status column

    rows = barangays_qs.order_by('-total_cases_sum')
    epidemic_by_barangay = _barangay_epidemic_summary([r.id for r in rows])

    features = []
    for r in rows:
        if r.latitude and r.longitude:
            lat, lon = float(r.latitude), float(r.longitude)
            epidemic = epidemic_by_barangay.get(r.id, {})
            threshold_status = epidemic.get('threshold_status', '')
            map_risk = THRESHOLD_RISK_MAP.get(threshold_status, r.risk_status)
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [lon, lat]
                },
                'properties': {
                    'id':           r.id,
                    'name':         r.barangay_name,
                    'risk_status':  map_risk,
                    'report_count': r.report_count,
                    'total_cases':  int(r.total_cases_sum or 0),
                    'top_syndrome': r.top_syndrome or 'N/A',
                    'epidemic_threshold_status': threshold_status,
                    'epidemic_disease': epidemic.get('disease_label', ''),
                    'epidemic_confirmed_count': epidemic.get('confirmed_count', 0),
                }
            })

    return JsonResponse({'type': 'FeatureCollection', 'features': features})


@require_GET
@login_required
def api_cases(request):
    time_range = request.GET.get('time_range', '30')
    symptom_category = request.GET.get('symptom_category', '').strip()
    disease_category = request.GET.get('disease_category', '').strip()
    barangay_name = request.GET.get('barangay', '').strip()
    case_classif = request.GET.get('case_classification', '').strip()

    try:
        days = int(time_range)
    except ValueError:
        days = 30

    role = request.session.get('role')
    cutoff = timezone.now() - timedelta(days=days)
    scoped_barangay = get_request_barangay(request)

    base_qs = SurveillanceReport.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        report_date__gte=cutoff,
    ).exclude(status__in=['Closed', 'Discarded'])

    if scoped_barangay:
        base_qs = base_qs.filter(barangay_id=scoped_barangay.id)
    elif is_city_wide_role(role):
        if barangay_name:
            base_qs = base_qs.filter(barangay__barangay_name=barangay_name)
    else:
        base_qs = base_qs.none()

    if symptom_category:
        if symptom_category not in SYMPTOM_CATEGORY_CODES:
            return JsonResponse({'ok': False, 'error': 'Invalid syndrome category filter.'}, status=400)
        filter_barangay_id = scoped_barangay.id if scoped_barangay else None
        if barangay_name and not scoped_barangay:
            filter_barangay_id = (
                Barangay.objects.filter(barangay_name=barangay_name)
                .values_list('id', flat=True).first()
            )
        report_ids = PatientCase.surveillance_report_ids_for_category(
            symptom_category,
            barangay_id=filter_barangay_id,
        )
        base_qs = base_qs.filter(id__in=report_ids)

    if disease_category:
        if disease_category not in VALID_DISEASE_CATEGORIES:
            return JsonResponse({'ok': False, 'error': 'Invalid disease category filter.'}, status=400)
        base_qs = filter_surveillance_reports_by_disease_category(base_qs, disease_category)

    if case_classif:
        base_qs = base_qs.filter(case_classification=case_classif)

    rows = list(
        base_qs.select_related('barangay', 'submitted_by', 'validated_by').order_by('-report_date')
    )
    report_ids = [r.id for r in rows]
    latest_assessments = {}
    if report_ids:
        for ra in RiskAssessment.objects.filter(report_id__in=report_ids).order_by('report_id', '-created_at'):
            if ra.report_id not in latest_assessments:
                latest_assessments[ra.report_id] = ra

    def _officer_name(user):
        if not user:
            return ''
        return f'{user.first_name} {user.last_name}'.strip()

    def _confirmed_by_name(admin):
        if not admin:
            return 'System Administrator'
        name = f'{admin.first_name} {admin.last_name}'.strip()
        return name or 'System Administrator'

    def _risk_display(assessment, report):
        score = None
        if assessment and assessment.anomaly_score is not None:
            score = float(assessment.anomaly_score)
            if score < 0:
                score = max(0.0, min(1.0, (0.5 - score)))
        elif assessment and assessment.risk_score is not None:
            score = float(assessment.risk_score)
            if score > 1.5:
                score = score / 100.0
        elif report.ml_anomaly_score is not None:
            raw = float(report.ml_anomaly_score)
            score = max(0.0, min(1.0, (0.5 - raw))) if raw <= 0.5 else min(1.0, raw)

        level = ''
        if assessment and assessment.risk_level:
            level = assessment.risk_level.title()
            if level.lower() == 'low':
                level = 'Moderate'
        else:
            classif = (report.case_classification or 'suspected').lower()
            level = {'confirmed': 'Critical', 'probable': 'High', 'suspected': 'Moderate'}.get(classif, 'Moderate')

        if score is not None:
            return f'{score:.2f} — {level} Risk', score, level
        return f'{level} Risk', None, level

    def _aptas_breakdown_for_report(report, assessment, cache):
        barangay = report.barangay.barangay_name if report.barangay else ''
        syndrome = (
            ml_top_prediction_for_report(report)
            or report.syndrome_type
            or report.suspected_disease
            or 'Undetermined'
        ).strip()
        raw_anomaly = None
        if assessment and assessment.anomaly_score is not None:
            raw_anomaly = float(assessment.anomaly_score)
        elif report.ml_anomaly_score is not None:
            raw_anomaly = float(report.ml_anomaly_score)

        cache_key = (barangay.lower(), syndrome.lower(), report.id, round(raw_anomaly or 0.0, 4))
        if cache_key not in cache:
            try:
                cache[cache_key] = compute_aptas_breakdown(
                    barangay, syndrome, raw_anomaly, report=report,
                )
            except (ValueError, TypeError):
                anomaly = normalize_anomaly_score(raw_anomaly)
                cache[cache_key] = {
                    'anomaly_score': anomaly,
                    'temporal_score': 0.0,
                    'spatial_score': 0.0,
                    'environmental_score': 0.0,
                    'final_risk_score': 0.0,
                }
        breakdown = cache[cache_key]
        return {
            'final_score': round(float(breakdown['final_risk_score']) / 100.0, 4),
            'anomaly_score': round(float(breakdown['anomaly_score']), 4),
            'temporal_score': round(float(breakdown['temporal_score']), 4),
            'spatial_score': round(float(breakdown['spatial_score']), 4),
            'environmental_score': round(float(breakdown['environmental_score']), 4),
        }

    def _recommendations_text(mitigation, recommended_action, disease_name):
        disease_name = (disease_name or 'the reported illness').strip()
        intro = f'Initiate {disease_name} vector control protocols.'
        fallback = (
            f'{intro} Inspect standing water and conduct localized vector control within the 25m radius.'
        )
        if recommended_action:
            if disease_name.lower() in recommended_action.lower():
                return recommended_action
            return f'{intro} {recommended_action}'
        if mitigation and mitigation.get('steps'):
            parts = [s.get('action_text', '') for s in mitigation['steps'] if s.get('action_text')]
            if parts:
                base = ' '.join(parts[:3])
                if disease_name.lower() in base.lower():
                    return base
                return f'{intro} {base}'
        return fallback

    cases = []
    aptas_cache = {}
    for r in rows:
        weight_map = {
            'confirmed': 1.0,
            'probable': 0.6,
            'suspected': 0.3,
            'unassigned': 0.25,
        }
        weight = weight_map.get(r.case_classification, 0.25)
        heat_intensity = min(1.0, weight * (r.case_count / 3))
        mitigation = mitigation_suggestions_for_report(r)
        assessment = latest_assessments.get(r.id)
        risk_line, risk_score, risk_level = _risk_display(assessment, r)
        officer = r.submitted_by
        contact = ''
        if officer:
            contact = officer.contact_number or officer.email or ''
        status_norm = (r.status or '').strip()
        classif_norm = (r.case_classification or '').strip().lower()
        confirmed_by = _confirmed_by_name(r.validated_by)
        is_confirmed = (
            status_norm == 'Confirmed'
            or classif_norm == 'confirmed'
            or bool(r.validated_by)
        )
        confirmed_date = (
            r.confirmed_at.strftime('%Y-%m-%d') if r.confirmed_at else ''
        )
        onset = r.date_of_onset.strftime('%Y-%m-%d') if r.date_of_onset else ''
        ml_predicted = ml_top_prediction_for_report(r) or _ml_predicted_disease(r)
        ml_confidence = parse_ml_confidence(r.remarks or '')
        ml_display = predicted_disease_display(r)
        confirmed_disease = _confirmed_disease_name(r) if status_norm == 'Confirmed' else ''
        ml_high = _ml_confidence_high(r, ml_predicted)
        action_disease = _canonical_disease_for_actions(
            r, status_norm, ml_predicted, confirmed_disease,
        )
        aptas_scores = _aptas_breakdown_for_report(r, assessment, aptas_cache)
        cases.append({
            'id':                  r.id,
            'patient_name':        (r.patient_name or '').strip() or 'Unknown Resident',
            'latitude':            float(r.latitude),
            'longitude':           float(r.longitude),
            'syndrome_type':       r.syndrome_type,
            'suspected_disease':   (r.suspected_disease or '').strip(),
            'confirmed_disease':   confirmed_disease,
            'ml_predicted_disease': ml_predicted,
            'ml_top_predicted_disease': ml_top_prediction_for_report(r) or ml_predicted,
            'ml_classification_confidence': ml_confidence,
            'ml_confidence_pct':   ml_display.get('confidence_pct'),
            'ml_confidence_high':  ml_high,
            'status':              r.status,
            'case_count':          r.case_count,
            'case_classification': r.case_classification,
            'validation_status':   r.validation_status,
            'report_date':         r.report_date.strftime('%Y-%m-%d') if r.report_date else '',
            'date_of_onset':       onset,
            'barangay_name':       r.barangay.barangay_name if r.barangay else 'Unknown',
            'heat_intensity':      heat_intensity,
            'epidemic_threshold_status': r.epidemic_threshold_status or '',
            'mitigation_suggestions': mitigation,
            'officer_name':        _officer_name(officer),
            'officer_contact':     contact,
            'risk_score_line':     risk_line,
            'risk_score':          risk_score,
            'risk_level':          risk_level,
            'final_score':         aptas_scores['final_score'],
            'anomaly_score':       aptas_scores['anomaly_score'],
            'temporal_score':      aptas_scores['temporal_score'],
            'spatial_score':       aptas_scores['spatial_score'],
            'environmental_score': aptas_scores['environmental_score'],
            'recommendations':     _recommendations_text(
                mitigation,
                assessment.recommended_action if assessment else None,
                action_disease,
            ),
            'confirmed_by':          confirmed_by,
            'confirmed_date':      confirmed_date,
            'is_confirmed':        is_confirmed,
        })

    return JsonResponse({'ok': True, 'cases': cases})
