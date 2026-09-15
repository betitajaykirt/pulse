from datetime import date

from django.test import SimpleTestCase

from reports.pidsr_schema import DISEASE_LABELS
from reports.recommendation_service import (
    CLUSTER_RADIUS_METERS,
    CLUSTER_WINDOW_DAYS,
    cases_share_cluster,
    recommendation_matrix,
    resolve_case_recommendation,
    resolve_cluster_recommendations,
)


class RecommendationMatrixContractTests(SimpleTestCase):
    def test_matrix_covers_exactly_the_27_canonical_diseases(self):
        matrix = recommendation_matrix()

        self.assertEqual(len(matrix), 27)
        self.assertEqual(set(matrix), set(DISEASE_LABELS))

    def test_every_state_has_complete_bilingual_actions(self):
        for disease, row in recommendation_matrix().items():
            self.assertEqual(
                set(row['actions']),
                {'suspected', 'probable', 'confirmed', 'cluster'},
                disease,
            )
            self.assertIn(row['category'], {'Category I', 'Category II'})
            for state, actions in row['actions'].items():
                self.assertTrue(actions, f'{disease}/{state}')
                for action in actions:
                    self.assertTrue(action['code'])
                    self.assertTrue(action['en'])
                    self.assertTrue(action['local'])
                    self.assertTrue(action['targets'])


class RecommendationResolverTests(SimpleTestCase):
    def _case(self, disease, status, **overrides):
        return {
            'id': overrides.pop('id', disease + status),
            'disease_name': disease,
            'status': status,
            'case_count': overrides.pop('case_count', 1),
            **overrides,
        }

    def test_same_disease_escalates_to_highest_status(self):
        result = resolve_cluster_recommendations([
            self._case('Dengue Fever', 'Suspected'),
            self._case('Dengue Fever', 'Confirmed'),
            self._case('Dengue Fever', 'Probable'),
        ])

        card = result['disease_cards'][0]
        self.assertEqual(card['highest_status'], 'Confirmed')
        self.assertEqual(card['case_count'], 3)
        self.assertTrue(card['is_cluster'])

    def test_case_classification_escalates_when_workflow_status_is_active(self):
        result = resolve_cluster_recommendations([{
            'disease_name': 'Dengue Fever',
            'status': 'Active',
            'case_classification': 'confirmed',
        }])

        self.assertEqual(
            result['disease_cards'][0]['highest_status'],
            'Confirmed',
        )

    def test_category_i_precedes_higher_status_category_ii(self):
        result = resolve_cluster_recommendations([
            self._case('Dengue Fever', 'Confirmed', case_count=8),
            self._case('Measles', 'Suspected'),
        ])

        self.assertEqual(
            [card['disease'] for card in result['disease_cards']],
            ['Measles', 'Dengue Fever'],
        )
        self.assertTrue(result['has_category_i'])

    def test_secondary_sort_uses_status_then_case_count(self):
        result = resolve_cluster_recommendations([
            self._case('Cholera', 'Confirmed', case_count=1),
            self._case('Dengue Fever', 'Probable', case_count=10),
            self._case('Leptospirosis', 'Confirmed', case_count=4),
        ])

        self.assertEqual(
            [card['disease'] for card in result['disease_cards']],
            ['Leptospirosis', 'Cholera', 'Dengue Fever'],
        )

    def test_field_summary_deduplicates_stable_action_codes(self):
        result = resolve_cluster_recommendations([
            self._case('Cholera', 'Confirmed'),
            self._case('Typhoid and Paratyphoid Fever', 'Confirmed'),
        ])

        codes = [action['code'] for action in result['field_action_summary']]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(codes.count('cluster_line_list'), 1)
        self.assertEqual(codes.count('water_food_cluster_investigation'), 1)

    def test_single_case_alias_and_unknown_disease(self):
        bundle = resolve_case_recommendation('Dengue', 'probable')

        self.assertEqual(bundle['disease'], 'Dengue Fever')
        self.assertEqual(bundle['highest_status'], 'Probable')
        self.assertIsNone(resolve_case_recommendation('Undetermined', 'confirmed'))


class ClusterMembershipTests(SimpleTestCase):
    def _case(self, lat, lon, onset):
        return {
            'latitude': lat,
            'longitude': lon,
            'date_of_onset': onset,
        }

    def test_cases_inside_300_meters_and_seven_days_share_cluster(self):
        left = self._case(10.7202, 122.5621, date(2026, 9, 1))
        right = self._case(10.7210, 122.5621, date(2026, 9, 8))

        self.assertTrue(cases_share_cluster(left, right))

    def test_spatial_or_temporal_boundary_excludes_case(self):
        anchor = self._case(10.7202, 122.5621, date(2026, 9, 1))
        spatially_far = self._case(10.7240, 122.5621, date(2026, 9, 2))
        temporally_far = self._case(10.7210, 122.5621, date(2026, 9, 9))

        self.assertFalse(cases_share_cluster(anchor, spatially_far))
        self.assertFalse(cases_share_cluster(anchor, temporally_far))
        self.assertEqual(CLUSTER_RADIUS_METERS, 300)
        self.assertEqual(CLUSTER_WINDOW_DAYS, 7)

