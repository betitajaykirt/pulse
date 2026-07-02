"""Barangay-level data isolation helpers for PULSE."""

from myapp.models import Barangay, User

# City-wide roles see all 24 barangays
CITY_WIDE_ROLES = frozenset({
    'admin', 'super_admin', 'health_officer', 'surveillance_officer',
})

# Localized roles are restricted to their assigned barangay
BARANGAY_SCOPED_ROLES = frozenset({
    'barangay_health_worker', 'encoder',
})


def is_city_wide_role(role):
    return role in CITY_WIDE_ROLES


def is_barangay_scoped_role(role):
    return role in BARANGAY_SCOPED_ROLES


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
