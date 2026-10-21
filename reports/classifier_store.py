"""Save and load the nightly-trained Random Forest."""
from __future__ import annotations

import pickle
import zlib
from typing import Optional, Tuple

from django.db import OperationalError, ProgrammingError, transaction

from reports.models import ClassifierModel


def pack_model(classifier, label_encoder) -> bytes:
    return zlib.compress(pickle.dumps((classifier, label_encoder), protocol=4), level=6)


def unpack_model(payload) -> Tuple[object, object]:
    # The payload is written only by our own retrain job into our own database.
    return pickle.loads(zlib.decompress(bytes(payload)))  # noqa: S301


def active_model_id() -> Optional[int]:
    try:
        return (
            ClassifierModel.objects.filter(is_active=True)
            .order_by('-created_at', '-id')
            .values_list('id', flat=True)
            .first()
        )
    except (OperationalError, ProgrammingError):
        return None


def load_active_model() -> Optional[Tuple[int, object, object]]:
    """Return ``(model_id, classifier, label_encoder)`` for the active row, if any."""
    try:
        row = ClassifierModel.objects.filter(is_active=True).order_by('-created_at', '-id').first()
    except (OperationalError, ProgrammingError):
        return None
    if row is None:
        return None
    classifier, encoder = unpack_model(row.payload)
    return row.id, classifier, encoder


@transaction.atomic
def save_active_model(classifier, label_encoder, *, accuracy, reference_accuracy, base_rows, live_rows, notes=''):
    """Store a new model and make it the only active one."""
    ClassifierModel.objects.filter(is_active=True).update(is_active=False)
    return ClassifierModel.objects.create(
        is_active=True,
        accuracy=accuracy,
        reference_accuracy=reference_accuracy,
        base_rows=base_rows,
        live_rows=live_rows,
        notes=notes[:255],
        payload=pack_model(classifier, label_encoder),
    )
