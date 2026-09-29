from unittest.mock import patch

import pandas as pd
from django.test import SimpleTestCase

from reports.prediction_service import analyze_patient_case


class PredictionResilienceTests(SimpleTestCase):
    @patch('reports.prediction_service.train_and_classify_result')
    @patch('reports.prediction_service._get_outbreak_model')
    @patch('myapp.models.SurveillanceReport.objects')
    def test_anomaly_failure_does_not_discard_disease_prediction(
        self,
        report_objects,
        outbreak_model,
        classify,
    ):
        report_objects.filter.return_value.exclude.return_value.count.return_value = 0
        outbreak_model.side_effect = RuntimeError('temporary screening failure')
        classify.return_value = {
            'disease_label': 'Dengue Fever',
            'top_predicted_disease': 'Dengue Fever',
            'classification_confidence': 0.829,
            'secondary_predicted_disease': '',
            'secondary_classification_confidence': None,
            'has_multiple_probable': False,
            'exposure_gated': False,
        }

        result = analyze_patient_case(
            age=22,
            sex='Male',
            symptoms=['fever', 'headache', 'reticular_pain', 'myalgia'],
            barangay_name='Poblacion',
            train_df=pd.DataFrame(),
            outbreak_train_df=pd.DataFrame([{
                'active_cases': 1,
                'rainfall_mm': 0,
                'temperature_c': 30,
                'humidity_pct': 70,
            }]),
            climate={'rainfall': 0, 'temperature': 30, 'humidity': 70},
            fitted_classifier=object(),
        )

        self.assertEqual(result['disease_label'], 'Dengue Fever')
        self.assertEqual(result['classification_confidence'], 0.829)
        self.assertFalse(result['is_anomaly'])
        self.assertGreaterEqual(result['anomaly_score'], 0.10)
        self.assertLessEqual(result['anomaly_score'], 0.22)
