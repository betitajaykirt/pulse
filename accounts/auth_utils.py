"""Session-based auth helpers using Django ORM (mirrors PHP BaseController auth methods)."""
import bcrypt
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from myapp.models import SuperAdmin, Admin, User, LoginAttempt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def get_current_user(request):
    uid = request.session.get('user_id')
    utype = request.session.get('user_type', 'user')
    if not uid:
        return None
    try:
        if utype == 'super_admin':
            return SuperAdmin.objects.get(id=uid)
        elif utype == 'admin':
            return Admin.objects.get(id=uid)
        else:
            return User.objects.get(id=uid)
    except Exception:
        return None


def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            messages.warning(request, 'Please log in to continue.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.session.get('user_id'):
                messages.warning(request, 'Please log in to continue.')
                return redirect('login')
            if request.session.get('role') not in roles:
                messages.error(request, 'Access denied.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def check_lockout(email: str) -> bool:
    """Returns True if the account is locked out."""
    if not getattr(settings, 'LOCKOUT_ENABLED', True):
        return False
    window = timezone.now() - timedelta(seconds=settings.LOCKOUT_WINDOW_SECONDS)
    cnt = LoginAttempt.objects.filter(
        email=email,
        attempted_at__gt=window,
        success=False
    ).count()
    return cnt >= settings.LOCKOUT_MAX_ATTEMPTS


def record_attempt(email: str, success: bool, ip: str = None):
    LoginAttempt.objects.create(
        email=email,
        success=success,
        ip_address=ip,
        attempted_at=timezone.now(),
    )


def build_full_name(user) -> str:
    # Works for both model instances and dictionaries (if any dict remains)
    if isinstance(user, dict):
        parts = [
            user.get('first_name', ''),
            user.get('middle_name') or user.get('middle_initial') or '',
            user.get('last_name', ''),
            user.get('suffix') or '',
        ]
    else:
        parts = [
            getattr(user, 'first_name', ''),
            getattr(user, 'middle_name', '') or '',
            getattr(user, 'last_name', ''),
            getattr(user, 'suffix', '') or '',
        ]
    return ' '.join(p for p in parts if p).strip()
