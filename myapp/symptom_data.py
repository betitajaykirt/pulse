"""Canonical PIDSR symptom seed data — maps ML codes to syndromic groups A–E."""

from reports.pidsr_schema import (
    PIDSR_SYMPTOM_LABELS,
    SYMPTOM_CODE_TO_GROUP,
    SYNDROMIC_GROUP_TITLES,
)


def seed_all_symptoms(verbose=True):
    """
    Idempotently populate the ``Symptom`` table from PIDSR reference data.

    Safe to run on every deploy: uses ``update_or_create`` keyed by ``code``.
    """
    from myapp.models import Symptom

    created = updated = 0
    for code, group in SYMPTOM_CODE_TO_GROUP.items():
        name = PIDSR_SYMPTOM_LABELS.get(code, code.replace('_', ' ').title())
        _, was_created = Symptom.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'syndromic_group': group,
                'description': '',
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    if verbose:
        print(
            f'Symptom seed complete: {created} created, {updated} updated '
            f'({Symptom.objects.count()} total).'
        )

    from reports.pidsr_schema import PIDSR_SYMPTOM_CODES
    removed, _ = Symptom.objects.exclude(code__in=PIDSR_SYMPTOM_CODES).delete()
    if verbose and removed:
        print(f'Removed {removed} legacy symptom catalog row(s).')
    return created, updated
