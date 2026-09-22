from datetime import datetime, timezone as datetime_timezone

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from myapp.date_utils import (
    format_display_date,
    format_display_datetime,
    parse_user_date,
)


@override_settings(USE_TZ=True, TIME_ZONE='Asia/Manila')
class DateDisplayTimezoneTests(SimpleTestCase):
    def test_utc_timestamp_is_displayed_in_manila_time(self):
        stored_timestamp = datetime(
            2026, 8, 31, 16, 18, tzinfo=datetime_timezone.utc
        )

        with timezone.override('Asia/Manila'):
            self.assertEqual(
                format_display_datetime(stored_timestamp),
                '09/01/2026 12:18 AM',
            )
            self.assertEqual(format_display_date(stored_timestamp), '09/01/2026')
            self.assertEqual(
                parse_user_date(stored_timestamp).isoformat(),
                '2026-09-01',
            )
