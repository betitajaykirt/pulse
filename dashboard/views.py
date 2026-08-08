from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.urls import reverse
from urllib.parse import urlencode
from accounts.auth_utils import login_required
from myapp.audit_utils import display_name_for_audit_log, display_name_for_system_log
from myapp.models import (
    User, Admin, SuperAdmin, Barangay, SurveillanceReport,
    Alert, SystemLog, AuditLog, NotificationLog, FieldTask, EnvironmentalData
)
from accounts.auth_utils import role_required
from myapp.barangay_scope import (
    is_city_wide_role, resolve_user_barangay, BARANGAY_SCOPED_ROLES,
)
from .analytics_service import (
    SYNDROME_CATEGORY_OPTIONS, get_analytics_payload, get_barangay_options,
)
from reports.weather_service import fetch_bago_city_weather
from reports.aptas_service import get_aptas_dashboard_context, resolve_aptas_barangay_filter
import json
from django.db.models import Count, Avg, Sum
from django.db.models.functions import TruncDate
from datetime import timedelta
from django.utils import timezone


@login_required
def dashboard(request):
    role = request.session.get('role')
    template_map = {
        'super_admin':            'dashboard/super_admin.html',
        'admin':                  'dashboard/admin.html',
        'encoder':                'dashboard/encoder.html',
        'health_officer':         'dashboard/health_officer.html',
        'surveillance_officer':   'dashboard/surveillance_officer.html',
        'barangay_health_worker': 'dashboard/barangay_health_worker.html',
    }
    if role == 'catchment_nurse':
        return redirect('nurse_dashboard')

    template = template_map.get(role)
    if not template:
        return redirect('login')

    ctx = _get_stats(role, request.session.get('user_id'))
    ctx['weather'] = fetch_bago_city_weather()
    barangay_filter = resolve_aptas_barangay_filter(
        role, request.session.get('user_id'), ctx,
    )
    ctx.update(get_aptas_dashboard_context(barangay_name=barangay_filter))
    if barangay_filter:
        ctx['aptas_barangay_scope'] = barangay_filter

    return render(request, template, ctx)


def _local_barangay_stats(user):
    """Aggregate surveillance metrics scoped to one barangay."""
    barangay = resolve_user_barangay(user)
    if not barangay:
        return {
            'barangay_name': user.barangay_text or 'Unassigned',
            'total_reports': 0,
            'my_reports_count': 0,
            'pending_reports': 0,
            'suspected_count': 0,
            'confirmed_count': 0,
            'active_alerts': 0,
            'recent_reports': [],
        }

    base_qs = SurveillanceReport.objects.filter(barangay_id=barangay.id).exclude(status='Closed')
    return {
        'barangay_name': barangay.barangay_name,
        'total_reports': base_qs.count(),
        'my_reports_count': base_qs.filter(submitted_by_id=user.id).count(),
        'pending_reports': base_qs.filter(validation_status='pending').count(),
        'suspected_count': base_qs.filter(status='Suspected').count(),
        'confirmed_count': base_qs.filter(status='Confirmed').count(),
        'active_alerts': base_qs.filter(status='Suspected').count(),
        'recent_reports': base_qs.order_by('-report_date')[:5],
    }


def _get_stats(role, user_id=None):
    ctx = {}
    if role in ('admin', 'super_admin'):
        ctx['total_users']     = User.objects.count()
        ctx['total_barangays'] = Barangay.objects.count()

        # Surveillance & Epidemiological KPIs
        active_qs = SurveillanceReport.objects.exclude(status='Closed')
        ctx['active_cases_total'] = active_qs.count()
        ctx['active_cases_dengue'] = active_qs.filter(syndrome_type__icontains='dengue').count()
        ctx['active_cases_lepto'] = active_qs.filter(syndrome_type__icontains='lepto').count()
        ctx['total_confirmed'] = SurveillanceReport.objects.filter(status='Confirmed').count()
        ctx['pending_reports'] = active_qs.filter(validation_status='pending').count()
        
    if role == 'super_admin':
        ctx['total_admins']  = Admin.objects.count()
        ctx['total_reports'] = SurveillanceReport.objects.exclude(status='Closed').count()
    if role in ('health_officer', 'surveillance_officer'):
        ctx['active_alerts'] = Alert.objects.filter(status='active').count()
        ctx['pending_reports'] = SurveillanceReport.objects.filter(validation_status='pending').exclude(status='Closed').count()
        ctx['suspected_count'] = SurveillanceReport.objects.filter(status='Suspected').count()
        ctx['confirmed_count'] = SurveillanceReport.objects.filter(status='Confirmed').count()
    if role in BARANGAY_SCOPED_ROLES and user_id:
        user = User.objects.filter(id=user_id).first()
        if user:
            ctx.update(_local_barangay_stats(user))
    return ctx


