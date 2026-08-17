"""Aggregate PatientCase data for surveillance analytics charts."""
from datetime import timedelta

from django.db import models
from django.db.models import Count, F, Q
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone

from myapp.models import PatientCase, Barangay, SYMPTOM_CATEGORY_CODES, SYMPTOM_CATEGORY_CHOICES

SYNDROME_CATEGORY_OPTIONS = SYMPTOM_CATEGORY_CHOICES

STATUS_ORDER = ['Suspected', 'Probable', 'Confirmed']
AGE_BRACKETS = ['0-5', '6-12', '13-19', '20+']
SEX_ORDER = ['Male', 'Female']

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
    if age <= 5:
        return '0-5'
    if age <= 12:
        return '6-12'
    if age <= 19:
        return '13-19'
    return '20+'


def _apply_symptom_category_filter(qs, symptom_category=''):
    if not symptom_category:
        return qs
    return qs.filter(surveillance_report__syndrome_type__icontains=symptom_category)


def _base_queryset(symptom_category='', barangay_id='', time_range='current_year'):
    now = timezone.now().date()
    qs = PatientCase.objects.filter(
        date_of_onset__isnull=False,
        surveillance_report__isnull=False,
    ).select_related('surveillance_report', 'session', 'barangay')

    qs = _apply_symptom_category_filter(qs, symptom_category)

    if barangay_id:
        qs = qs.filter(barangay_id=barangay_id)

    if time_range == 'last_30_days':
        cutoff = now - timedelta(days=30)
        qs = qs.filter(date_of_onset__gte=cutoff)
    elif time_range == 'last_3_months':
        cutoff = now - timedelta(days=90)
        qs = qs.filter(date_of_onset__gte=cutoff)
    elif time_range == 'last_6_months':
        cutoff = now - timedelta(days=183)
        qs = qs.filter(date_of_onset__gte=cutoff)
    else:
        qs = qs.filter(date_of_onset__year=now.year)

    return qs


def _period_label(dt, interval):
    if interval == 'day':
        return dt.strftime('%b %d')
    if interval == 'week':
        return dt.strftime('%b %d, %Y')
    return dt.strftime('%b %Y')


def _pad_period_keys(period_keys, interval, start_date=None, end_date=None):
    """Fill gaps in period_keys so every day/week/month in the range is represented."""
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

    # Ensure start is not after end
    if start > end:
        start = end

    if interval == 'day':
        step = timedelta(days=1)
    elif interval == 'week':
        step = timedelta(weeks=1)
    else:
        # Monthly: step by ~30 days, snapping to 1st of month
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


def build_epi_curve_data(qs, time_range='current_year'):
    """
    Build Epi-Curve chart payload with adaptive time intervals.

    Interval selection:
      - Data span ≤ 31 days  → daily (YYYY-MM-DD)
      - Data span ≤ 90 days  → weekly
      - Data span > 90 days  → monthly

    All gaps are zero-filled so Chart.js renders continuous lines.
    """
    # --- 1. Determine the actual data span to choose the right interval ---
    date_range = qs.aggregate(
        earliest=models.Min('date_of_onset'),
        latest=models.Max('date_of_onset'),
    )
    earliest = date_range['earliest']
    latest = date_range['latest']

    if earliest and latest:
        span_days = (latest - earliest).days
    else:
        span_days = 0

    # Adaptive interval based on data density
    if span_days <= 31:
        interval = 'day'
        trunc = F('date_of_onset')
    elif span_days <= 90 or time_range == 'last_3_months':
        interval = 'week'
        trunc = TruncWeek('date_of_onset')
    else:
        interval = 'month'
        trunc = TruncMonth('date_of_onset')

    # --- 2. Query grouped counts ---
    rows = (
        qs.annotate(period=trunc)
        .values('period', status=F('surveillance_report__status'))
        .annotate(count=Count('id'))
        .order_by('period')
    )

    # Collect unique period keys from the query
    raw_period_keys = []
    for row in rows:
        if row['period']:
            dt = row['period']
            # TruncDate returns a date, TruncWeek/TruncMonth returns datetime
            if hasattr(dt, 'date') and callable(dt.date):
                key = dt.date().isoformat()
            else:
                key = dt.isoformat()
            if key not in raw_period_keys:
                raw_period_keys.append(key)

    from django.utils import timezone
    today = timezone.now().date()
    expected_start = earliest if earliest else today
    
    if time_range == 'last_30_days':
        expected_start = today - timedelta(days=30)
    elif time_range == 'last_3_months':
        expected_start = today - timedelta(days=90)
    elif time_range == 'last_6_months':
        expected_start = today - timedelta(days=183)
    elif time_range == 'current_year':
        expected_start = today.replace(month=1, day=1)

    # --- 3. Pad the timeline so every interval slot exists ---
    period_keys = _pad_period_keys(raw_period_keys, interval, start_date=expected_start, end_date=today)
    if not period_keys:
        period_keys = raw_period_keys

    from datetime import date as date_type
    periods = [_period_label(date_type.fromisoformat(k), interval) for k in period_keys]

    # --- 4. Build zero-filled data arrays per status ---
    status_data = {s: [0] * len(period_keys) for s in STATUS_ORDER}
    key_index = {k: i for i, k in enumerate(period_keys)}

    for row in rows:
        if not row['period']:
            continue
        dt = row['period']
        if hasattr(dt, 'date') and callable(dt.date):
            key = dt.date().isoformat()
        else:
            key = dt.isoformat()
        status = row['status'] or 'Unclassified'
        if key in key_index and status in status_data:
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

    return {
        'labels': periods,
        'datasets': datasets,
        'interval': interval,
    }


