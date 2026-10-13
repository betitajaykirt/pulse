"""Admin catalog for diseases the office adds before the next model training."""
from types import SimpleNamespace

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from accounts.auth_utils import role_required
from myapp.audit_utils import log_audit
from myapp.models import AddedDisease, Symptom, SurveillanceReport
from reports.disease_catalog import (
    clean_new_symptoms,
    code_for_new_symptom,
    symptom_groups,
    validate_added_disease,
)
from reports.pidsr_schema import PIDSR_SYMPTOM_LABELS, SYNDROMIC_GROUP_TITLES


@role_required('admin', 'super_admin')
def added_diseases_view(request):
    editing = None
    new_symptom_drafts = []
    edit_id = (request.GET.get('edit') or '').strip()
    if edit_id.isdigit():
        editing = AddedDisease.objects.filter(id=int(edit_id)).first()

    if request.method == 'POST':
        action = (request.POST.get('action') or 'save').strip()
        disease_id = (request.POST.get('disease_id') or '').strip()
        current = AddedDisease.objects.filter(id=int(disease_id)).first() if disease_id.isdigit() else None

        if action == 'deactivate' and current:
            current.is_active = False
            current.save(update_fields=['is_active', 'updated_at'])
            _audit(request, 'deactivate_added_disease', current.id, current.name)
            messages.success(request, f'{current.name} is hidden from the confirmation list.')
            return redirect('added_diseases')

        if action == 'activate' and current:
            current.is_active = True
            current.save(update_fields=['is_active', 'updated_at'])
            _audit(request, 'activate_added_disease', current.id, current.name)
            messages.success(request, f'{current.name} is available when confirming a case.')
            return redirect('added_diseases')

        taken = AddedDisease.objects.exclude(pk=getattr(current, 'pk', None)).values_list('name', flat=True)
        posted_names = request.POST.getlist('new_symptom_names')
        posted_groups = request.POST.getlist('new_symptom_groups')
        try:
            with transaction.atomic():
                new_codes = _create_new_symptoms(posted_names, posted_groups)
                name, category, codes = validate_added_disease(
                    request.POST.get('name', ''),
                    request.POST.get('category', ''),
                    request.POST.getlist('symptom_codes') + new_codes,
                    taken_names=taken,
                    extra_allowed_codes=new_codes,
                )
        except ValueError as exc:
            messages.error(request, str(exc))
            editing = SimpleNamespace(
                id=getattr(current, 'id', ''),
                name=request.POST.get('name', ''),
                category=request.POST.get('category', ''),
                symptom_codes=request.POST.getlist('symptom_codes'),
            )
            new_symptom_drafts = [
                {'name': posted_names[index] if index < len(posted_names) else '', 'group': group}
                for index, group in enumerate(posted_groups)
                if (posted_names[index] if index < len(posted_names) else '').strip()
            ]
        else:
            previous_name = current.name if current else ''
            if current:
                current.name = name
                current.category = category
                current.symptom_codes = codes
                current.is_active = True
                current.save()
                if previous_name and previous_name != name:
                    SurveillanceReport.objects.filter(syndrome_type=previous_name).update(syndrome_type=name)
                    SurveillanceReport.objects.filter(suspected_disease=previous_name).update(suspected_disease=name)
                _audit(request, 'update_added_disease', current.id, name)
                messages.success(request, f'{name} was updated. Staff can confirm cases under this name.')
            else:
                created = AddedDisease.objects.create(
                    name=name,
                    category=category,
                    symptom_codes=codes,
                )
                _audit(request, 'create_added_disease', created.id, name)
                messages.success(
                    request,
                    f'{name} was added. It can be confirmed now. The prediction model will not name it until the next training.',
                )
            return redirect('added_diseases')

    label_map = dict(PIDSR_SYMPTOM_LABELS)
    label_map.update(Symptom.objects.values_list('code', 'name'))
    diseases = []
    for row in AddedDisease.objects.all():
        codes = row.symptom_codes if isinstance(row.symptom_codes, list) else []
        diseases.append({
            'row': row,
            'symptom_labels': [label_map.get(code, code) for code in codes],
        })

    selected = []
    if editing and isinstance(editing.symptom_codes, list):
        selected = editing.symptom_codes

    return render(request, 'dashboard/added_diseases.html', {
        'diseases': diseases,
        'editing': editing,
        'symptom_groups': symptom_groups(selected),
        'new_symptom_drafts': new_symptom_drafts,
        'symptom_group_choices': [
            (key, SYNDROMIC_GROUP_TITLES[key]) for key in ('A', 'B', 'C', 'D', 'R', 'N', 'E')
        ],
    })


def _create_new_symptoms(names, groups) -> list[str]:
    existing_names = set(PIDSR_SYMPTOM_LABELS.values())
    existing_names.update(Symptom.objects.values_list('name', flat=True))
    cleaned = clean_new_symptoms(names, groups, existing_names=existing_names)
    taken_codes = set(Symptom.objects.values_list('code', flat=True))
    created_codes = []
    for symptom_name, group in cleaned:
        code = code_for_new_symptom(symptom_name, taken_codes)
        Symptom.objects.create(
            code=code,
            name=symptom_name,
            syndromic_group=group,
            description='',
        )
        taken_codes.add(code)
        created_codes.append(code)
    return created_codes


def _audit(request, action, target_id, name):
    log_audit(
        request.session.get('user_id'),
        request.session.get('user_type') or request.session.get('role') or 'admin',
        action,
        target_id=target_id,
        details=name,
        request=request,
    )
