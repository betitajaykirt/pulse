"""Seed dummy surveillance reports so sample pins appear on the geospatial map."""
from __future__ import annotations

import random
from collections import defaultdict
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models.signals import pre_delete

from myapp.models import (
    Barangay,
    PatientCase,
    RiskAssessment,
    SurveillanceReport,
    SurveillanceSession,
    User,
)
from reports.pidsr_schema import DISEASE_LABELS
from reports.signals import reconcile_after_report_delete

DEMO_MARKER = '[PULSE-DEMO]'

FIRST_NAMES = [
    'Ana', 'Ben', 'Carlo', 'Diana', 'Elena', 'Felix', 'Gina', 'Hugo',
    'Ivy', 'Jose', 'Kara', 'Leo', 'Mia', 'Nico', 'Olive', 'Paolo',
    'Quin', 'Rosa', 'Sam', 'Tess', 'Uly', 'Vera', 'Walt', 'Yna',
]
LAST_NAMES = [
    'Santos', 'Reyes', 'Cruz', 'Bautista', 'Garcia', 'Lopez', 'Ramos',
    'Flores', 'Mendoza', 'Castillo', 'Navarro', 'Soriano', 'Pineda', 'Diaz',
]

# 27 PIDSR diseases across 20 of 24 barangays (clusters for a few high-visibility diseases).
CASE_PLAN = [
    ('Poblacion', 'Dengue Fever', 4),
    ('Ma-ao', 'Measles', 3),
    ('Calumangan', 'Leptospirosis', 3),
    ('Taloc', 'COVID-19', 2),
    ('Lag-asan', 'Cholera', 2),
    ('Pacol', 'Typhoid and Paratyphoid Fever', 2),
    ('Abuanan', 'Hand, Foot, and Mouth Disease', 2),
    ('Busay', 'Influenza-Like Illness', 2),
    ('Caridad', 'Pertussis', 2),
    ('Dulao', 'Rabies', 1),
    ('Dulao', 'Malaria', 1),
    ('Ilijan', 'Anthrax', 1),
    ('Ilijan', 'Acute Flaccid Paralysis', 1),
    ('Mailum', 'Diphtheria', 1),
    ('Mailum', 'Acute Encephalitis Syndrome', 1),
    ('Sagasa', 'Meningococcal Disease', 1),
    ('Sagasa', 'Acute Hemorrhagic Fever Syndrome', 1),
    ('Tabunan', 'Acute Viral Hepatitis', 1),
    ('Tabunan', 'Bacterial Meningitis', 1),
    ('Napoles', 'Middle East Respiratory Syndrome', 1),
    ('Napoles', 'Severe Acute Respiratory Syndrome', 1),
    ('Sampinit', 'Neonatal Tetanus', 1),
    ('Sampinit', 'Non-Neonatal Tetanus', 1),
    ('Balingasag', 'Adverse Event Following Immunization', 1),
    ('Balingasag', 'Human Avian Influenza', 1),
    ('Binubuhan', 'Paralytic Shellfish Poisoning', 1),
    ('Binubuhan', 'Acute Bloody Diarrhea', 1),
    ('Alianza', 'Dengue Fever', 1),
    ('Malingin', 'Influenza-Like Illness', 1),
]

