from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from dashboard.views import api_alert_acknowledge
from myapp.barangay_scope import can_acknowledge_alerts


class AlertAcknowledgePolicyTests(SimpleTestCase):
    def test_cho_roles_may_acknowledge(self):
        for role in ('admin', 'super_admin', 'health_officer', 'surveillance_officer'):
            self.assertTrue(can_acknowledge_alerts(role), role)

    def test_field_roles_may_not_acknowledge(self):
        for role in ('encoder', 'barangay_health_worker', 'catchment_nurse', None, ''):
            self.assertFalse(can_acknowledge_alerts(role), role)

    def _post(self, role):
        request = RequestFactory().post('/dashboard/api/alerts/9/acknowledge/')
        request.session = {'user_id': 4, 'role': role, 'full_name': 'Test User'}
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        return request

    def test_encoder_receives_403(self):
        response = api_alert_acknowledge(self._post('encoder'), 9)
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'CHO officers', response.content)

    @patch('dashboard.views.log_system')
    @patch('dashboard.views.log_audit')
    @patch('dashboard.views.Alert.objects')
    def test_health_officer_acknowledges_and_is_audited(self, mock_alerts, mock_audit, mock_system):
        alert = SimpleNamespace(
            id=9,
            status='active',
            alert_type='Dengue Fever',
            alert_level='high',
            save=MagicMock(),
        )
        mock_alerts.filter.return_value.first.return_value = alert

        response = api_alert_acknowledge(self._post('health_officer'), 9)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(alert.status, 'acknowledged')
        alert.save.assert_called_once()
        mock_audit.assert_called_once()
        self.assertEqual(mock_audit.call_args.args[2], 'alert_acknowledged')
        mock_system.assert_called_once()
        self.assertEqual(mock_system.call_args.args[0], 'alert_acknowledged')
