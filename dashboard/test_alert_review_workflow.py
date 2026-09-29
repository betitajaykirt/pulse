from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, SimpleTestCase

from dashboard.views import review_alert_notification
from reports.risk_service import alert_trigger_label


class AlertTriggerLabelTests(SimpleTestCase):
    def test_anomaly_trigger_is_not_confirmed_case(self):
        self.assertEqual(
            alert_trigger_label('aptas_anomaly'),
            'High Anomaly Score',
        )

    def test_threshold_trigger_has_specific_label(self):
        self.assertEqual(
            alert_trigger_label('pidsr_threshold'),
            'PIDSR Threshold Breach',
        )


class AlertReviewWorkflowTests(SimpleTestCase):
    def _request(self, action='approve', recommendation='Inspect the affected area.'):
        request = RequestFactory().post('/dashboard/alerts/7/review/', data={
            'action': action,
            'recommendation_text': recommendation,
        })
        request.session = {
            'user_id': 4,
            'role': 'admin',
            'user_type': 'admin',
        }
        request._messages = FallbackStorage(request)
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        return request

    @patch('dashboard.views.transaction.atomic', return_value=nullcontext())
    @patch('dashboard.views.log_audit')
    @patch('dashboard.views.NotificationLog.objects')
    @patch('dashboard.views.Alert.objects')
    @patch('dashboard.models.AppNotificationRead.objects')
    @patch('dashboard.models.AppNotification.objects')
    def test_approval_activates_and_dispatches_to_field_roles(
        self,
        notifications,
        notification_reads,
        alerts,
        notification_logs,
        audit,
        _atomic,
    ):
        notification = SimpleNamespace(
            id=7,
            alert_id=11,
            disease='Dengue Fever',
            barangay_name='Napoles',
            trigger_source='High Anomaly Score',
            review_status='pending',
            recommendation_text='',
            reviewed_by_id=None,
            reviewed_by_role='',
            reviewed_at=None,
            sent_at=None,
            save=MagicMock(),
        )
        notifications.select_for_update.return_value.filter.return_value.first.return_value = notification
        alert = SimpleNamespace(status='pending_review', save=MagicMock())
        alerts.filter.return_value.first.return_value = alert

        response = review_alert_notification(self._request(), 7)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(notification.review_status, 'approved')
        self.assertEqual(notification.recommendation_text, 'Inspect the affected area.')
        self.assertEqual(alert.status, 'active')
        self.assertEqual(notification_logs.update_or_create.call_count, 3)
        notification_reads.filter.return_value.delete.assert_called_once()
        audit.assert_called_once()

    @patch('dashboard.views.transaction.atomic', return_value=nullcontext())
    @patch('dashboard.views.log_audit')
    @patch('dashboard.views.NotificationLog.objects')
    @patch('dashboard.views.Alert.objects')
    @patch('dashboard.models.AppNotification.objects')
    def test_rejection_does_not_dispatch(
        self,
        notifications,
        alerts,
        notification_logs,
        audit,
        _atomic,
    ):
        notification = SimpleNamespace(
            id=7,
            alert_id=11,
            disease='Dengue Fever',
            barangay_name='Napoles',
            trigger_source='High Anomaly Score',
            review_status='pending',
            recommendation_text='',
            reviewed_by_id=None,
            reviewed_by_role='',
            reviewed_at=None,
            sent_at=None,
            save=MagicMock(),
        )
        notifications.select_for_update.return_value.filter.return_value.first.return_value = notification
        alert = SimpleNamespace(status='pending_review', save=MagicMock())
        alerts.filter.return_value.first.return_value = alert

        response = review_alert_notification(
            self._request(action='reject', recommendation=''),
            7,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(notification.review_status, 'rejected')
        self.assertEqual(alert.status, 'rejected')
        notification_logs.get_or_create.assert_not_called()
        audit.assert_called_once()