def build_demographics_data(qs):
    bracket_sex = {(b, s): 0 for b in AGE_BRACKETS for s in SEX_ORDER}

    for case in qs.iterator(chunk_size=500):
        bracket = _age_bracket(case.age)
        sex = case.sex if case.sex in SEX_ORDER else 'Male'
        bracket_sex[(bracket, sex)] = bracket_sex.get((bracket, sex), 0) + 1

    datasets = [
        {
            'label': sex,
            'data': [bracket_sex[(b, sex)] for b in AGE_BRACKETS],
            'backgroundColor': SEX_COLORS[sex],
            'borderRadius': 4,
        }
        for sex in SEX_ORDER
    ]

    return {
        'labels': AGE_BRACKETS,
        'datasets': datasets,
    }


def _normalize_disease_name(disease):
    if not disease:
        return 'Unknown'
    clean_name = disease.strip().lower()
    
    if 'dengue' in clean_name:
        return 'Dengue Fever'
    if 'lepto' in clean_name:
        return 'Leptospirosis'
    if 'insufficient' in clean_name:
        return 'Insufficient Data For Prediction'
        
    return disease.title()


def build_disease_distribution_data(qs):
    rows = (
        qs.exclude(
            Q(surveillance_report__syndrome_type__isnull=True) |
            Q(surveillance_report__syndrome_type__exact='') |
            Q(surveillance_report__syndrome_type__icontains='inconclusive') |
            Q(surveillance_report__syndrome_type__icontains='unclassified') |
            Q(surveillance_report__syndrome_type__icontains='insufficient data') |
            Q(surveillance_report__syndrome_type__icontains='pending')
        )
        .values(disease=F('surveillance_report__syndrome_type'))
        .annotate(count=Count('id'))
    )

    aggregated = {}
    for row in rows:
        norm_disease = _normalize_disease_name(row['disease'])
        aggregated[norm_disease] = aggregated.get(norm_disease, 0) + row['count']
        
    sorted_items = sorted(aggregated.items(), key=lambda x: x[1], reverse=True)

    labels = []
    data = []
    
    base_colors = ['#0F4C81', '#00A6A6', '#E11D48', '#f59e0b', '#8b5cf6', '#10b981', '#f43f5e']
    background_colors = []

    for i, (disease, count) in enumerate(sorted_items):
        labels.append(disease)
        data.append(count)
        background_colors.append(base_colors[i % len(base_colors)])
            
    datasets = [{
        'data': data,
        'backgroundColor': background_colors,
        'borderWidth': 0
    }]
    
    return {
        'labels': labels,
        'datasets': datasets,
    }


def build_top_hotspots_data(qs):
    # Aggregate cases grouped by barangay_name, sort descending, get top 5
    rows = (
        qs.values(barangay_name=F('barangay__barangay_name'))
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    
    labels = []
    data = []
    
    for row in rows:
        name = row['barangay_name'] or 'Unassigned'
        labels.append(name)
        data.append(row['count'])
        
    datasets = [{
        'label': 'Total Cases',
        'data': data,
        'backgroundColor': '#E11D48',
        'borderRadius': 4
    }]
    
    return {
        'labels': labels,
        'datasets': datasets,
    }


def build_summary_stats(qs, symptom_category_filter=''):
    if symptom_category_filter:
        dominant_syndrome = symptom_category_filter
    else:
        top_disease = qs.exclude(
            Q(surveillance_report__syndrome_type__isnull=True) |
            Q(surveillance_report__syndrome_type__exact='') |
            Q(surveillance_report__syndrome_type__icontains='inconclusive') |
            Q(surveillance_report__syndrome_type__icontains='unclassified') |
            Q(surveillance_report__syndrome_type__icontains='insufficient data') |
            Q(surveillance_report__syndrome_type__icontains='pending')
        ).values('surveillance_report__syndrome_type').annotate(c=Count('id')).order_by('-c').first()
        dominant_syndrome = top_disease['surveillance_report__syndrome_type'] if top_disease else '—'

    bracket_sex = {}
    for case in qs.iterator(chunk_size=500):
        key = (_age_bracket(case.age), case.sex)
        bracket_sex[key] = bracket_sex.get(key, 0) + 1

    top_demo = '—'
    if bracket_sex:
        top_key = max(bracket_sex, key=bracket_sex.get)
        top_demo = f'{top_key[0]} yrs, {top_key[1]}'

    status_rows = (
        qs.values(status=F('surveillance_report__status'))
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    top_status = status_rows[0]['status'] if status_rows else '—'

    return {
        'dominant_syndrome_category': dominant_syndrome,
        'top_demographic': top_demo,
        'top_status': top_status or '—',
    }


def get_analytics_payload(*, symptom_category='', barangay_id='', time_range='current_year'):
    qs = _base_queryset(
        symptom_category=symptom_category,
        barangay_id=barangay_id,
        time_range=time_range,
    )
    total_cases = qs.count()

    return {
        'total_cases': total_cases,
        'summary': build_summary_stats(qs, symptom_category_filter=symptom_category),
        'epi_curve': build_epi_curve_data(qs, time_range=time_range),
        'demographics': build_demographics_data(qs),
        'disease_distribution': build_disease_distribution_data(qs),
        'hotspots': build_top_hotspots_data(qs),
        'filters': {
            'symptom_category': symptom_category,
            'barangay_id': barangay_id,
            'time_range': time_range,
        },
    }


def get_barangay_options():
    return list(Barangay.objects.all().order_by('barangay_name').values('id', 'barangay_name'))
