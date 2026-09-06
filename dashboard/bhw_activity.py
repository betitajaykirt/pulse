"""Build organized BHW activity rows for admin and catchment-nurse oversight."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable, Optional

from django.utils import timezone

from myapp.models import Barangay, SurveillanceReport, SystemLog, User


def _worker_name(user) -> str:
    if not user:
        return 'Unknown BHW'
    first = (user.first_name or '').strip()
    last = (user.last_name or '').strip()
    if first or last:
        return f'{first} {last}'.strip()
    return (user.email or user.username or 'Unknown BHW').strip()


def _barangay_name(report) -> str:
    if getattr(report, 'barangay', None) and report.barangay.barangay_name:
        return report.barangay.barangay_name
    return '—'


def _disease_label(report) -> str:
    return (report.syndrome_type or report.suspected_disease or 'Unclassified').strip() or 'Unclassified'


def bhw_user_ids(*, barangay_name: Optional[str] = None) -> list[int]:
    qs = User.objects.filter(role='barangay_health_worker')
    if barangay_name:
        qs = qs.filter(barangay_text__iexact=barangay_name)
    return list(qs.values_list('id', flat=True))


def build_bhw_activity_entries(
    *,
    barangay_name: Optional[str] = None,
    activity: str = '',
    search: str = '',
    limit: int = 250,
) -> list[dict]:
    worker_ids = bhw_user_ids(barangay_name=barangay_name)
    entries: list[dict] = []

    want_reports = activity in ('', 'submitted')
    want_logins = activity in ('', 'signed_in')

    if want_reports:
        report_qs = (
            SurveillanceReport.objects.filter(submitted_by_id__in=worker_ids)
            .select_related('barangay', 'submitted_by', 'session')
            .order_by('-report_date')
        )
        if barangay_name:
            report_qs = report_qs.filter(barangay__barangay_name__iexact=barangay_name)

        grouped: dict[int, list] = defaultdict(list)
        singles: list = []
        for report in report_qs[:800]:
            if report.session_id:
                grouped[report.session_id].append(report)
            else:
                singles.append(report)

        for rows in grouped.values():
            first = rows[0]
            diseases = []
            seen = set()
            for row in rows:
                label = _disease_label(row)
                if label not in seen:
                    seen.add(label)
                    diseases.append(label)
            disease_text = ', '.join(diseases[:3])
            if len(diseases) > 3:
                disease_text += f' +{len(diseases) - 3} more'
            entries.append({
                'when': first.report_date,
                'barangay': _barangay_name(first),
                'worker': _worker_name(first.submitted_by),
                'worker_id': first.submitted_by_id,
                'activity': 'Submitted case report',
                'activity_key': 'submitted',
                'detail': f'{len(rows)} patient case(s) · {disease_text}',
                'status': first.status or '—',
                'ref': f'Session #{first.session_id}',
            })

        for report in singles:
            entries.append({
                'when': report.report_date,
                'barangay': _barangay_name(report),
                'worker': _worker_name(report.submitted_by),
                'worker_id': report.submitted_by_id,
                'activity': 'Submitted case report',
                'activity_key': 'submitted',
                'detail': f'{_disease_label(report)} · {report.patient_name or "Unknown resident"}',
                'status': report.status or '—',
                'ref': f'Report #{report.id}',
            })

    if want_logins and worker_ids:
        workers = {
            user.id: user
            for user in User.objects.filter(id__in=worker_ids)
        }
        login_qs = SystemLog.objects.filter(
            user_id__in=worker_ids,
            activity_type='login_success',
        ).order_by('-created_at')[:300]
        for log in login_qs:
            worker = workers.get(log.user_id)
            worker_brgy = (getattr(worker, 'barangay_text', None) or '').strip()
            if barangay_name and worker_brgy.casefold() != barangay_name.casefold():
                continue
            entries.append({
                'when': log.created_at,
                'barangay': worker_brgy or '—',
                'worker': _worker_name(worker) if worker else (log.user_display_name or 'Unknown BHW'),
                'worker_id': log.user_id,
                'activity': 'Signed in',
                'activity_key': 'signed_in',
                'detail': log.log_message or 'BHW signed in to PULSE',
                'status': '—',
                'ref': 'Login',
            })

    search = (search or '').strip().lower()
    if search:
        entries = [
            row for row in entries
            if search in (row['worker'] or '').lower()
            or search in (row['detail'] or '').lower()
            or search in (row['barangay'] or '').lower()
            or search in (row['ref'] or '').lower()
        ]

    fallback = timezone.make_aware(datetime(1970, 1, 1))
    entries.sort(key=lambda row: row['when'] or fallback, reverse=True)
    return entries[:limit]


def barangay_filter_choices() -> Iterable[Barangay]:
    return Barangay.objects.all().order_by('barangay_name')
