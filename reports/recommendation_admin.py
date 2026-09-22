"""Admin editing and approval workflow for public-health recommendations."""
import json

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.auth_utils import role_required
from myapp.audit_utils import log_audit, log_system
from myapp.models import RecommendationRevision
from reports.recommendation_repository import (
    clear_approved_recommendation_cache,
)
from reports.recommendation_service import (
    baseline_recommendation_payload,
    validate_recommendation_matrix,
)


ADMIN_ROLES = ('admin', 'super_admin')


def _editor_context(*, payload_text=None, change_summary=''):
    approved = (
        RecommendationRevision.objects.filter(status='approved')
        .order_by('-approved_at', '-id')
        .first()
    )
    pending = list(
        RecommendationRevision.objects.filter(status='pending')
        .order_by('-created_at')[:10]
    )
    source_payload = pending[0].payload if pending else (
        approved.payload if approved else baseline_recommendation_payload()
    )
    return {
        'approved_revision': approved,
        'pending_revisions': pending,
        'payload_text': payload_text or json.dumps(
            source_payload,
            indent=2,
            ensure_ascii=False,
        ),
        'change_summary': change_summary,
    }


@role_required(*ADMIN_ROLES)
def recommendation_editor(request):
    if request.method == 'POST':
        payload_text = request.POST.get('payload', '').strip()
        change_summary = request.POST.get('change_summary', '').strip()
        try:
            payload = json.loads(payload_text)
            validate_recommendation_matrix(payload)
        except (json.JSONDecodeError, ValueError) as exc:
            messages.error(request, f'Recommendation draft was not saved: {exc}')
            return render(
                request,
                'reports/recommendation_editor.html',
                _editor_context(
                    payload_text=payload_text,
                    change_summary=change_summary,
                ),
                status=400,
            )

        revision = RecommendationRevision.objects.create(
            payload=payload,
            status='pending',
            change_summary=change_summary,
            created_by_id=request.session['user_id'],
            created_by_role=request.session.get('role', 'admin'),
        )
        log_audit(
            actor_id=request.session['user_id'],
            actor_type=request.session.get('role', 'admin'),
            action='recommendation_revision_submitted',
            target_id=revision.id,
            details=change_summary or 'Recommendation revision submitted for approval.',
            request=request,
        )
        messages.success(
            request,
            f'Recommendation revision #{revision.id} is pending admin approval.',
        )
        return redirect('recommendation_editor')

    return render(
        request,
        'reports/recommendation_editor.html',
        _editor_context(),
    )


@require_POST
@role_required(*ADMIN_ROLES)
def approve_recommendation_revision(request, revision_id):
    with transaction.atomic():
        revision = get_object_or_404(
            RecommendationRevision.objects.select_for_update(),
            id=revision_id,
            status='pending',
        )
        validate_recommendation_matrix(revision.payload)
        RecommendationRevision.objects.filter(status='approved').update(
            status='superseded'
        )
        revision.status = 'approved'
        revision.approved_by_id = request.session['user_id']
        revision.approved_by_role = request.session.get('role', 'admin')
        revision.approved_at = timezone.now()
        revision.save(update_fields=[
            'status',
            'approved_by_id',
            'approved_by_role',
            'approved_at',
        ])

    clear_approved_recommendation_cache()
    log_audit(
        actor_id=request.session['user_id'],
        actor_type=request.session.get('role', 'admin'),
        action='recommendation_revision_approved',
        target_id=revision.id,
        details=revision.change_summary or 'Recommendation revision approved.',
        request=request,
    )
    log_system(
        activity_type='recommendation_revision_approved',
        log_message=f'Recommendation revision #{revision.id} was approved.',
        user_role=request.session.get('role', 'admin'),
        user_id=request.session['user_id'],
        module='recommendations',
        request=request,
    )
    messages.success(
        request,
        f'Recommendation revision #{revision.id} is now visible to field users.',
    )
    return redirect('recommendation_editor')


@require_POST
@role_required(*ADMIN_ROLES)
def reject_recommendation_revision(request, revision_id):
    revision = get_object_or_404(
        RecommendationRevision,
        id=revision_id,
        status='pending',
    )
    revision.status = 'rejected'
    revision.save(update_fields=['status'])
    log_audit(
        actor_id=request.session['user_id'],
        actor_type=request.session.get('role', 'admin'),
        action='recommendation_revision_rejected',
        target_id=revision.id,
        details=revision.change_summary or 'Recommendation revision rejected.',
        request=request,
    )
    messages.info(request, f'Recommendation revision #{revision.id} was rejected.')
    return redirect('recommendation_editor')
