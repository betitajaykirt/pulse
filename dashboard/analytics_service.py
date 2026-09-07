"""Live surveillance analytics — always queried from the database."""
from datetime import date, timedelta
import re

from django.db.models import Count, F, Max, Min, Q
from django.db.models.functions import Coalesce, TruncDate, TruncMonth, TruncWeek
from django.utils import timezone

from myapp.models import Barangay, PatientCase, SurveillanceReport, SYMPTOM_CATEGORY_CHOICES
from reports.ml_display import (
    is_inconclusive_disease_label,
    ml_top_prediction_for_report,
    predicted_disease_display,
)
from reports.pidsr_schema import normalize_disease_label

# Kept for import compatibility; disease filters now use live case labels.
SYNDROME_CATEGORY_OPTIONS = SYMPTOM_CATEGORY_CHOICES

STATUS_ORDER = ['Suspected', 'Probable', 'Confirmed']
AGE_BRACKETS = ['0-5', '6-12', '13-19', '20+']
SEX_ORDER = ['Male', 'Female']
INACTIVE_STATUSES = ('Closed', 'Discarded')

STATUS_COLORS = {
    'Suspected': '#f59e0b',
    'Probable': '#f97316',
    'Confirmed': '#ef4444',
}

SEX_COLORS = {
    'Male': '#3b82f6',
    'Female': '#ec4899',
}


def _age_bracket(age):
    try:
        age = int(age)
    except (TypeError, ValueError):
        return None
    if age < 0:
        return None
    if age <= 5:
        return '0-5'
    if age <= 12:
        return '6-12'
    if age <= 19:
        return '13-19'
    return '20+'


def _age_from_birthdate(birthdate, today=None):
    if not birthdate:
        return None
    today = today or timezone.now().date()
    years = today.year - birthdate.year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        years -= 1
    return years if years >= 0 else None


VALID_TIME_RANGES = (
    'all_active',
    'current_month',
    'last_30_days',
    'last_3_months',
    'last_6_months',
    'current_year',
)

_REMARKS_AGE_RE = re.compile(r'Age:\s*(\d+)', re.IGNORECASE)
_REMARKS_SEX_RE = re.compile(r'Sex:\s*(Male|Female)', re.IGNORECASE)
_SKIP_DISEASE_LABELS = frozenset({'unknown', '—', '-', 'n/a', 'na', 'none'})


def _time_window(time_range, today=None):
    today = today or timezone.now().date()
    if time_range == 'all_active':
        return None, today
    if time_range == 'current_month':
        return today.replace(day=1), today
    if time_range == 'last_30_days':
        return today - timedelta(days=30), today
    if time_range == 'last_3_months':
        return today - timedelta(days=90), today
    if time_range == 'last_6_months':
        return today - timedelta(days=183), today
    return today.replace(month=1, day=1), today


def _apply_disease_filter(qs, disease=''):
    """Match stored labels and ML remarks the same way Case Monitoring does."""
    disease = (disease or '').strip()
    if not disease:
        return qs
    from reports.disease_category_data import _disease_label_match_q, disease_label_filter_q

    clause = disease_label_filter_q(disease)
    if not clause:
        clause = _disease_label_match_q(disease)
    if not clause:
        return qs
    return qs.filter(clause).distinct()


def _base_queryset(symptom_category='', barangay_id='', time_range='all_active'):
    """All open surveillance reports in the selected window, read live from MySQL."""
    qs = SurveillanceReport.objects.exclude(status__in=INACTIVE_STATUSES).select_related('barangay')
    start, end = _time_window(time_range)
    if start is not None:
        qs = qs.filter(
            Q(date_of_onset__gte=start, date_of_onset__lte=end)
            | Q(
                date_of_onset__isnull=True,
                report_date__date__gte=start,
                report_date__date__lte=end,
            )
        )
    qs = _apply_disease_filter(qs, symptom_category)
    if barangay_id:
        qs = qs.filter(barangay_id=barangay_id)
    return qs


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, date) and not hasattr(value, 'hour'):
        return value
    if hasattr(value, 'date') and callable(value.date):
        try:
            return value.date()
        except (TypeError, ValueError):
            return None
    return None


