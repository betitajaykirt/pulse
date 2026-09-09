from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.utils import timezone

from reports.views import (
    LAB_OCR_SCAN_MAX_AGE_SECONDS,
    _clear_lab_ocr_scan,
    _evaluate_lab_confirmation,
    _get_valid_lab_ocr_scan,
    _store_lab_ocr_scan,
    close_case_rejection,
)

class CloseCasePolicyTests(SimpleTestCase):
    def test_encoder_cannot_close_probable(self):
        msg = close_case_rejection(
            'encoder', 'Probable', 'Lost to Follow-up',
        )
        self.assertIsNotNone(msg)
        self.assertIn('cannot close probable or suspected', msg.lower())

    def test_bhw_cannot_close_suspected(self):
        msg = close_case_rejection(
            'barangay_health_worker', 'Suspected', 'Deceased',
        )
        self.assertIsNotNone(msg)

    def test_encoder_can_close_confirmed_recovered(self):
        self.assertIsNone(close_case_rejection(
            'encoder', 'Confirmed', 'Recovered (Confirmed Case)',
        ))

    def test_discard_not_a_case_blocked_for_cho(self):
        msg = close_case_rejection(
            'health_officer', 'Probable',
            'Discarded (Not a Case / False Alarm)',
        )
        self.assertIsNotNone(msg)
        self.assertIn('Case Confirmation', msg)

    def test_cho_can_close_probable_lost_to_follow_up(self):
        self.assertIsNone(close_case_rejection(
            'health_officer', 'Probable', 'Lost to Follow-up',
        ))


class _Session(dict):
    modified = False


def _request(post=None):
    request = RequestFactory().post('/ocr/', data=post or {})
    request.session = _Session()
    return request


class LabOcrScanSessionTests(SimpleTestCase):
    def test_scan_is_bound_to_report_id(self):
        request = _request()
        _store_lab_ocr_scan(
            request,
            report_id=12,
            ocr_patient_name='Jelyn Aujero',
            identity_match=True,
            lab_outcome='positive',
        )
        self.assertIsNone(_get_valid_lab_ocr_scan(request, 99))
        scan = _get_valid_lab_ocr_scan(request, 12)
        self.assertIsNotNone(scan)
        self.assertTrue(scan['identity_match'])

    def test_expired_scan_is_rejected(self):
        request = _request()
        _store_lab_ocr_scan(
            request,
            report_id=12,
            ocr_patient_name='Jelyn Aujero',
            identity_match=True,
        )
        request.session['pulse_lab_ocr_scan']['scanned_at'] = (
            timezone.now().timestamp() - LAB_OCR_SCAN_MAX_AGE_SECONDS - 5
        )
        self.assertIsNone(_get_valid_lab_ocr_scan(request, 12))

    def test_clear_scan(self):
        request = _request()
        _store_lab_ocr_scan(
            request,
            report_id=12,
            ocr_patient_name='Jelyn Aujero',
            identity_match=True,
        )
        _clear_lab_ocr_scan(request)
        self.assertIsNone(_get_valid_lab_ocr_scan(request, 12))


class EvaluateLabConfirmationTests(SimpleTestCase):
    def setUp(self):
        self.report = SimpleNamespace(id=12)

    def test_refuses_when_no_scan(self):
        request = _request()
        gate = _evaluate_lab_confirmation(request, self.report)
        self.assertFalse(gate['ok'])
        self.assertIn('Upload a laboratory document first', gate['error'])

    @patch('reports.views._patient_display_for_report')
    def test_refuses_identity_mismatch(self, display):
        display.return_value = {'name': 'Jelyn Aujero'}
        request = _request({
            'lab_interpretation': 'POSITIVE FOR ACUTE DENGUE FEVER INFECTION',
        })
        _store_lab_ocr_scan(
            request,
            report_id=12,
            ocr_patient_name='Maria Santos',
            identity_match=False,
            lab_outcome='positive',
        )
        gate = _evaluate_lab_confirmation(request, self.report)
        self.assertFalse(gate['ok'])
        self.assertIn('does not match', gate['error'])

    @patch('reports.views._patient_display_for_report')
    def test_refuses_unclear_result_even_if_client_posts_positive(self, display):
        display.return_value = {'name': 'Jelyn Aujero'}
        request = RequestFactory().post('/confirm/', data={
            'lab_interpretation': 'Pending',
            'lab_findings': '',
            'lab_outcome': 'positive',
        })
        request.session = _Session()
        _store_lab_ocr_scan(
            request,
            report_id=12,
            ocr_patient_name='Jelyn Aujero',
            identity_match=True,
            lab_outcome='positive',
        )
        gate = _evaluate_lab_confirmation(request, self.report)
        self.assertFalse(gate['ok'])
        self.assertIn('unclear', gate['error'].lower())

    @patch('reports.views._patient_display_for_report')
    def test_allows_matching_scan_with_clear_positive(self, display):
        display.return_value = {'name': 'Jelyn Aujero'}
        request = RequestFactory().post('/confirm/', data={
            'lab_interpretation': 'POSITIVE FOR ACUTE DENGUE FEVER INFECTION',
            'lab_findings': 'NS1: DETECTED',
            'lab_outcome': 'negative',
        })
        request.session = _Session()
        _store_lab_ocr_scan(
            request,
            report_id=12,
            ocr_patient_name='Jelyn S. Aujero',
            identity_match=True,
        )
        gate = _evaluate_lab_confirmation(request, self.report)
        self.assertTrue(gate['ok'])
        self.assertEqual(gate['lab_outcome'], 'positive')
