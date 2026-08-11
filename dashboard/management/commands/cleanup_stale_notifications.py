from django.core.management.base import BaseCommand

from dashboard.notification_service import prune_stale_app_notifications


class Command(BaseCommand):
    help = 'Remove dashboard popup notifications for closed or resolved surveillance cases.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scan-limit',
            type=int,
            default=500,
            help='How many recent app_notifications rows to evaluate (default: 500).',
        )

    def handle(self, *args, **options):
        removed = prune_stale_app_notifications(scan_limit=options['scan_limit'])
        self.stdout.write(self.style.SUCCESS(f'Removed {removed} stale notification(s).'))
