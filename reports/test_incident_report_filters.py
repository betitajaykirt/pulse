from datetime import date, timedelta

from django.test import SimpleTestCase, override_settings

from reports.views import _incident_report_date_bound


@override_settings(USE_TZ=True, TIME_ZONE='Asia/Manila')
class IncidentReportDateFilterTests(SimpleTestCase):
    def test_date_bound_is_midnight_in_the_configured_timezone(self):
        bound = _incident_report_date_bound(date(2026, 9, 1))

        self.assertEqual(bound.date(), date(2026, 9, 1))
        self.assertEqual((bound.hour, bound.minute, bound.second), (0, 0, 0))
        self.assertEqual(bound.utcoffset(), timedelta(hours=8))

    def test_end_date_uses_the_following_midnight(self):
        selected_end = date(2026, 9, 22)
        exclusive_end = _incident_report_date_bound(
            selected_end + timedelta(days=1)
        )

        self.assertEqual(exclusive_end.date(), date(2026, 9, 23))
        self.assertEqual((exclusive_end.hour, exclusive_end.minute), (0, 0))
