from io import StringIO
from unittest.mock import patch

import pandas as pd
from django.core.management import call_command
from django.test import SimpleTestCase
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

from reports import prediction_service as ps
from reports.classifier_store import pack_model, unpack_model
from reports.management.commands import retrain_classifier as command


def _tiny_model():
    encoder = LabelEncoder().fit(['Dengue Fever', 'Measles'])
    forest = RandomForestClassifier(n_estimators=3, random_state=0).fit([[0, 1], [1, 0]], [0, 1])
    return forest, encoder


class ModelStoreTests(SimpleTestCase):
    def test_model_survives_pack_and_unpack(self):
        forest, encoder = _tiny_model()
        restored_forest, restored_encoder = unpack_model(pack_model(forest, encoder))
        self.assertEqual(list(restored_encoder.classes_), ['Dengue Fever', 'Measles'])
        self.assertEqual(list(restored_forest.predict([[1, 0]])), [1])


class CachedClassifierTests(SimpleTestCase):
    def setUp(self):
        ps._get_fitted_classifier.cache_clear()
        self.addCleanup(ps._get_fitted_classifier.cache_clear)

    def test_uses_saved_model_when_one_is_active(self):
        forest, encoder = _tiny_model()
        with patch.object(ps, 'active_model_id', return_value=7), \
                patch.object(ps, 'load_active_model', return_value=(7, forest, encoder)), \
                patch.object(ps, 'fit_random_forest_classifier') as fit:
            self.assertEqual(ps._get_fitted_classifier(), (forest, encoder))
        fit.assert_not_called()

    def test_falls_back_to_training_data_without_saved_model(self):
        with patch.object(ps, 'active_model_id', return_value=None), \
                patch.object(ps, '_load_training_frame', return_value='frame'), \
                patch.object(ps, 'fit_random_forest_classifier', return_value=('clf', 'enc')) as fit:
            self.assertEqual(ps._get_fitted_classifier(), ('clf', 'enc'))
        fit.assert_called_once_with('frame')

    def test_falls_back_when_saved_model_cannot_load(self):
        with patch.object(ps, 'active_model_id', side_effect=RuntimeError('db down')), \
                patch.object(ps, '_load_training_frame', return_value='frame'), \
                patch.object(ps, 'fit_random_forest_classifier', return_value=('clf', 'enc')):
            self.assertEqual(ps._get_fitted_classifier(), ('clf', 'enc'))

    def test_checks_for_a_newer_model_only_after_the_refresh_window(self):
        forest, encoder = _tiny_model()
        with patch.object(ps, 'active_model_id', return_value=1) as newest, \
                patch.object(ps, 'load_active_model', return_value=(1, forest, encoder)):
            ps._get_fitted_classifier()
            ps._get_fitted_classifier()
            self.assertEqual(newest.call_count, 1)
            ps._classifier_state['checked_at'] -= ps.CLASSIFIER_REFRESH_SECONDS + 1
            ps._get_fitted_classifier()
            self.assertEqual(newest.call_count, 2)


class RetrainCommandTests(SimpleTestCase):
    def _run(self, *args):
        out = StringIO()
        call_command('retrain_classifier', *args, stdout=out)
        return out.getvalue()

    def test_skips_when_too_few_live_cases(self):
        base = pd.DataFrame({'age': [1], 'disease_label': ['Measles']})
        with patch.object(command, 'load_csv_training_frame', return_value=base), \
                patch.object(command, 'load_live_training_frame', return_value=None), \
                patch.object(command, 'fit_random_forest_classifier') as fit:
            output = self._run()
        self.assertIn('Not retraining', output)
        fit.assert_not_called()

    def test_keeps_current_model_when_candidate_is_worse(self):
        base = pd.DataFrame({'age': range(40), 'sex': ['Male'] * 40,
                             'disease_label': ['Measles', 'Dengue Fever'] * 20})
        live = base.head(10).copy()
        forest, encoder = _tiny_model()
        with patch.object(command, 'load_csv_training_frame', return_value=base), \
                patch.object(command, 'load_live_training_frame', return_value=live), \
                patch.object(command, 'fit_random_forest_classifier', return_value=(forest, encoder)), \
                patch.object(command, 'load_active_model', return_value=(3, forest, encoder)), \
                patch.object(command, 'holdout_accuracy', side_effect=[0.80, 0.95]), \
                patch.object(command, 'save_active_model') as save:
            output = self._run('--min-live', '5')
        self.assertIn('less accurate', output)
        save.assert_not_called()
