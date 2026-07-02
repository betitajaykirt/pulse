"""Audit and system log helpers — pure Django ORM."""
from django.utils import timezone

from myapp.models import Admin, AuditLog, SuperAdmin, SystemLog, User

ROLE_SLUGS = {
    'super_admin', 'admin', 'health_officer', 'surveillance_officer',
    'barangay_health_worker', 'encoder', 'user',
}


def _infer_user_type(user_role: str) -> str:
    """Map a stored role slug to an account table for legacy log hydration."""
    if user_role == 'super_admin':
        return 'super_admin'
    if user_role == 'admin':
        return 'admin'
    return 'user'


def _display_from_account(account) -> str:
    """First/last name, then email, then username — same priority as Django auth fallback."""
    if not account:
        return ''
    first = (getattr(account, 'first_name', '') or '').strip()
    last = (getattr(account, 'last_name', '') or '').strip()
    if first or last:
        return f'{first} {last}'.strip()
    email = (getattr(account, 'email', '') or '').strip()
    if email:
        return email
    username = (getattr(account, 'username', '') or '').strip()
    return username


def _lookup_account(user_id, user_type=None):
    if not user_id:
        return None
    try:
        if user_type == 'super_admin':
            return SuperAdmin.objects.filter(id=user_id).first()
        if user_type == 'admin':
            return Admin.objects.filter(id=user_id).first()
        account = User.objects.filter(id=user_id).first()
        if account:
            return account
        account = Admin.objects.filter(id=user_id).first()
        if account:
            return account
        return SuperAdmin.objects.filter(id=user_id).first()
    except Exception:
        return None


def build_log_user_display(*, request=None, user_id=None, user_role=None) -> str:
    """
    Determine the human-readable name stored on SystemLog.user_display_name.

    Uses Django auth when available, then PULSE session/ORM lookup for custom auth.
    """
    django_user = getattr(request, 'user', None) if request is not None else None
    if django_user and getattr(django_user, 'is_authenticated', False):
        first = getattr(django_user, 'first_name', '').strip()
        last = getattr(django_user, 'last_name', '').strip()

        if first or last:
            return f'{first} {last}'.strip()

        return django_user.email if django_user.email else django_user.username

    # PULSE custom session authentication (primary app login path)
    if request is not None and request.session.get('user_id'):
        session_name = (request.session.get('full_name') or '').strip()
        if session_name:
            return session_name

        account = _lookup_account(
            request.session.get('user_id'),
            request.session.get('user_type'),
        )
        name = _display_from_account(account)
        if name:
            return name

    # Hydrate legacy rows or calls that pass explicit user_id without request
    if user_id:
        account = _lookup_account(user_id, _infer_user_type(user_role or ''))
        name = _display_from_account(account)
        if name:
            return name

    return 'Anonymous / System'


def _stored_name_is_valid(stored: str) -> bool:
    """Reject legacy values that are only a role slug, not a person's name."""
    if not stored:
        return False
    normalized = stored.strip().lower().replace(' ', '_')
    return normalized not in ROLE_SLUGS


def display_name_for_system_log(log) -> str:
    stored = (getattr(log, 'user_display_name', None) or '').strip()
    if _stored_name_is_valid(stored):
        return stored
    return build_log_user_display(user_id=log.user_id, user_role=log.user_role)


def display_name_for_audit_log(log) -> str:
    stored = (getattr(log, 'actor_display_name', None) or '').strip()
    if _stored_name_is_valid(stored):
        return stored
    return build_log_user_display(
        user_id=log.actor_id,
        user_role=log.actor_type,
    )


def log_audit(
    actor_id,
    actor_type,
    action,
    target_id=None,
    details=None,
    *,
    request=None,
    actor_display_name=None,
):
    if actor_display_name is None:
        actor_display_name = build_log_user_display(
            request=request,
            user_id=actor_id,
            user_role=actor_type,
        )

    AuditLog.objects.create(
        actor_id=actor_id,
        actor_type=actor_type,
        actor_display_name=actor_display_name,
        action=action,
        target_id=target_id,
        details=details,
        created_at=timezone.now(),
    )


def log_system(
    activity_type,
    log_message,
    user_role=None,
    user_id=None,
    module=None,
    ip_address=None,
    log_level='info',
    *,
    request=None,
    user_display_name=None,
):
    if user_display_name is None:
        user_display_name = build_log_user_display(
            request=request,
            user_id=user_id,
            user_role=user_role,
        )

    SystemLog.objects.create(
        user_role=user_role,
        user_id=user_id,
        user_display_name=user_display_name,
        activity_type=activity_type,
        module=module,
        ip_address=ip_address,
        log_message=log_message,
        log_level=log_level,
        created_at=timezone.now(),
    )
