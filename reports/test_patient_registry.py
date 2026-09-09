from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import json

from django.test import RequestFactory, SimpleTestCase

from reports.patient_registry import (
    DuplicatePatientCaseError,
    assert_no_duplicate_case,
    get_or_create_patient,
    names_match,
    normalize_patient_name,
    patient_identity_key,
)


def _report(**kwargs):
    defaults = {
        'id': 41,
        'status': 'Suspected',
        'patient_id': 7,
        'patient_name': 'Juan Dela Cruz',
        'date_of_onset': date(2026, 4, 2),
        'syndrome_type': 'Dengue Fever',
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _patient(**kwargs):
    defaults = {
        'id': 7,
        'full_name': 'Juan Dela Cruz',
        'birthdate': date(2010, 1, 15),
        'barangay_id': 3,
        'sex': 'Male',
        'address': 'Purok 1',
        'save': MagicMock(),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class PatientNameTests(SimpleTestCase):
    def test_normalize_collapses_case_and_spaces(self):
        self.assertEqual(
            normalize_patient_name('  JUAN   dela  CRUZ '),
            'juan dela cruz',
        )

    def test_names_match_ignores_case(self):
        self.assertTrue(names_match('Juan Dela Cruz', 'juan dela cruz'))
        self.assertFalse(names_match('Juan Dela Cruz', 'Juan Cruz'))
        self.assertFalse(names_match('Unknown Resident', 'Unknown Resident'))

    def test_identity_key_includes_barangay(self):
        key = patient_identity_key('Juan Dela Cruz', date(2010, 1, 15), 3)
        self.assertEqual(key[0], 'juan dela cruz')
        self.assertEqual(key[2], 3)


class DuplicateCaseGuardTests(SimpleTestCase):
    def test_in_batch_duplicate_is_blocked(self):
        key = patient_identity_key('Juan Dela Cruz', date(2010, 1, 15), 3)
        with self.assertRaises(DuplicatePatientCaseError) as ctx:
            assert_no_duplicate_case(
                full_name='Juan Dela Cruz',
                birthdate=date(2010, 1, 15),
                barangay_id=3,
                case_index=2,
                allow_duplicate=False,
                seen_keys={key},
            )
        self.assertEqual(ctx.exception.code, 'duplicate_patient')

    def test_override_allows_in_batch_duplicate(self):
        key = patient_identity_key('Juan Dela Cruz', date(2010, 1, 15), 3)
        assert_no_duplicate_case(
            full_name='Juan Dela Cruz',
            birthdate=date(2010, 1, 15),
            barangay_id=3,
            case_index=2,
            allow_duplicate=True,
            seen_keys={key},
        )

    @patch('reports.patient_registry.find_open_duplicate_cases')
    def test_open_case_in_barangay_is_blocked(self, mock_find):
        mock_find.return_value = [_report()]
        with self.assertRaises(DuplicatePatientCaseError) as ctx:
            assert_no_duplicate_case(
                full_name='Juan Dela Cruz',
                birthdate=date(2010, 1, 15),
                barangay_id=3,
                case_index=1,
                allow_duplicate=False,
            )
        payload = ctx.exception.as_list()
        self.assertEqual(payload[0]['report_id'], 41)
        self.assertEqual(payload[0]['status'], 'Suspected')

    @patch('reports.patient_registry.find_open_duplicate_cases')
    def test_no_open_case_is_allowed(self, mock_find):
        mock_find.return_value = []
        assert_no_duplicate_case(
            full_name='Juan Dela Cruz',
            birthdate=date(2010, 1, 15),
            barangay_id=3,
            case_index=1,
            allow_duplicate=False,
        )


class GetOrCreatePatientTests(SimpleTestCase):
    @patch('reports.patient_registry.find_matching_patients')
    def test_reuses_existing_patient(self, mock_find):
        existing = _patient()
        mock_find.return_value = [existing]
        result = get_or_create_patient(
            full_name='Juan Dela Cruz',
            birthdate=date(2010, 1, 15),
            barangay_id=3,
            sex='Male',
            address='Purok 2',
        )
        self.assertIs(result, existing)

    @patch('reports.patient_registry.Patient.objects')
    @patch('reports.patient_registry.find_matching_patients')
    def test_creates_when_no_match(self, mock_find, mock_objects):
        mock_find.return_value = []
        created = _patient(id=99)
        mock_objects.create.return_value = created
        result = get_or_create_patient(
            full_name='Ana Santos',
            birthdate=date(1998, 5, 2),
            barangay_id=4,
            sex='Female',
            address='Purok 5',
        )
        self.assertIs(result, created)
        mock_objects.create.assert_called_once()
        kwargs = mock_objects.create.call_args.kwargs
        self.assertEqual(kwargs['full_name'], 'Ana Santos')
        self.assertEqual(kwargs['barangay_id'], 4)
        self.assertEqual(kwargs['birthdate'], date(1998, 5, 2))


class BatchDuplicateResponseTests(SimpleTestCase):
    @patch('reports.views.save_batch_submission')
    def test_duplicate_patient_returns_409(self, mock_save):
        from reports.views import _process_batch_submission

        mock_save.side_effect = DuplicatePatientCaseError(
            'already has an open case',
            [{
                'case_index': 1,
                'patient_name': 'Juan Dela Cruz',
                'report_id': 9,
                'status': 'Suspected',
                'patient_id': 3,
                'syndrome_type': 'Dengue Fever',
                'date_of_onset': '2026-04-02',
            }],
        )
        request = RequestFactory().generic(
            'POST',
            '/reports/submit/',
            data=json.dumps({'cases': [{}]}),
            content_type='application/json',
        )
        request.session = {'user_id': 1}
        response = _process_batch_submission(request)
        self.assertEqual(response.status_code, 409)
        body = json.loads(response.content)
        self.assertFalse(body['ok'])
        self.assertEqual(body['code'], 'duplicate_patient')
        self.assertEqual(body['duplicates'][0]['report_id'], 9)
