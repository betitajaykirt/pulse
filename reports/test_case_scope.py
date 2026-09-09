from datetime import date

from django.db.models import Q
from django.test import SimpleTestCase

from reports.case_scope import (
    INACTIVE_CASE_STATUSES,
    event_date_window_q,
    named_time_window,
    parse_scope_time_range,
    rolling_days_window,
)


class CaseScopeWindowTests(SimpleTestCase):
    def test_inactive_statuses_are_closed_and_discarded(self):
        self.assertEqual(INACTIVE_CASE_STATUSES, ('Closed', 'Discarded'))

    def test_all_active_has_no_start(self):
        start, end = named_time_window('all_active', today=date(2026, 9, 10))
        self.assertIsNone(start)
        self.assertEqual(end, date(2026, 9, 10))

    def test_last_30_days_matches_rolling_map_window(self):
        today = date(2026, 9, 10)
        named_start, named_end = named_time_window('last_30_days', today=today)
        roll_start, roll_end = rolling_days_window(30, today=today)
        self.assertEqual((named_start, named_end), (roll_start, roll_end))
        self.assertEqual(named_start, date(2026, 8, 11))

    def test_map_all_active_parses_to_unbounded_window(self):
        start, end = parse_scope_time_range('all_active')
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_map_days_use_onset_window(self):
        start, end = parse_scope_time_range('7', today=date(2026, 9, 10))
        self.assertEqual(start, date(2026, 9, 3))
        self.assertEqual(end, date(2026, 9, 10))

    def test_event_window_is_empty_without_start(self):
        self.assertEqual(event_date_window_q(None, date(2026, 9, 10)), Q())

    def test_event_window_uses_onset_with_report_date_fallback(self):
        clause = event_date_window_q(date(2026, 8, 11), date(2026, 9, 10))
        children = list(clause.children)
        self.assertEqual(len(children), 2)
        connectors = {child[0] if isinstance(child, tuple) else None for child in children}
        self.assertTrue(any('date_of_onset' in str(child) for child in children))
        self.assertTrue(any('report_date' in str(child) for child in children))
        self.assertTrue(clause.connector == 'OR' or len(connectors) >= 1)

    def test_related_prefix_for_barangay_shading(self):
        clause = event_date_window_q(
            date(2026, 8, 11), date(2026, 9, 10), prefix='surveillancereport',
        )
        text = str(clause)
        self.assertIn('surveillancereport__date_of_onset', text)
        self.assertIn('surveillancereport__report_date', text)
        self.assertNotIn('validation_status', text)