def _period_key(dt):
    resolved = _as_date(dt)
    if resolved is None:
        text = str(dt or '')
        return text[:10] if len(text) >= 10 else None
    return resolved.isoformat()


def _with_event_date(qs):
    return qs.annotate(event_date=Coalesce('date_of_onset', TruncDate('report_date')))


def _period_label(dt, interval):
    if interval == 'day':
        return dt.strftime('%b %d')
    if interval == 'week':
        return dt.strftime('%b %d, %Y')
    return dt.strftime('%b %Y')


def _pad_period_keys(period_keys, interval, start_date=None, end_date=None):
    from datetime import date

    if not period_keys and not (start_date and end_date):
        return period_keys

    if period_keys:
        dates = sorted(date.fromisoformat(k) for k in period_keys)
        start = start_date or dates[0]
        end = end_date or dates[-1]
    else:
        start = start_date
        end = end_date

    if start > end:
        start = end

    if interval == 'day':
        step = timedelta(days=1)
    elif interval == 'week':
        step = timedelta(weeks=1)
    else:
        filled = []
        cur = start.replace(day=1)
        end_month = end.replace(day=1)
        while cur <= end_month:
            filled.append(cur.isoformat())
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)
        return filled

    filled = []
    cur = start
    while cur <= end:
        filled.append(cur.isoformat())
        cur += step
    return filled


def build_epi_curve_data(qs, time_range='all_active'):
    today = timezone.now().date()
    dated_qs = _with_event_date(qs)
    window_start, window_end = _time_window(time_range, today)

    if window_start is None:
        extrema = dated_qs.aggregate(mn=Min('event_date'), mx=Max('event_date'))
        expected_start = _as_date(extrema['mn']) or today
        expected_end = _as_date(extrema['mx']) or today
        if expected_start > expected_end:
            expected_start, expected_end = expected_end, expected_start
    else:
        expected_start, expected_end = window_start, window_end

    span_days = (expected_end - expected_start).days

    if time_range in ('current_month', 'last_30_days') or span_days <= 31:
        interval = 'day'
        trunc = F('event_date')
    elif span_days <= 90 or time_range == 'last_3_months':
        interval = 'week'
        trunc = TruncWeek('event_date')
    else:
        interval = 'month'
        trunc = TruncMonth('event_date')

    rows = (
        dated_qs.annotate(period=trunc)
        .values('period', 'status')
        .annotate(count=Count('id'))
        .order_by('period')
    )

    raw_period_keys = []
    for row in rows:
        key = _period_key(row['period'])
        if key and key not in raw_period_keys:
            raw_period_keys.append(key)

    period_keys = _pad_period_keys(
        raw_period_keys, interval, start_date=expected_start, end_date=expected_end,
    )
    if not period_keys:
        period_keys = raw_period_keys

    periods = []
    valid_keys = []
    for key in period_keys:
        try:
            periods.append(_period_label(date.fromisoformat(key[:10]), interval))
            valid_keys.append(key[:10])
        except ValueError:
            continue
    period_keys = valid_keys

    status_data = {s: [0] * len(period_keys) for s in STATUS_ORDER}
    key_index = {k: i for i, k in enumerate(period_keys)}

    for row in rows:
        key = _period_key(row['period'])
        if not key or key not in key_index:
            continue
        status = row['status'] or 'Suspected'
        if status not in status_data:
            status = 'Suspected'
        status_data[status][key_index[key]] += row['count']

    datasets = [
        {
            'label': status,
            'data': status_data[status],
            'backgroundColor': STATUS_COLORS[status],
            'borderRadius': 4,
        }
        for status in STATUS_ORDER
    ]

    if time_range == 'current_month':
        period_title = expected_end.strftime('%B %Y')
    elif time_range == 'all_active':
        period_title = 'All open cases'
    else:
        period_title = f'{expected_start.strftime("%b %d")} – {expected_end.strftime("%b %d, %Y")}'

    return {
        'labels': periods,
        'datasets': datasets,
        'interval': interval,
        'period_title': period_title,
    }


