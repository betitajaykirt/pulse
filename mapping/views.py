from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.db.models import OuterRef, Subquery, Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from accounts.auth_utils import login_required
from myapp.models import (
    Barangay, User, SurveillanceReport, PatientCase,
    SYMPTOM_CATEGORY_CHOICES, SYMPTOM_CATEGORY_CODES, BarangayEpidemicStatus,
)
from myapp.barangay_scope import (
    is_city_wide_role, get_request_barangay, resolve_user_barangay,
    is_barangay_scoped_role,
)
from myapp.mitigation_utils import mitigation_suggestions_for_report


THRESHOLD_RISK_MAP = {
    'OUTBREAK_CONFIRMED': 'critical',
    'PROBABLE_OUTBREAK': 'high',
    'ISOLATED_CASE': 'moderate',
    'NORMAL': 'low',
}


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
    )

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

    if case_classif:
        base_qs = base_qs.filter(case_classification=case_classif)

    rows = base_qs.select_related('barangay').order_by('-report_date')

    cases = []
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
        cases.append({
            'id':                  r.id,
            'latitude':            float(r.latitude),
            'longitude':           float(r.longitude),
            'syndrome_type':       r.syndrome_type,
            'status':              r.status,
            'case_count':          r.case_count,
            'case_classification': r.case_classification,
            'validation_status':   r.validation_status,
            'report_date':         r.report_date.strftime('%Y-%m-%d') if r.report_date else '',
            'barangay_name':       r.barangay.barangay_name if r.barangay else 'Unknown',
            'heat_intensity':      heat_intensity,
            'epidemic_threshold_status': r.epidemic_threshold_status or '',
            'mitigation_suggestions': mitigation,
        })

    return JsonResponse({'ok': True, 'cases': cases})