@role_required('admin', 'super_admin')
def system_logs_view(request):
    system_logs = list(SystemLog.objects.order_by('-created_at')[:100])
    audit_logs = list(AuditLog.objects.order_by('-created_at')[:100])
    for log in system_logs:
        log.display_user = display_name_for_system_log(log)
    for log in audit_logs:
        log.display_actor = display_name_for_audit_log(log)
    return render(request, 'dashboard/system_logs.html', {
        'system_logs': system_logs,
        'audit_logs': audit_logs,
    })


@login_required
def alerts_inbox_view(request):
    role = request.session.get('role')
    if is_city_wide_role(role):
        alerts = Alert.objects.filter(status='active').order_by('-alert_date')[:50]
        alert_history = Alert.objects.filter(status='resolved').order_by('-alert_date')[:50]
        notifications = NotificationLog.objects.select_related('alert').order_by('-sent_at')[:50]
    elif role in BARANGAY_SCOPED_ROLES:
        user = User.objects.filter(id=request.session.get('user_id')).first()
        barangay = resolve_user_barangay(user)
        if barangay:
            notifications = NotificationLog.objects.select_related('alert').filter(
                recipient_role=role,
                message_summary__icontains=barangay.barangay_name,
            ).order_by('-sent_at')[:50]
            alert_ids = {n.alert_id for n in notifications}
            alerts = Alert.objects.filter(id__in=alert_ids, status='active').order_by('-alert_date')[:50]
            alert_history = Alert.objects.filter(id__in=alert_ids, status='resolved').order_by('-alert_date')[:50]
        else:
            alerts = Alert.objects.none()
            alert_history = Alert.objects.none()
            notifications = NotificationLog.objects.none()
    else:
        alerts = Alert.objects.none()
        alert_history = Alert.objects.none()
        notifications = NotificationLog.objects.none()

    ctx = {
        'alerts': alerts,
        'alert_history': alert_history,
        'notifications': notifications,
    }

    barangay_filter = resolve_aptas_barangay_filter(
        role, request.session.get('user_id'), ctx,
    )
    ctx.update(get_aptas_dashboard_context(barangay_name=barangay_filter))
    if barangay_filter:
        ctx['aptas_barangay_scope'] = barangay_filter

    return render(request, 'dashboard/alerts_inbox.html', ctx)


@role_required('surveillance_officer', 'admin', 'super_admin', 'health_officer')
def analytics_view(request):
    barangays = get_barangay_options()
    return render(request, 'dashboard/analytics.html', {
        'symptom_category_choices': SYNDROME_CATEGORY_OPTIONS,
        'barangays': barangays,
    })


@require_GET
@role_required('surveillance_officer', 'admin', 'super_admin', 'health_officer')
def api_analytics_data(request):
    symptom_category = request.GET.get('symptom_category', '').strip()
    barangay_id = request.GET.get('barangay', '').strip()
    time_range = request.GET.get('time_range', 'current_year').strip()

    if time_range not in ('current_year', 'last_3_months', 'last_6_months'):
        time_range = 'current_year'

    valid_categories = {value for value, _ in SYNDROME_CATEGORY_OPTIONS if value}
    if symptom_category and symptom_category not in valid_categories:
        return JsonResponse({'ok': False, 'error': 'Invalid syndrome category filter.'}, status=400)

    payload = get_analytics_payload(
        symptom_category=symptom_category,
        barangay_id=barangay_id,
        time_range=time_range,
    )
    return JsonResponse({'ok': True, **payload})