def _age_sex_from_remarks(remarks):
    text = remarks or ''
    age_match = _REMARKS_AGE_RE.search(text)
    sex_match = _REMARKS_SEX_RE.search(text)
    age = int(age_match.group(1)) if age_match else None
    sex = sex_match.group(1) if sex_match else None
    return age, sex


def build_demographics_data(qs):
    report_ids = list(qs.values_list('id', flat=True))
    bracket_sex = {(b, s): 0 for b in AGE_BRACKETS for s in SEX_ORDER}
    counted = set()

    if report_ids:
        for case in PatientCase.objects.filter(surveillance_report_id__in=report_ids).iterator(chunk_size=500):
            bracket = _age_bracket(case.age)
            sex = case.sex if case.sex in SEX_ORDER else None
            if bracket and sex:
                bracket_sex[(bracket, sex)] += 1
                counted.add(case.surveillance_report_id)

        missing = [rid for rid in report_ids if rid not in counted]
        if missing:
            for report in (
                SurveillanceReport.objects.filter(id__in=missing)
                .select_related('patient')
                .only('id', 'patient_id', 'date_of_birth', 'remarks', 'patient__birthdate', 'patient__sex')
                .iterator(chunk_size=300)
            ):
                age = None
                sex = None
                if report.patient_id:
                    age = _age_from_birthdate(getattr(report.patient, 'birthdate', None))
                    patient_sex = getattr(report.patient, 'sex', None)
                    sex = patient_sex if patient_sex in SEX_ORDER else None
                if age is None:
                    age = _age_from_birthdate(report.date_of_birth)
                if age is None or sex not in SEX_ORDER:
                    remark_age, remark_sex = _age_sex_from_remarks(report.remarks)
                    age = age if age is not None else remark_age
                    sex = sex if sex in SEX_ORDER else remark_sex
                bracket = _age_bracket(age)
                if bracket and sex in SEX_ORDER:
                    bracket_sex[(bracket, sex)] += 1

    datasets = [
        {
            'label': sex,
            'data': [bracket_sex[(b, sex)] for b in AGE_BRACKETS],
            'backgroundColor': SEX_COLORS[sex],
            'borderRadius': 4,
        }
        for sex in SEX_ORDER
    ]
    return {'labels': AGE_BRACKETS, 'datasets': datasets}


def _canonical_analytics_disease(label):
    raw = (label or '').strip()
    if not raw or is_inconclusive_disease_label(raw):
        return None
    text = normalize_disease_label(raw)
    if not text or text.lower() in _SKIP_DISEASE_LABELS or is_inconclusive_disease_label(text):
        return None
    return text


def _analytics_disease_for_report(report):
    """Same confirmed / ML-predicted label used on the map and Case Monitoring."""
    display = predicted_disease_display(report)
    label = _canonical_analytics_disease(display.get('primary'))
    if label:
        return label
    return _canonical_analytics_disease(ml_top_prediction_for_report(report))


def _count_by_analytics_disease(qs):
    aggregated = {}
    reports = qs.select_related(None).only(
        'id', 'syndrome_type', 'suspected_disease', 'status', 'remarks',
    )
    for report in reports.iterator(chunk_size=300):
        label = _analytics_disease_for_report(report)
        if not label:
            continue
        aggregated[label] = aggregated.get(label, 0) + 1
    return aggregated


def build_disease_distribution_data(qs):
    aggregated = _count_by_analytics_disease(qs)
    sorted_items = sorted(aggregated.items(), key=lambda x: x[1], reverse=True)
    base_colors = [
        '#0F4C81', '#00A6A6', '#E11D48', '#f59e0b', '#8b5cf6',
        '#10b981', '#f43f5e', '#6366f1', '#14b8a6', '#eab308',
    ]
    labels, data, background_colors = [], [], []
    for i, (disease, count) in enumerate(sorted_items):
        labels.append(disease)
        data.append(count)
        background_colors.append(base_colors[i % len(base_colors)])

    return {
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': background_colors,
            'borderWidth': 0,
        }],
    }


