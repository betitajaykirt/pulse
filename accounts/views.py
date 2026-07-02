from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from myapp.models import SuperAdmin, Admin, User, PulseSession
from myapp.audit_utils import log_system
from .auth_utils import (
    verify_password, hash_password, build_full_name,
    check_lockout, record_attempt, login_required, get_current_user
)


# ── Login ─────────────────────────────────────────────────────────

def login_view(request):
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        ip       = request.META.get('REMOTE_ADDR')

        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return render(request, 'auth/login.html')

        if check_lockout(email):
            messages.error(request, 'Account temporarily locked. Try again in 15 minutes.')
            return render(request, 'auth/login.html')

        user_obj = None
        utype = None

        # Check SuperAdmin
        sa = SuperAdmin.objects.filter(email=email).first()
        if sa and verify_password(password, sa.password_hash):
            user_obj, utype = sa, 'super_admin'

        if not user_obj:
            a = Admin.objects.filter(email=email).first()
            if a and verify_password(password, a.password_hash):
                user_obj, utype = a, 'admin'

        if not user_obj:
            u = User.objects.filter(email=email).first()
            if u and verify_password(password, u.password_hash):
                user_obj, utype = u, 'user'

        if user_obj:
            if user_obj.status == 'inactive':
                record_attempt(email, False, ip)
                messages.error(request, 'Your account has been deactivated.')
                return render(request, 'auth/login.html')

            record_attempt(email, True, ip)

            # Update last_login timestamp
            now = timezone.now()
            if utype == 'super_admin':
                SuperAdmin.objects.filter(id=user_obj.id).update(last_login=now)
            elif utype == 'admin':
                Admin.objects.filter(id=user_obj.id).update(last_login=now)
            else:
                User.objects.filter(id=user_obj.id).update(last_login=now)

            request.session['user_id']       = user_obj.id
            request.session['user_type']     = utype
            request.session['full_name']     = build_full_name(user_obj)
            request.session['email']         = user_obj.email
            request.session['role']          = utype if utype != 'user' else user_obj.role
            request.session['profile_image'] = user_obj.profile_image or ''
            assigned_barangay = ''
            if utype == 'user':
                assigned_barangay = getattr(user_obj, 'barangay_text', '') or ''
            request.session['barangay_text'] = assigned_barangay
            request.session['assigned_barangay'] = assigned_barangay

            # Mirror session into pulse_db.sessions (schema.sql custom table)
            session_key = request.session.session_key
            if session_key:
                from datetime import timedelta
                expires = now + timedelta(seconds=settings.SESSION_COOKIE_AGE)
                _, created = PulseSession.objects.get_or_create(
                    id=session_key,
                    defaults={
                        'user_id': user_obj.id,
                        'user_type': utype,
                        'ip_address': ip,
                        'user_agent': (request.META.get('HTTP_USER_AGENT') or '')[:500],
                        'created_at': now,
                        'expires_at': expires,
                        'invalidated': False,
                    },
                )
                if not created:
                    PulseSession.objects.filter(id=session_key).update(
                        user_id=user_obj.id,
                        user_type=utype,
                        ip_address=ip,
                        user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:500],
                        expires_at=expires,
                        invalidated=False,
                    )

            log_system(
                'login_success',
                f'{utype} login: {email}',
                user_role=request.session['role'],
                user_id=user_obj.id,
                module='accounts',
                ip_address=ip,
                request=request,
            )

            # First-login password change — only for regular users, not admins/super_admins
            if utype == 'user' and getattr(user_obj, 'first_login', True):
                request.session['pending_first_login'] = True
                return redirect('first_login_set_password')

            return redirect('dashboard')

        record_attempt(email, False, ip)
        messages.error(request, 'Invalid email or password.')

    return render(request, 'auth/login.html')


# ── Logout ────────────────────────────────────────────────────────

def logout_view(request):
    session_key = request.session.session_key
    if session_key:
        PulseSession.objects.filter(id=session_key).update(invalidated=True)
    request.session.flush()
    messages.success(request, 'You have been logged out.')
    return redirect('login')


# ── First-Login Set Password ──────────────────────────────────────

def first_login_set_password(request):
    """First-login flow: set a new permanent password (admin-created accounts)."""
    if not request.session.get('user_id'):
        return redirect('login')
    if not request.session.get('pending_first_login'):
        return redirect('dashboard')

    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm  = request.POST.get('confirm_password', '')

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return render(request, 'auth/first_login_set_password.html')
        if password != confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/first_login_set_password.html')

        uid = request.session['user_id']
        User.objects.filter(id=uid).update(
            password_hash=hash_password(password),
            first_login=False,
        )

        request.session.pop('pending_first_login', None)

        messages.success(request, 'Password set successfully. Welcome to PULSE.')
        return redirect('dashboard')

    return render(request, 'auth/first_login_set_password.html')
