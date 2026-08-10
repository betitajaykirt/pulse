"""Aggregate PatientCase data for surveillance analytics charts."""
from datetime import timedelta

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
    codes = SYMPTOM_CATEGORY_CODES.get(symptom_category)
    if not codes:
        return qs.none()
    symptom_q = Q()
    for code in codes:
        symptom_q |= Q(symptoms_json__contains=f'"{code}"')
    return qs.filter(symptom_q)


def _base_queryset(symptom_category='', barangay_id='', time_range='current_year'):
    now = timezone.now().date()
    qs = PatientCase.objects.filter(
        date_of_onset__isnull=False,
        surveillance_report__isnull=False,
    ).select_related('surveillance_report', 'session', 'barangay')

    qs = _apply_symptom_category_filter(qs, symptom_category)

    if barangay_id:
        qs = qs.filter(barangay_id=barangay_id)

    if time_range == 'last_3_months':
        cutoff = now - timedelta(days=90)
        qs = qs.filter(date_of_onset__gte=cutoff)
    elif time_range == 'last_6_months':
        cutoff = now - timedelta(days=183)
        qs = qs.filter(date_of_onset__gte=cutoff)
    else:
        qs = qs.filter(date_of_onset__year=now.year)

    return qs


def _period_label(dt, interval):
    if interval == 'week':
        return dt.strftime('%b %d, %Y')
    return dt.strftime('%b %Y')


def build_epi_curve_data(qs, time_range='current_year'):
    interval = 'week' if time_range == 'last_3_months' else 'month'
    trunc = TruncWeek('date_of_onset') if interval == 'week' else TruncMonth('date_of_onset')

    rows = (
        qs.annotate(period=trunc)
        .values('period', status=F('surveillance_report__status'))
        .annotate(count=Count('id'))
        .order_by('period')
    )

    periods = []
    period_keys = []
    for row in rows:
        key = row['period'].isoformat() if row['period'] else None
        if key and key not in period_keys:
            period_keys.append(key)
            periods.append(_period_label(row['period'], interval))

    status_data = {s: [0] * len(period_keys) for s in STATUS_ORDER}
    key_index = {k: i for i, k in enumerate(period_keys)}

    for row in rows:
        key = row['period'].isoformat() if row['period'] else None
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


def build_disease_distribution_data(qs):
    rows = (
        qs.exclude(
            Q(surveillance_report__syndrome_type__isnull=True) |
            Q(surveillance_report__syndrome_type__exact='') |
            Q(surveillance_report__syndrome_type__iexact='inconclusive') |
            Q(surveillance_report__syndrome_type__iexact='unclassified') |
            Q(surveillance_report__syndrome_type__iexact='inconclusive syndromic pattern')
        )
        .values(disease=F('surveillance_report__syndrome_type'))
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    labels = []
    data = []
    
    base_colors = ['#0F4C81', '#00A6A6', '#E11D48', '#f59e0b', '#8b5cf6', '#10b981', '#f43f5e']
    background_colors = []

    for i, row in enumerate(rows):
        disease = row['disease']
        # Optionally, format to title case if not already
        labels.append(disease.title() if disease else 'Unknown')
        data.append(row['count'])
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
    category_labels = dict(SYMPTOM_CATEGORY_CHOICES)

    if symptom_category_filter:
        dominant_syndrome = category_labels.get(symptom_category_filter, symptom_category_filter)
    else:
        category_counts = {cat: 0 for cat in SYMPTOM_CATEGORY_CODES}
        for case in qs.iterator(chunk_size=500):
            case_symptoms = set(case.symptoms_list())
            for cat, codes in SYMPTOM_CATEGORY_CODES.items():
                if case_symptoms & codes:
                    category_counts[cat] += 1
        dominant_syndrome = '—'
        if category_counts and max(category_counts.values()) > 0:
            top_cat = max(category_counts, key=category_counts.get)
            dominant_syndrome = category_labels.get(top_cat, top_cat)

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
