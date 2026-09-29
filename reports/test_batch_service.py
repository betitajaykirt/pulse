from django.test import SimpleTestCase

from reports.batch_service import _numeric_score


class BatchMlFallbackTests(SimpleTestCase):
    def test_none_confidence_uses_zero(self):
        self.assertEqual(_numeric_score(None), 0.0)

    def test_numeric_confidence_is_preserved(self):
        self.assertEqual(_numeric_score('0.72'), 0.72)

    def test_invalid_anomaly_score_uses_default(self):
        self.assertEqual(_numeric_score(''), 0.0)
