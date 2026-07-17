from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from accounts.auth_utils import login_required
from myapp.audit_utils import display_name_for_audit_log, display_name_for_system_log
from myapp.models import (
    User, Admin, SuperAdmin, Barangay, SurveillanceReport,
    Alert, SystemLog, AuditLog, NotificationLog,
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
        ctx['active_alerts']   = Alert.objects.filter(status='active').count()
        ctx['total_barangays'] = Barangay.objects.count()
        ctx['pending_reports'] = SurveillanceReport.objects.filter(validation_status='pending').exclude(status='Closed').count()
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
        alerts = Alert.objects.order_by('-alert_date')[:50]
        notifications = NotificationLog.objects.select_related('alert').order_by('-sent_at')[:50]
    elif role in BARANGAY_SCOPED_ROLES:
        user = User.objects.filter(id=request.session.get('user_id')).first()
        barangay = resolve_user_barangay(user)
        if barangay:
            notifications = NotificationLog.objects.select_related('alert').filter(
                recipient_role=role,
                message_summary__icontains=barangay.barangay_name
            ).order_by('-sent_at')[:50]
            alert_ids = [n.alert_id for n in notifications]
            alerts = Alert.objects.filter(id__in=alert_ids).order_by('-alert_date')[:50]
        else:
            alerts = Alert.objects.none()
            notifications = NotificationLog.objects.none()
    else:
        alerts = Alert.objects.none()
        notifications = NotificationLog.objects.none()

    return render(request, 'dashboard/alerts_inbox.html', {
        'alerts': alerts,
        'notifications': notifications,
    })


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

