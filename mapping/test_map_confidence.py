from types import SimpleNamespace

from django.test import SimpleTestCase

from mapping.views import MIN_MAP_ML_CONFIDENCE, should_show_map_pin


class MapPinConfidenceTests(SimpleTestCase):
    def report(self, **overrides):
        values = {
            'status': 'Active',
            'case_classification': 'suspected',
            'validated_by': None,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_unconfirmed_case_below_30_percent_is_hidden(self):
        self.assertFalse(should_show_map_pin(self.report(), 0.299))

    def test_30_percent_boundary_and_missing_confidence_are_visible(self):
        self.assertEqual(MIN_MAP_ML_CONFIDENCE, 0.30)
        self.assertTrue(should_show_map_pin(self.report(), 0.30))
        self.assertTrue(should_show_map_pin(self.report(), None))

    def test_confirmed_case_is_never_hidden_by_old_ml_confidence(self):
        self.assertTrue(
            should_show_map_pin(self.report(status='Confirmed'), 0.10)
        )
        self.assertTrue(
            should_show_map_pin(
                self.report(case_classification='confirmed'),
                0.10,
            )
        )
        self.assertTrue(
            should_show_map_pin(self.report(validated_by=object()), 0.10)
        )