@require_GET
@login_required
def api_alerts_aptas(request):
    """Merged APTAS ML + PIDSR threshold alerts feed."""
    role = request.session.get('role')
    barangay_filter = resolve_aptas_barangay_filter(
        role, request.session.get('user_id'), {},
    )
    ctx = get_aptas_dashboard_context(barangay_name=barangay_filter)
    alerts = []
    for card in ctx['aptas_alerts']:
        alerts.append({
            'source': card.get('alert_source'),
            'is_pidsr_threshold': card.get('is_pidsr_threshold', False),
            'risk_level': card.get('risk_level'),
            'barangay': card.get('barangay'),
            'syndrome': card.get('syndrome'),
            'final_risk_score': card.get('final_risk_score'),
            'anomaly_score': card.get('anomaly_score'),
            'temporal_score': card.get('temporal_score'),
            'spatial_score': card.get('spatial_score'),
            'environmental_score': card.get('environmental_score'),
            'threshold_status': card.get('threshold_status'),
            'threshold_headline': card.get('threshold_headline'),
            'threshold_summary': card.get('threshold_summary'),
            'confirmed_count': card.get('confirmed_count'),
            'time_window_days': card.get('time_window_days'),
            'map_url': card.get('map_url'),
            'is_active_alert': card.get('is_active_alert', False),
            'created_at': card.get('created_at').isoformat() if card.get('created_at') else None,
        })
    return JsonResponse({
        'ok': True,
        'alerts': alerts,
        'counts': ctx['aptas_risk_counts'],
        'active_count': ctx['aptas_alert_count'],
    })


@role_required('admin', 'super_admin')
def outbreak_thresholds_view(request):
    from myapp.models import OutbreakThreshold
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete':
            threshold_id = request.POST.get('threshold_id')
            if threshold_id:
                OutbreakThreshold.objects.filter(id=threshold_id).delete()
        elif action == 'save':
            threshold_id = request.POST.get('threshold_id')
            disease_label = request.POST.get('disease_label', '').strip()
            case_threshold = request.POST.get('case_threshold', 3)
            rolling_window_days = request.POST.get('rolling_window_days', 7)
            is_active = request.POST.get('is_active') == 'on'
            
            if disease_label:
                if threshold_id:
                    OutbreakThreshold.objects.filter(id=threshold_id).update(
                        disease_label=disease_label,
                        case_threshold=case_threshold,
                        rolling_window_days=rolling_window_days,
                        is_active=is_active
                    )
                else:
                    OutbreakThreshold.objects.create(
                        disease_label=disease_label,
                        case_threshold=case_threshold,
                        rolling_window_days=rolling_window_days,
                        is_active=is_active
                    )
        return redirect('outbreak_thresholds')

    thresholds = OutbreakThreshold.objects.all().order_by('disease_label')
    return render(request, 'dashboard/outbreak_thresholds.html', {
        'thresholds': thresholds,
    })


