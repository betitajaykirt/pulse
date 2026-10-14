"""Find cases by patient name after the name column is encrypted."""


def report_ids_for_identity_search(search: str, queryset) -> list[int]:
    needle = (search or '').strip().casefold()
    if not needle:
        return []
    matched = []
    reports = queryset.select_related('patient')
    for report in reports:
        names = [report.patient_name or '']
        patient = getattr(report, 'patient', None)
        if patient is not None:
            names.append(getattr(patient, 'full_name', '') or '')
        if any(needle in name.casefold() for name in names if name):
            matched.append(report.id)
    return matched
