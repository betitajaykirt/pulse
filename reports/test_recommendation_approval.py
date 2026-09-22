from copy import deepcopy
import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from reports.recommendation_admin import recommendation_card
from reports.recommendation_repository import (
    approved_recommendation_matrix,
    clear_approved_recommendation_cache,
    matrix_from_payload,
)
from reports.recommendation_service import (
    baseline_recommendation_payload,
    resolve_case_recommendation,
)


class ApprovedRecommendationTests(SimpleTestCase):
    def tearDown(self):
        clear_approved_recommendation_cache()

    def _edited_payload(self):
        payload = deepcopy(baseline_recommendation_payload())
        dengue = next(
            row for row in payload['diseases']
            if row['label'] == 'Dengue Fever'
        )
        dengue['actions']['probable'][0]['en'] = 'Approved edited action.'
        return payload

    @patch('reports.recommendation_repository.RecommendationRevision.objects')
    def test_only_approved_revision_is_loaded(self, objects):
        payload = self._edited_payload()
        objects.filter.return_value.order_by.return_value.values_list.return_value.first.return_value = payload

        matrix = approved_recommendation_matrix()

        objects.filter.assert_called_once_with(status='approved')
        bundle = resolve_case_recommendation(
            'Dengue Fever',
            'probable',
            matrix=matrix,
        )
        self.assertEqual(bundle['actions'][0]['text_en'], 'Approved edited action.')

    @patch('reports.recommendation_repository.RecommendationRevision.objects')
    def test_missing_approved_revision_uses_shipped_baseline(self, objects):
        objects.filter.return_value.order_by.return_value.values_list.return_value.first.return_value = None

        matrix = approved_recommendation_matrix()

        self.assertEqual(
            matrix,
            matrix_from_payload(baseline_recommendation_payload()),
        )


class RecommendationCardAccessTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch('reports.recommendation_admin.RecommendationRevision.objects')
    def test_admin_can_load_a_card_for_inline_editing(self, objects):
        objects.filter.return_value.order_by.return_value.first.return_value = None
        request = self.factory.get(
            '/reports/recommendations/card/',
            {'disease': 'Dengue Fever'},
        )
        request.session = {'user_id': 1, 'role': 'admin'}

        response = recommendation_card(request)
        payload = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['disease'], 'Dengue Fever')
        self.assertIn('probable', payload['actions'])
        self.assertIsNone(payload['pending_revision_id'])

    @patch('accounts.auth_utils.messages.error')
    def test_field_user_cannot_open_inline_editor_api(self, _message):
        request = self.factory.get(
            '/reports/recommendations/card/',
            {'disease': 'Dengue Fever'},
        )
        request.session = {'user_id': 9, 'role': 'barangay_health_worker'}

        response = recommendation_card(request)

        self.assertEqual(response.status_code, 302)
