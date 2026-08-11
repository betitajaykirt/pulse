import os
import secrets
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import FileResponse, Http404
from django.conf import settings
from myapp.models import SuperAdmin, Admin, User
from accounts.identity_utils import (
    contact_in_use,
    email_in_use,
    is_valid_contact_number,
    normalize_contact_number,
    normalize_email,
)
from .auth_utils import login_required, get_current_user, verify_password, hash_password


@login_required
def profile_show(request):
    user = get_current_user(request)
    return render(request, 'profile/show.html', {'user': user})


@login_required
def profile_update(request):
    if request.method != 'POST':
        return redirect('profile')

    uid   = request.session['user_id']
    utype = request.session.get('user_type', 'user')
    email   = normalize_email(request.POST.get('email', ''))
    contact = request.POST.get('contact_number', '').strip()
    contact_normalized = normalize_contact_number(contact)

    if not email:
        messages.error(request, 'Email is required.')
        return redirect('profile')

    if email_in_use(email, exclude_user_type=utype, exclude_id=uid):
        messages.error(request, 'That email is already in use.')
        return redirect('profile')

    if contact:
        if not is_valid_contact_number(contact):
            messages.error(request, 'Enter a valid contact number (at least 10 digits).')
            return redirect('profile')
        if contact_in_use(contact, exclude_user_type=utype, exclude_id=uid):
            messages.error(request, 'That contact number is already in use.')
            return redirect('profile')

    if utype == 'user':
        User.objects.filter(id=uid).update(email=email, contact_number=contact_normalized or None)
    elif utype == 'admin':
        Admin.objects.filter(id=uid).update(email=email, contact_number=contact_normalized or None)
    elif utype == 'super_admin':
        SuperAdmin.objects.filter(id=uid).update(email=email, contact_number=contact_normalized or None)

    request.session['email'] = email
    messages.success(request, 'Profile updated.')
    return redirect('profile')


@login_required
def profile_upload_photo(request):
    if request.method != 'POST':
        return redirect('profile')

    uid   = request.session['user_id']
    utype = request.session.get('user_type', 'user')
    photo = request.FILES.get('profile_photo')

    if not photo:
        messages.error(request, 'No file selected.')
        return redirect('profile')

    if photo.size > 2 * 1024 * 1024:
        messages.error(request, 'Photo must be under 2 MB.')
        return redirect('profile')

    if photo.content_type not in ('image/jpeg', 'image/png', 'image/webp'):
        messages.error(request, 'Only JPEG, PNG, or WebP images accepted.')
        return redirect('profile')

    ext = {'image/png': 'png', 'image/webp': 'webp'}.get(photo.content_type, 'jpg')
    filename = f'avatar_{uid}_{secrets.token_hex(6)}.{ext}'
    avatar_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
    os.makedirs(avatar_dir, exist_ok=True)

    # Delete old profile image if exists
    user = get_current_user(request)
    if user and getattr(user, 'profile_image', None):
        old = os.path.join(avatar_dir, os.path.basename(user.profile_image))
        if os.path.exists(old):
            try:
                os.unlink(old)
            except Exception:
                pass

    with open(os.path.join(avatar_dir, filename), 'wb') as f:
        for chunk in photo.chunks():
            f.write(chunk)

    if utype == 'super_admin':
        SuperAdmin.objects.filter(id=uid).update(profile_image=filename)
    elif utype == 'admin':
        Admin.objects.filter(id=uid).update(profile_image=filename)
    else:
        User.objects.filter(id=uid).update(profile_image=filename)

    request.session['profile_image'] = filename
    messages.success(request, 'Profile photo updated.')
    return redirect('profile')


@login_required
def serve_avatar(request, filename):
    path = os.path.join(settings.MEDIA_ROOT, 'avatars', os.path.basename(filename))
    if not os.path.exists(path):
        raise Http404
    return FileResponse(open(path, 'rb'))
