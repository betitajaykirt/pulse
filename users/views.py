import secrets
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from accounts.auth_utils import role_required, hash_password, build_full_name
from myapp.models import User, Barangay


@role_required('admin', 'super_admin')
def index(request):
    search = request.GET.get('search', '').strip()
    if search:
        users = User.objects.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(role__icontains=search) |
            Q(status__icontains=search)
        ).order_by('-created_at')
    else:
        users = User.objects.all().order_by('-created_at')

    barangays = Barangay.objects.all().order_by('barangay_name')

    return render(request, 'users/index.html', {
        'users': users,
        'search': search,
        'barangays': barangays,
    })


@role_required('admin', 'super_admin')
def create(request):
    if request.method != 'POST':
        return redirect('users_index')

    first    = request.POST.get('first_name', '').strip()
    last     = request.POST.get('last_name', '').strip()
    middle   = request.POST.get('middle_initial', '').strip()
    suffix   = request.POST.get('suffix', '').strip()
    bdate    = request.POST.get('birthdate', '').strip()
    email    = request.POST.get('email', '').strip()
    role     = request.POST.get('role', '').strip()
    password = request.POST.get('password', '')
    barangay = request.POST.get('barangay_text', '').strip()
    contact  = request.POST.get('contact_number', '').strip()

    valid_roles = ['encoder', 'health_officer', 'surveillance_officer', 'barangay_health_worker']
    errors = []
    if not first:  errors.append('First name required.')
    if not last:   errors.append('Last name required.')
    if not email:  errors.append('Email required.')
    if role not in valid_roles: errors.append('Invalid role.')
    if len(password) < 8: errors.append('Password must be at least 8 characters.')
    if role in ('barangay_health_worker', 'encoder', 'surveillance_officer', 'health_officer') and not barangay:
        errors.append('Barangay is required for the selected role.')

    if errors:
        for e in errors:
            messages.error(request, e)
        return redirect('users_index')

    if User.objects.filter(email=email).exists():
        messages.error(request, 'Email already exists.')
        return redirect('users_index')

    username = f"{first.lower()}.{last.lower()}.{secrets.token_hex(4)}"
    now = timezone.now()
    User.objects.create(
        username=username,
        first_name=first,
        last_name=last,
        middle_name=middle or None,
        suffix=suffix or None,
        birthdate=bdate or None,
        email=email,
        password_hash=hash_password(password),
        role=role,
        status='active',
        barangay_text=barangay or None,
        contact_number=contact or None,
        created_at=now,
        updated_at=now,
    )
    messages.success(request, f'Account for {first} {last} ({role}) created.')
    return redirect('users_index')


@role_required('admin', 'super_admin')
def update_role(request, user_id):
    if request.method != 'POST':
        return redirect('users_index')

    new_role = request.POST.get('role', '').strip()
    valid_roles = ['encoder', 'health_officer', 'surveillance_officer', 'barangay_health_worker']
    if new_role not in valid_roles:
        messages.error(request, 'Invalid role.')
        return redirect('users_index')

    user = User.objects.filter(id=user_id).first()
    if not user:
        messages.error(request, 'User not found.')
        return redirect('users_index')

    User.objects.filter(id=user_id).update(role=new_role)
    messages.success(request, f'Role updated to {new_role}.')
    return redirect('users_index')


@role_required('admin', 'super_admin')
def deactivate(request, user_id):
    if request.method != 'POST':
        return redirect('users_index')

    if user_id == request.session.get('user_id'):
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('users_index')

    user = User.objects.filter(id=user_id).first()
    if not user:
        messages.error(request, 'User not found.')
        return redirect('users_index')

    User.objects.filter(id=user_id).update(status='inactive')
    messages.success(request, f"{build_full_name(user)}'s account deactivated.")
    return redirect('users_index')


@role_required('admin', 'super_admin')
def reactivate(request, user_id):
    if request.method != 'POST':
        return redirect('users_index')

    user = User.objects.filter(id=user_id).first()
    if not user:
        messages.error(request, 'User not found.')
        return redirect('users_index')

    User.objects.filter(id=user_id).update(status='active')
    messages.success(request, f"{build_full_name(user)}'s account reactivated.")
    return redirect('users_index')
