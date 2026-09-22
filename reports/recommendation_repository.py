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


def approved_recommendation_matrix() -> dict[str, dict]:
    """Return only approved content, falling back to the shipped baseline."""
    try:
        payload = (
            RecommendationRevision.objects
            .filter(status='approved')
            .order_by('-approved_at', '-id')
            .values_list('payload', flat=True)
            .first()
        )
    except (OperationalError, ProgrammingError):
        # Keeps deploy-time checks and the first migration safe.
        payload = None

    if not payload:
        return recommendation_matrix()
    return matrix_from_payload(payload)


def clear_approved_recommendation_cache() -> None:
    """Compatibility hook; database reads are intentionally not process-cached."""
    return None
