def pulse_globals(request):
    """Inject session user info into every template context."""
    from myapp.barangay_scope import scoped_map_query

    return {
        'session_user_id':   request.session.get('user_id'),
        'session_user_type': request.session.get('user_type'),
        'session_full_name': request.session.get('full_name'),
        'session_role':      request.session.get('role'),
        'session_email':     request.session.get('email'),
        'session_avatar':    request.session.get('profile_image'),
        'session_assigned_barangay': request.session.get('assigned_barangay', ''),
        'scoped_map_query':  scoped_map_query(request),
    }
