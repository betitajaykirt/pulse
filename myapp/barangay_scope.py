"""Barangay-level data isolation helpers for PULSE."""

from django.db.models import Q

from myapp.models import Barangay, User

# City-wide roles see all 24 barangays
CITY_WIDE_ROLES = frozenset({
    'admin', 'super_admin', 'health_officer', 'surveillance_officer',
})

# Localized roles are restricted to their assigned barangay
BARANGAY_SCOPED_ROLES = frozenset({
    'barangay_health_worker', 'encoder', 'catchment_nurse',
})


def is_city_wide_role(role):
    return role in CITY_WIDE_ROLES


def is_barangay_scoped_role(role):
    return role in BARANGAY_SCOPED_ROLES


def user_display_name(user) -> str:
    if not user:
        return ''
    name = f'{(user.first_name or "").strip()} {(user.last_name or "").strip()}'.strip()
    return name or (getattr(user, 'email', None) or getattr(user, 'username', None) or '')


def catchment_nurses_by_barangay(barangay_names=None) -> dict:
    """Map casefolded barangay name to the assigned catchment nurse."""
    qs = User.objects.filter(role='catchment_nurse', status='active')
    if barangay_names is not None:
        cleaned = [str(name).strip() for name in barangay_names if name]
        if not cleaned:
            return {}
        query = Q()
        for name in cleaned:
            query |= Q(barangay_text__iexact=name)
        qs = qs.filter(query)

    mapping = {}
    for nurse in qs.order_by('id'):
        key = (nurse.barangay_text or '').strip().casefold()
        if key and key not in mapping:
            mapping[key] = nurse
    return mapping


def resolve_catchment_nurse(barangay_name: str | None):
    """Return the catchment nurse assigned to a barangay, or None."""
    name = (barangay_name or '').strip()
    if not name:
        return None
    return catchment_nurses_by_barangay([name]).get(name.casefold())


def catchment_nurse_officer_fields(nurse=None, *, barangay_name=None) -> dict:
    """Officer-in-charge fields used by alert cards and related popups."""
    if nurse is None and barangay_name:
        nurse = resolve_catchment_nurse(barangay_name)
    return {
        'officer_name': user_display_name(nurse),
        'officer_contact': (nurse.contact_number or '').strip() if nurse else '',
        'officer_email': (nurse.email or '').strip() if nurse else '',
    }


def resolve_user_barangay(user):
    """Return the Barangay row for a user's assigned barangay_text, or None."""
    if not user or not user.barangay_text:
        return None
    return Barangay.objects.filter(barangay_name=user.barangay_text).first()


def get_request_barangay(request):
    """
    Return the Barangay instance a scoped user may access.
    Returns None for city-wide roles (no restriction).
    """
    role = request.session.get('role')
    if is_city_wide_role(role):
        return None
    if not is_barangay_scoped_role(role):
        return None
    user = User.objects.filter(id=request.session.get('user_id')).first()
    return resolve_user_barangay(user)


def barangay_queryset_filter(request, queryset, field='barangay_id'):
    """Restrict a queryset to the user's barangay when applicable."""
    barangay = get_request_barangay(request)
    if barangay is None and is_city_wide_role(request.session.get('role', '')):
        return queryset
    if barangay is None:
        return queryset.none()
    return queryset.filter(**{field: barangay.id})


def scoped_map_query(request) -> str:
    """Return ``?barangay=Name`` for barangay-scoped roles, else empty string."""
    role = request.session.get('role', '')
    if not is_barangay_scoped_role(role):
        return ''
    barangay_name = (
        request.session.get('assigned_barangay')
        or request.session.get('barangay_text')
        or ''
    ).strip()
    if not barangay_name:
        return ''
    from urllib.parse import urlencode
    return '?' + urlencode({'barangay': barangay_name})
