"""Reconcile stale alerts, epidemic status, and APTAS scores after case closures."""
from django.core.management.base import BaseCommand

from myapp.models import Barangay
from reports.case_state_service import reconcile_barangay_surveillance_state


class Command(BaseCommand):
    help = 'Resolve stale alerts and reset APTAS/epidemic state for barangays with no active cases'

    def add_arguments(self, parser):
        parser.add_argument(
            '--barangay',
            dest='barangay_name',
            help='Reconcile a single barangay by name (default: all barangays)',
        )

    def handle(self, *args, **options):
        barangay_name = (options.get('barangay_name') or '').strip()
        if barangay_name:
            barangays = Barangay.objects.filter(barangay_name__iexact=barangay_name)
        else:
            barangays = Barangay.objects.all().order_by('barangay_name')

        if not barangays.exists():
            self.stderr.write(self.style.ERROR(f'Barangay not found: {barangay_name!r}'))
            return

        for barangay in barangays:
            result = reconcile_barangay_surveillance_state(barangay.id)
            self.stdout.write(
                f'{barangay.barangay_name}: '
                f'resolved={result.get("resolved_alerts", 0)} alerts, '
                f'aptas_resets={result.get("aptas_resets", 0)}, '
                f'active_cases={result.get("total_active_cases", 0)}'
            )