SYMPTOMS_BY_DISEASE = {
    'Acute Flaccid Paralysis': ['acute_flaccid_paralysis', 'marked_weakness', 'fever'],
    'Adverse Event Following Immunization': ['fever', 'injection_site_reaction', 'rash'],
    'Anthrax': ['painless_skin_lesion', 'fever', 'chest_pain'],
    'COVID-19': ['fever', 'dry_cough', 'loss_of_smell_taste'],
    'Hand, Foot, and Mouth Disease': ['vesicle_mouth_ulcers', 'palmar_plantar_vesicles', 'fever'],
    'Human Avian Influenza': ['fever', 'dry_cough', 'trouble_breathing'],
    'Measles': ['fever', 'rash', 'koplik_spots', 'runny_nose'],
    'Meningococcal Disease': ['fever', 'neck_stiffness', 'headache', 'petechiae'],
    'Middle East Respiratory Syndrome': ['fever', 'dry_cough', 'trouble_breathing'],
    'Neonatal Tetanus': ['trismus', 'muscle_spasms', 'severe_restlessness'],
    'Paralytic Shellfish Poisoning': ['tingling_numbness', 'vomiting', 'marked_weakness'],
    'Rabies': ['hydrophobia', 'muscle_spasms', 'altered_consciousness'],
    'Severe Acute Respiratory Syndrome': ['fever', 'dry_cough', 'trouble_breathing'],
    'Acute Bloody Diarrhea': ['bloody_diarrhea', 'fever', 'abdominal_discomfort'],
    'Acute Encephalitis Syndrome': ['fever', 'altered_consciousness', 'seizure'],
    'Acute Hemorrhagic Fever Syndrome': ['fever', 'gum_bleeding', 'petechiae'],
    'Acute Viral Hepatitis': ['jaundice', 'right_upper_quadrant_pain', 'anorexia'],
    'Bacterial Meningitis': ['fever', 'neck_stiffness', 'headache'],
    'Cholera': ['loose_watery_stool', 'vomiting', 'thirst'],
    'Dengue Fever': ['fever', 'headache', 'rash', 'gum_bleeding'],
    'Diphtheria': ['sore_throat', 'bull_neck', 'fever'],
    'Influenza-Like Illness': ['fever', 'dry_cough', 'body_malaise', 'headache'],
    'Leptospirosis': ['fever', 'myalgia', 'conjunctival_suffusion', 'jaundice'],
    'Malaria': ['fever', 'chills', 'diaphoresis', 'headache'],
    'Non-Neonatal Tetanus': ['trismus', 'muscle_spasms', 'neck_stiffness'],
    'Pertussis': ['cough_paroxysms', 'post_tussive_vomiting', 'runny_nose'],
    'Typhoid and Paratyphoid Fever': ['fever', 'abdominal_discomfort', 'constipation', 'headache'],
}


def _symptoms_for(disease: str) -> list[str]:
    return list(SYMPTOMS_BY_DISEASE.get(disease) or ['fever', 'body_malaise'])


def _age_for(disease: str, rng: random.Random) -> int:
    if disease == 'Neonatal Tetanus':
        return 0
    if disease in {'Hand, Foot, and Mouth Disease', 'Measles', 'Pertussis'}:
        return rng.randint(1, 10)
    if disease == 'Non-Neonatal Tetanus':
        return rng.randint(18, 55)
    return rng.randint(8, 72)


def _jitter(lat: float, lng: float, rng: random.Random) -> tuple[float, float]:
    return (
        round(lat + rng.uniform(-0.004, 0.004), 7),
        round(lng + rng.uniform(-0.004, 0.004), 7),
    )


def _submitter_for(barangay_name: str):
    for role in ('barangay_health_worker', 'catchment_nurse'):
        user = User.objects.filter(
            role=role,
            barangay_text__iexact=barangay_name,
            status='active',
        ).first()
        if user:
            return user
    return User.objects.filter(status='active').order_by('id').first()


def _purge_demo_reports():
    """Delete demo rows without firing APTAS/threshold reconciliation."""
    pre_delete.disconnect(reconcile_after_report_delete, sender=SurveillanceReport)
    try:
        demo_qs = SurveillanceReport.objects.filter(remarks__icontains=DEMO_MARKER)
        report_ids = list(demo_qs.values_list('id', flat=True))
        session_ids = list(demo_qs.exclude(session_id=None).values_list('session_id', flat=True))
        if report_ids:
            RiskAssessment.objects.filter(report_id__in=report_ids).delete()
            PatientCase.objects.filter(surveillance_report_id__in=report_ids).delete()
        deleted, _ = demo_qs.delete()
        if session_ids:
            SurveillanceSession.objects.filter(id__in=session_ids).delete()
        return deleted
    finally:
        pre_delete.connect(reconcile_after_report_delete, sender=SurveillanceReport)


