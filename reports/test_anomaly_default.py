from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from reports.aptas_service import normalize_anomaly_score, raw_anomaly_for_report
from reports.risk_service import _raw_anomaly_for_report


class MissingAnomalyScoreTests(SimpleTestCase):
    def test_stored_score_is_used(self):
        report = SimpleNamespace(ml_anomaly_score=Decimal('-0.12'), is_anomaly=True)
        self.assertEqual(raw_anomaly_for_report(report), -0.12)

    def test_missing_score_is_not_invented_as_high(self):
        report = SimpleNamespace(ml_anomaly_score=None, is_anomaly=True)
        self.assertIsNone(raw_anomaly_for_report(report))
        self.assertIsNone(_raw_anomaly_for_report(report, is_anomaly=True))

    def test_boolean_anomaly_flag_does_not_map_to_075(self):
        report = SimpleNamespace(ml_anomaly_score=None, is_anomaly=True)
        raw = _raw_anomaly_for_report(report, is_anomaly=True)
        self.assertNotEqual(raw, 0.75)
        self.assertEqual(normalize_anomaly_score(raw), 0.0)

    def test_normalize_none_is_zero_not_high(self):
        self.assertEqual(normalize_anomaly_score(None), 0.0)
        self.assertLess(normalize_anomaly_score(None), 0.50)
