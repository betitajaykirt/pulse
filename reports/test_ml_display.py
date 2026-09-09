from types import SimpleNamespace

from django.test import SimpleTestCase

from reports.ml_display import (
    official_disease_label,
    predicted_disease_display,
    report_has_alertable_disease,
    stored_disease_identity_from_ml,
)


def _report(**kwargs):
    defaults = {
        'status': 'Suspected',
        'syndrome_type': 'Inconclusive Syndromic Pattern',
        'suspected_disease': 'Inconclusive Syndromic Pattern',
        'remarks': '',
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class OfficialDiseaseIdentityTests(SimpleTestCase):
    def test_open_case_uses_ml_top_prediction_not_stored_inconclusive(self):
        report = _report(
            remarks='ML Classification: Inconclusive Syndromic Pattern | ML Top Prediction: Dengue Fever | ML Confidence: 15.0%',
        )
        self.assertEqual(official_disease_label(report), 'Dengue Fever')
        self.assertEqual(predicted_disease_display(report)['primary'], 'Dengue Fever')
        self.assertFalse(report_has_alertable_disease(report))

    def test_high_confidence_stored_label_is_official(self):
        report = _report(
            syndrome_type='Leptospirosis',
            suspected_disease='Leptospirosis',
            remarks='ML Classification: Leptospirosis | ML Top Prediction: Leptospirosis | ML Confidence: 72.0%',
        )
        self.assertEqual(official_disease_label(report), 'Leptospirosis')
        self.assertTrue(report_has_alertable_disease(report))

    def test_confirmed_uses_lab_disease(self):
        report = _report(
            status='Confirmed',
            syndrome_type='COVID-19',
            suspected_disease='Influenza-Like Illness',
            remarks='ML Top Prediction: Influenza-Like Illness',
        )
        self.assertEqual(official_disease_label(report), 'COVID-19')
        self.assertTrue(report_has_alertable_disease(report))

    def test_submit_stores_top_prediction_when_gated_inconclusive(self):
        self.assertEqual(
            stored_disease_identity_from_ml({
                'disease_label': 'Inconclusive Syndromic Pattern',
                'top_predicted_disease': 'Dengue Fever',
            }),
            'Dengue Fever',
        )

    def test_submit_keeps_gated_label_when_no_top_prediction(self):
        self.assertEqual(
            stored_disease_identity_from_ml({
                'disease_label': 'Inconclusive Syndromic Pattern',
                'top_predicted_disease': '',
            }),
            'Inconclusive Syndromic Pattern',
        )
