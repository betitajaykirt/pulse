"""Admin editing and approval workflow for public-health recommendations."""
from copy import deepcopy
import json

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.auth_utils import role_required
from myapp.audit_utils import log_audit, log_system
from myapp.models import RecommendationRevision
from reports.recommendation_repository import (
    clear_approved_recommendation_cache,
)
from reports.recommendation_service import (
    baseline_recommendation_payload,
    canonical_disease_name,
    normalize_case_status,
    validate_recommendation_matrix,
)


ADMIN_ROLES = ('admin', 'super_admin')


def _approved_payload():
    approved = (
        RecommendationRevision.objects.filter(status='approved')
        .order_by('-approved_at', '-id')
        .first()
    )
    return deepcopy(
        approved.payload if approved else baseline_recommendation_payload()
    )


def _disease_row(payload, disease):
    return next(
        (row for row in payload['diseases'] if row['label'] == disease),
        None,
    )


def _combined_action(actions):
    unique = {}
    for action in actions:
        unique.setdefault(action.get('code'), action)
    actions = list(unique.values())
    targets = []
    for action in actions:
        for target in action.get('targets') or []:
            if target not in targets:
                targets.append(target)
    return {
        'en': ' '.join(
            action.get('en', '').strip() for action in actions
            if action.get('en', '').strip()
        ),
        'local': ' '.join(
            action.get('local', '').strip() for action in actions
            if action.get('local', '').strip()
        ),
        'targets': targets,
    }


@require_http_methods(['GET', 'POST'])
@role_required(*ADMIN_ROLES)
def recommendation_card(request):
    disease = canonical_disease_name(
        request.GET.get('disease') if request.method == 'GET' else ''
    )
    state = normalize_case_status(
        request.GET.get('state') if request.method == 'GET' else ''
    )
    is_cluster = (
        request.GET.get('cluster') == 'true'
        if request.method == 'GET'
        else False
    )

    if request.method == 'POST':
        try:
            submitted = json.loads(request.body.decode('utf-8'))
            if not isinstance(submitted, dict):
                raise ValueError('Recommendation request must be a JSON object.')
            disease = canonical_disease_name(submitted.get('disease'))
            if not disease:
                raise ValueError('Select a supported monitored disease.')
            state = normalize_case_status(submitted.get('state'))
            is_cluster = bool(submitted.get('is_cluster'))
            recommendation = submitted.get('recommendation')
            if not isinstance(recommendation, dict):
                raise ValueError('Recommendation details are required.')

            payload = _approved_payload()
            row = _disease_row(payload, disease)
            if not row:
                raise ValueError('Recommendation disease was not found.')
            existing = row['actions'].get(state) or []
            recommendation = {
                'code': (
                    existing[0].get('code')
                    if existing and existing[0].get('code')
                    else f'{disease.casefold().replace(" ", "_")}_{state}_recommendation'
                ),
                'en': str(recommendation.get('en') or '').strip(),
                'local': str(recommendation.get('local') or '').strip(),
                'targets': [
                    str(target).strip()
                    for target in recommendation.get('targets') or []
                    if str(target).strip()
                ],
            }
            row['actions'][state] = [recommendation]
            if is_cluster:
                row['actions']['cluster'] = [deepcopy(recommendation)]
            validate_recommendation_matrix(payload)
        except (json.JSONDecodeError, ValueError) as exc:
            return JsonResponse(
                {'ok': False, 'error': str(exc)},
                status=400,
            )

        RecommendationRevision.objects.filter(
            status='pending',
            scope_disease=disease,
        ).update(status='superseded')
        revision = RecommendationRevision.objects.create(
            payload=payload,
            scope_disease=disease,
            status='pending',
            change_summary=f'Updated map recommendation card for {disease}.',
            created_by_id=request.session['user_id'],
            created_by_role=request.session.get('role', 'admin'),
        )
        log_audit(
            actor_id=request.session['user_id'],
            actor_type=request.session.get('role', 'admin'),
            action='recommendation_revision_submitted',
            target_id=revision.id,
            details=revision.change_summary,
            request=request,
        )
        return JsonResponse({
            'ok': True,
            'revision_id': revision.id,
            'message': (
                f'{disease} changes were saved and are pending admin approval.'
            ),
        })

    if not disease:
        return JsonResponse(
            {'ok': False, 'error': 'Select a supported monitored disease.'},
            status=400,
        )
    pending = (
        RecommendationRevision.objects
        .filter(status='pending', scope_disease=disease)
        .order_by('-created_at', '-id')
        .first()
    )
    source_payload = pending.payload if pending else _approved_payload()
    row = _disease_row(source_payload, disease)
    if not row:
        return JsonResponse(
            {'ok': False, 'error': 'Recommendation disease was not found.'},
            status=404,
        )
    actions = list(row['actions'][state])
    if is_cluster:
        actions += list(row['actions']['cluster'])
    return JsonResponse({
        'ok': True,
        'disease': disease,
        'category': row['category'],
        'state': state,
        'is_cluster': is_cluster,
        'recommendation': _combined_action(actions),
        'pending_revision_id': pending.id if pending else None,
    })


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
        if revision.scope_disease:
            merged_payload = _approved_payload()
            edited_row = _disease_row(
                revision.payload,
                revision.scope_disease,
            )
            current_row = _disease_row(
                merged_payload,
                revision.scope_disease,
            )
            if not edited_row or not current_row:
                return JsonResponse(
                    {'ok': False, 'error': 'Recommendation disease was not found.'},
                    status=400,
                )
            current_row.clear()
            current_row.update(deepcopy(edited_row))
            validate_recommendation_matrix(merged_payload)
            revision.payload = merged_payload
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
            'payload',
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
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'message': (
                f'{revision.scope_disease or "Recommendation"} is approved and '
                'now visible to field users.'
            ),
        })
    return redirect('map_view')


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
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'message': 'Pending changes were rejected.'})
    return redirect('map_view')