class Command(BaseCommand):
    help = 'Create dummy PIDSR case reports across Bago barangays for map demos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--purge',
            action='store_true',
            help='Delete previously seeded [PULSE-DEMO] reports instead of creating new ones.',
        )

    def handle(self, *args, **options):
        from reports.batch_service import save_batch_submission

        self.stdout.write('Starting dummy report seed...')
        self.stdout.flush()

        if options.get('purge'):
            deleted = _purge_demo_reports()
            self.stdout.write(self.style.WARNING(f'Deleted {deleted} demo report(s).'))
            return

        unknown = [label for _, label, _ in CASE_PLAN if label not in DISEASE_LABELS]
        if unknown:
            raise SystemExit(f'Unknown disease labels: {unknown}')

        existing_count = SurveillanceReport.objects.filter(remarks__icontains=DEMO_MARKER).count()
        if existing_count:
            self.stdout.write(self.style.WARNING(
                f'Removing {existing_count} existing demo report(s) before reseeding.'
            ))
            self.stdout.flush()
            _purge_demo_reports()

        rng = random.Random(20260902)
        barangays = {b.barangay_name: b for b in Barangay.objects.all()}
        created = 0
        skipped = []
        grouped = defaultdict(list)

        for barangay_name, disease, count in CASE_PLAN:
            row = barangays.get(barangay_name)
            if not row:
                skipped.append(barangay_name)
                continue
            grouped[barangay_name].append((disease, count, row))

        for barangay_name, jobs in grouped.items():
            submitter = _submitter_for(barangay_name)
            if not submitter:
                self.stderr.write(self.style.ERROR('No user account available to submit reports.'))
                return
            barangay = jobs[0][2]
            lat = float(barangay.latitude) if barangay.latitude is not None else 10.5376
            lng = float(barangay.longitude) if barangay.longitude is not None else 122.8380
            cases = []
            for disease, count, _row in jobs:
                for _ in range(count):
                    onset = date.today() - timedelta(days=rng.randint(0, 12))
                    pin_lat, pin_lng = _jitter(lat, lng, rng)
                    first = rng.choice(FIRST_NAMES)
                    last = rng.choice(LAST_NAMES)
                    purok = f'Purok {rng.randint(1, 8)}, {barangay_name}'
                    cases.append({
                        'first_name': first,
                        'last_name': last,
                        'patient_name': f'{first} {last}',
                        'barangay': barangay.id,
                        'purok_street': purok,
                        'detailed_address': purok,
                        'latitude': pin_lat,
                        'longitude': pin_lng,
                        'date_of_onset': onset.isoformat(),
                        'age': _age_for(disease, rng),
                        'sex': rng.choice(['Male', 'Female']),
                        'symptoms': _symptoms_for(disease),
                    })
            self.stdout.write(
                f'Submitting {len(cases)} case(s) for {barangay_name} via Isolation Forest + Random Forest + APTAS...'
            )
            self.stdout.flush()
            session, reports = save_batch_submission(
                payload={'cases': cases},
                submitted_by_id=submitter.id,
                locked_barangay=barangay,
            )
            for report in reports:
                remarks = (report.remarks or '').strip()
                if DEMO_MARKER not in remarks:
                    report.remarks = f'{remarks} | {DEMO_MARKER}' if remarks else DEMO_MARKER
                    report.save(update_fields=['remarks'])
            created += len(reports)
            scores = ', '.join(
                str(r.ml_anomaly_score if r.ml_anomaly_score is not None else '—')
                for r in reports
            )
            self.stdout.write(
                f'{barangay_name}: {len(reports)} case(s) session #{session.id} '
                f'anomaly=[{scores}] via {submitter.email}'
            )
            self.stdout.flush()

        if skipped:
            self.stdout.write(self.style.WARNING(
                'Skipped missing barangays: ' + ', '.join(sorted(set(skipped)))
            ))
        self.stdout.write(self.style.SUCCESS(
            f'Created {created} dummy reports across {len(grouped)} barangays '
            'through Isolation Forest, Random Forest, and APTAS. '
            'Open Geospatial Map (last 30 days) to view the pins.'
        ))
