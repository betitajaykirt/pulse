from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from reports.risk_service import _resolve_trigger_code, alert_trigger_label


class AlertTriggerSourceTests(SimpleTestCase):
    def _resolve(self, anomaly=0.21, is_anomaly=False, active_cases=1, category_i=False):
        assessment = SimpleNamespace(anomaly_score=anomaly)
        with patch('reports.risk_service.report_is_category_i_high_confidence', return_value=category_i):
            return _resolve_trigger_code(
                assessment, object(), is_anomaly=is_anomaly, active_cases=active_cases,
            )

    def test_single_category_i_case_is_not_a_spatial_cluster(self):
        code = self._resolve(category_i=True, active_cases=1)
        self.assertEqual(code, 'category_i_signal')
        self.assertEqual(alert_trigger_label(code), 'Category I High-Confidence Case')

    def test_single_case_without_signal_is_not_a_spatial_cluster(self):
        self.assertNotEqual(self._resolve(active_cases=1), 'spatial_cluster')

    def test_multiple_cases_are_a_spatial_cluster(self):
        self.assertEqual(self._resolve(active_cases=3), 'spatial_cluster')

    def test_high_anomaly_wins(self):
        self.assertEqual(self._resolve(anomaly=0.8, category_i=True, active_cases=3), 'aptas_anomaly')