@login_required
@require_GET
def api_notifications(request):
    from dashboard.models import AppNotification, AppNotificationRead
    from myapp.models import RiskAssessment

    role = request.session.get('role')
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type', role)

    if is_city_wide_role(role):
        notifications = AppNotification.objects.order_by('-created_at')[:20]
    elif role in BARANGAY_SCOPED_ROLES:
        user = User.objects.filter(id=user_id).first()
        barangay = resolve_user_barangay(user)
        if barangay:
            notifications = AppNotification.objects.filter(barangay_name__iexact=barangay.barangay_name).order_by('-created_at')[:20]
        else:
            notifications = AppNotification.objects.none()
    else:
        notifications = AppNotification.objects.none()

    notifications_list = list(notifications)
    notification_ids = [n.id for n in notifications_list]

    read_notification_ids = set(AppNotificationRead.objects.filter(
        notification_id__in=notification_ids,
        user_id=user_id,
        user_type=user_type
    ).values_list('notification_id', flat=True))

    def _notification_recommendations(notif, report=None):
        if report:
            assessment = RiskAssessment.objects.filter(report_id=report.id).order_by('-created_at').first()
            if assessment and assessment.recommended_action:
                return assessment.recommended_action
        disease = notif.disease or 'the case'
        sev = (notif.severity_level or '').lower()
        if 'critical' in sev:
            return (
                f'Initiate 25m vector inspection for {disease}, check and eliminate standing water, '
                'isolate probable cases, and notify the city health center immediately.'
            )
        if 'high' in sev:
            return (
                f'Conduct targeted 25m vector inspection, verify breeding sites, escalate to the '
                f'surveillance officer, and update the {disease} line list.'
            )
        return (
            f'Review syndromic indicators, document environmental risks, and schedule barangay '
            f'follow-up for {disease}.'
        )

    def _resolve_context_report(notif):
        qs = SurveillanceReport.objects.select_related('submitted_by', 'barangay').filter(
            barangay__barangay_name__iexact=notif.barangay_name,
        ).order_by('-report_date')
        if notif.disease:
            by_disease = qs.filter(syndrome_type__icontains=notif.disease.split()[0])
            report = by_disease.first()
            if report:
                return report
        return qs.first()

    def _serialize_notification(notif, is_read):
        report = _resolve_context_report(notif)
        officer_name = ''
        officer_contact = ''
        officer_email = ''
        case_status = 'Active'
        street_address = ''
        latitude = None
        longitude = None

        if report:
            case_status = report.status or report.case_classification or 'Active'
            street_address = (report.detailed_address or '').strip()
            if report.latitude is not None:
                latitude = float(report.latitude)
            if report.longitude is not None:
                longitude = float(report.longitude)
            if report.submitted_by_id:
                officer = report.submitted_by
                officer_name = f'{officer.first_name} {officer.last_name}'.strip()
                officer_contact = officer.contact_number or ''
                officer_email = officer.email or ''

        map_params = {'barangay': notif.barangay_name}
        if latitude is not None and longitude is not None:
            map_params['lat'] = latitude
            map_params['lng'] = longitude
        map_url = reverse('map_view') + '?' + urlencode(map_params)

        final_risk = float(notif.final_risk_score) if notif.final_risk_score is not None else None
        anomaly = float(notif.anomaly_score) if notif.anomaly_score is not None else None

        return {
            'id': notif.id,
            'disease': notif.disease,
            'barangay_name': notif.barangay_name,
            'purok': notif.purok or '',
            'severity_level': notif.severity_level,
            'spatial_metric': notif.spatial_metric,
            'temporal_metric': notif.temporal_metric,
            'created_at': notif.created_at.isoformat(),
            'is_read': is_read,
            'final_risk_score': final_risk,
            'anomaly_score': anomaly,
            'active_cases': notif.active_cases,
            'trigger_source': notif.trigger_source or '',
            'score_shift': float(notif.score_shift) if notif.score_shift is not None else None,
            'last_evaluated_at': notif.last_evaluated_at.isoformat() if notif.last_evaluated_at else None,
            'case_status': case_status,
            'street_address': street_address,
            'officer_name': officer_name,
            'officer_contact': officer_contact,
            'officer_email': officer_email,
            'recommendations': _notification_recommendations(notif, report),
            'latitude': latitude,
            'longitude': longitude,
            'map_url': map_url,
        }

    data = []
    unread_count = 0

    for notif in notifications_list:
        is_read = notif.id in read_notification_ids
        if not is_read:
            unread_count += 1
        data.append(_serialize_notification(notif, is_read))

    return JsonResponse({
        'ok': True, 
        'unread_count': unread_count, 
        'notifications': data
    })


