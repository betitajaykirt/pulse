from django.test import SimpleTestCase

from reports.weather_service import _recent_precipitation_mm


class RecentPrecipitationTests(SimpleTestCase):
    def test_sums_trailing_24_hours_instead_of_current_interval_only(self):
        payload = {
            'hourly': {
                'time': [
                    '2026-09-24T21:00',
                    '2026-09-24T22:00',
                    '2026-09-25T15:00',
                    '2026-09-25T21:00',
                    '2026-09-25T22:00',
                ],
                'precipitation': [9.0, 0.4, 2.2, 0.0, 5.0],
            },
        }
        current = {'time': '2026-09-25T21:30', 'precipitation': 0.0}

        self.assertEqual(_recent_precipitation_mm(payload, current), 2.6)

    def test_returns_none_when_hourly_feed_is_missing(self):
        self.assertIsNone(
            _recent_precipitation_mm({}, {'time': '2026-09-25T21:30'})
        )
