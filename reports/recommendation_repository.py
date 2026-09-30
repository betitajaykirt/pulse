"""Persistence boundary for approved recommendation content."""
from django.db import OperationalError, ProgrammingError

from myapp.models import RecommendationRevision
from reports.recommendation_service import (
    recommendation_matrix,
    validate_recommendation_matrix,
)


def matrix_from_payload(payload: dict) -> dict[str, dict]:
    validate_recommendation_matrix(payload)
    return {row['label']: row for row in payload['diseases']}


def _latest_approved_payload():
    try:
        return (
            RecommendationRevision.objects
            .filter(status='approved')
            .order_by('-approved_at', '-id')
            .values_list('payload', flat=True)
            .first()
        )
    except (OperationalError, ProgrammingError):
        # Keeps deploy-time checks and the first migration safe.
        return None


def approved_recommendation_matrix() -> dict[str, dict]:
    """Admin editing catalog: latest approval, or the shipped baseline."""
    payload = _latest_approved_payload()
    if not payload:
        return recommendation_matrix()
    return matrix_from_payload(payload)


def field_recommendation_matrix() -> dict[str, dict]:
    """Recommendations released to BHWs and other non-admin roles."""
    try:
        released = {
            disease
            for disease in RecommendationRevision.objects.filter(
                approved_at__isnull=False,
            ).exclude(scope_disease='').values_list('scope_disease', flat=True)
            if disease
        }
    except (OperationalError, ProgrammingError):
        return {}
    if not released:
        return {}
    source = approved_recommendation_matrix()
    return {
        label: row
        for label, row in source.items()
        if label in released
    }


def clear_approved_recommendation_cache() -> None:
    """Compatibility hook; database reads are intentionally not process-cached."""
    return None