@login_required
def api_notification_read(request, notif_id):
    from dashboard.models import AppNotification, AppNotificationRead
    
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type', request.session.get('role'))
    
    if request.method == 'POST':
        notification = AppNotification.objects.filter(id=notif_id).first()
        if notification:
            AppNotificationRead.objects.get_or_create(
                notification=notification,
                user_id=user_id,
                user_type=user_type
            )
            return JsonResponse({'ok': True})
    return JsonResponse({'ok': False}, status=400)


@login_required
def api_alert_acknowledge(request, alert_id):
    """Update an alert's status from 'active' to 'acknowledged'."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)
    alert = Alert.objects.filter(id=alert_id).first()
    if not alert:
        return JsonResponse({'ok': False, 'error': 'Alert not found'}, status=404)
    if alert.status == 'active':
        alert.status = 'acknowledged'
        alert.save(update_fields=['status'])
    return JsonResponse({'ok': True, 'new_status': alert.status})


@login_required
@role_required('catchment_nurse')
def nurse_dashboard_view(request):
    ctx = _get_stats('catchment_nurse', request.session.get('user_id'))
    ctx['weather'] = fetch_bago_city_weather()
    barangay_filter = resolve_aptas_barangay_filter(
        'catchment_nurse', request.session.get('user_id'), ctx,
    )
    ctx.update(get_aptas_dashboard_context(barangay_name=barangay_filter))
    if barangay_filter:
        ctx['aptas_barangay_scope'] = barangay_filter
    
    # Active BHW List
    user = User.objects.filter(id=request.session.get('user_id')).first()
    barangay = resolve_user_barangay(user)
    bhws = []
    if barangay:
        bhws = User.objects.filter(
            role='barangay_health_worker',
            barangay_text__iexact=barangay.barangay_name,
            status='active'
        )
    ctx['active_bhws'] = bhws
    
    # Pre-fetch recent reports with 'submitted_by'
    if barangay:
        base_qs = SurveillanceReport.objects.select_related('submitted_by').filter(
            barangay_id=barangay.id
        ).exclude(status='Closed')
        ctx['recent_reports'] = base_qs.order_by('-report_date')[:10]

    return render(request, 'dashboard/nurse_dashboard.html', ctx)


@login_required
@role_required('catchment_nurse')
def api_dispatch_task(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)
    
    bhw_id = request.POST.get('bhw_id')
    report_id = request.POST.get('report_id')
    title = request.POST.get('title')
    description = request.POST.get('description', '')
    
    if not bhw_id or not title:
        return JsonResponse({'ok': False, 'error': 'Missing required fields'}, status=400)
        
    bhw = User.objects.filter(id=bhw_id, role='barangay_health_worker').first()
    if not bhw:
        return JsonResponse({'ok': False, 'error': 'Invalid BHW'}, status=404)
        
    report = None
    if report_id:
        report = SurveillanceReport.objects.filter(id=report_id).first()
        
    nurse = User.objects.filter(id=request.session.get('user_id')).first()
    
    task = FieldTask.objects.create(
        assigned_to=bhw,
        assigned_by=nurse,
        report=report,
        title=title,
        description=description,
        status='Pending'
    )

    return JsonResponse({'ok': True, 'task_id': task.id})

@login_required
@role_required('catchment_nurse')
def manage_bhws_view(request):
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count, Q
    
    user = User.objects.filter(id=request.session.get('user_id')).first()
    barangay = resolve_user_barangay(user)
    
    if not barangay:
        return redirect('login')
        
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    yesterday = now - timedelta(days=1)
    
    # Base query for BHWs in the same barangay
    bhws = User.objects.filter(
        role='barangay_health_worker',
        barangay_text__iexact=barangay.barangay_name
    ).annotate(
        reports_filed=Count('submitted_reports')
    ).order_by('first_name', 'last_name')
    
    total_bhws = bhws.count()
    active_today = bhws.filter(last_login__gte=yesterday).count()
    
    # Reports submitted by these BHWs this month
    reports_this_month = SurveillanceReport.objects.filter(
        submitted_by__in=bhws,
        report_date__gte=start_of_month
    ).count()
    
    ctx = {
        'session_full_name': request.session.get('full_name'),
        'barangay_name': barangay.barangay_name,
        'bhws': bhws,
        'total_bhws': total_bhws,
        'active_today': active_today,
        'reports_this_month': reports_this_month,
        'now': now,
        'yesterday': yesterday,
    }
    
    return render(request, 'dashboard/nurse_manage_bhws.html', ctx)


@login_required
@role_required('catchment_nurse')
def bhw_reports_view(request):
    # Redirect to case_records but append a query parameter so we can filter.
    # Actually, the case_records view doesn't currently filter by submitter role.
    # To keep it simple, we'll just redirect to case records since it's already scoped 
    # to their barangay. We could pass a parameter, but for now case_records does the job.
    url = reverse('case_records')
    # If the user specifically wants BHW reports, we can just redirect to case_records
    # because in the catchment nurse view, most reports are from BHWs.
    return redirect(url)

@login_required
@role_required('admin', 'super_admin', 'health_officer', 'surveillance_officer')
def environmental_intelligence_view(request):
    weather = fetch_bago_city_weather()
    
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    # Chart data: Environmental Trends & APTAS Correlation
    env_qs = EnvironmentalData.objects.filter(
        recorded_at__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('recorded_at')
    ).values('date').annotate(
        avg_temp=Avg('temperature'),
        avg_rain=Sum('rainfall')
    ).order_by('date')
    
    surveillance_qs = SurveillanceReport.objects.filter(
        report_date__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('report_date')
    ).values('date').annotate(
        cases=Count('id')
    ).order_by('date')
    
    chart_labels = []
    chart_temp = []
    chart_rain = []
    chart_cases = []
    
    env_map = {item['date']: item for item in env_qs if item['date']}
    surveillance_map = {item['date']: item for item in surveillance_qs if item['date']}
    
    for i in range(30):
        d = (thirty_days_ago + timedelta(days=i)).date()
        chart_labels.append(d.strftime('%b %d'))
        e = env_map.get(d, {'avg_temp': 0, 'avg_rain': 0})
        s = surveillance_map.get(d, {'cases': 0})
        
        chart_temp.append(float(e.get('avg_temp') or 0))
        chart_rain.append(float(e.get('avg_rain') or 0))
        chart_cases.append(s.get('cases', 0))
        
    # Barangay Vector Risk Table
    seven_days_ago = now - timedelta(days=7)
    recent_rain = EnvironmentalData.objects.filter(
        recorded_at__gte=seven_days_ago
    ).values('barangay_id').annotate(
        total_rain=Sum('rainfall')
    )
    rain_map = {r['barangay_id']: r['total_rain'] for r in recent_rain if r['barangay_id']}
    
    active_cases_by_brgy = SurveillanceReport.objects.exclude(status='Closed').values('barangay_id').annotate(
        cases=Count('id')
    )
    cases_map = {c['barangay_id']: c['cases'] for c in active_cases_by_brgy if c['barangay_id']}
    
    barangays = Barangay.objects.all()
    vector_risk_data = []
    
    for b in barangays:
        cases = cases_map.get(b.id, 0)
        rain = float(rain_map.get(b.id, 0) or 0)
        risk_index = (cases * 15.0) + (rain * 0.5)
        
        level = 'Low'
        if risk_index >= 75:
            level = 'Critical'
        elif risk_index >= 50:
            level = 'High'
        elif risk_index >= 25:
            level = 'Moderate'
            
        vector_risk_data.append({
            'barangay': b.barangay_name,
            'active_cases': cases,
            'recent_rain_mm': round(rain, 2),
            'risk_index': round(risk_index, 1),
            'risk_level': level
        })
        
    vector_risk_data.sort(key=lambda x: x['risk_index'], reverse=True)
    
    context = {
        'weather': weather,
        'chart_labels': json.dumps(chart_labels),
        'chart_temp': json.dumps(chart_temp),
        'chart_rain': json.dumps(chart_rain),
        'chart_cases': json.dumps(chart_cases),
        'vector_risk_data': vector_risk_data,
    }
    
    return render(request, 'dashboard/environmental_intelligence.html', context)