def build_top_hotspots_data(qs):
    rows = (
        qs.values(barangay_name=F('barangay__barangay_name'))
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    labels = []
    data = []
    for row in rows:
        labels.append(row['barangay_name'] or 'Unassigned')
        data.append(row['count'])
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Total Cases',
            'data': data,
            'backgroundColor': '#E11D48',
            'borderRadius': 4,
        }],
    }


def build_top_disease_breakdown(qs, limit=2):
    aggregated = _count_by_analytics_disease(qs)
    sorted_items = sorted(aggregated.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{'label': label, 'count': count} for label, count in sorted_items]


def get_analytics_disease_choices():
    qs = SurveillanceReport.objects.exclude(status__in=INACTIVE_STATUSES)
    labels = sorted(_count_by_analytics_disease(qs).keys())
    return [('', 'All Diseases')] + [(label, label) for label in labels]


def build_summary_stats(qs, symptom_category_filter=''):
    if symptom_category_filter:
        dominant_syndrome = normalize_disease_label(symptom_category_filter)
    else:
        top = build_top_disease_breakdown(qs, limit=1)
        dominant_syndrome = top[0]['label'] if top else '—'

    report_ids = list(qs.values_list('id', flat=True))
    bracket_sex = {}
    if report_ids:
        for case in PatientCase.objects.filter(surveillance_report_id__in=report_ids).iterator(chunk_size=500):
            bracket = _age_bracket(case.age)
            if not bracket:
                continue
            key = (bracket, case.sex or '—')
            bracket_sex[key] = bracket_sex.get(key, 0) + 1

    top_demo = '—'
    if bracket_sex:
        top_key = max(bracket_sex, key=bracket_sex.get)
        top_demo = f'{top_key[0]} yrs, {top_key[1]}'

    status_rows = qs.values('status').annotate(count=Count('id')).order_by('-count')
    top_status = status_rows[0]['status'] if status_rows else '—'

    return {
        'dominant_syndrome_category': dominant_syndrome,
        'top_demographic': top_demo,
        'top_status': top_status or '—',
    }


def build_live_kpis(qs):
    from reports.models import BarangayRiskLog

    confirmed = qs.filter(status='Confirmed').count()
    pending = qs.filter(validation_status='pending').exclude(status='Confirmed').count()
    hotspot_count = BarangayRiskLog.objects.filter(is_active_alert=True).count()
    return {
        'active_total': qs.count(),
        'confirmed': confirmed,
        'pending_lab': pending,
        'hotspot_count': hotspot_count,
        'top_diseases': build_top_disease_breakdown(qs, limit=2),
    }


def get_analytics_payload(*, symptom_category='', barangay_id='', time_range='all_active'):
    qs = _base_queryset(
        symptom_category=symptom_category,
        barangay_id=barangay_id,
        time_range=time_range,
    )
    kpis = build_live_kpis(qs)
    return {
        'total_cases': kpis['active_total'],
        'generated_at': timezone.now().isoformat(),
        'source': 'surveillance_reports',
        'kpis': kpis,
        'summary': build_summary_stats(qs, symptom_category_filter=symptom_category),
        'epi_curve': build_epi_curve_data(qs, time_range=time_range),
        'demographics': build_demographics_data(qs),
        'disease_distribution': build_disease_distribution_data(qs),
        'hotspots': build_top_hotspots_data(qs),
        'filters': {
            'symptom_category': symptom_category,
            'barangay_id': str(barangay_id or ''),
            'time_range': time_range,
        },
    }


def get_barangay_options():
    return list(Barangay.objects.all().order_by('barangay_name').values('id', 'barangay_name'))
