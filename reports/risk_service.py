"""

Risk assessment and APTAS alert pipeline — adapted for pulse_db legacy alerts table.

"""

import logging
from decimal import Decimal

from django.utils import timezone

from myapp.models import (

    Barangay, SurveillanceReport, RiskAssessment, Alert, NotificationLog,

)

from reports.aptas_service import compute_and_log_barangay_risk

logger = logging.getLogger(__name__)


def _raw_anomaly_for_report(report, *, is_anomaly=False) -> float:
    if report.ml_anomaly_score is not None:
        return float(report.ml_anomaly_score)
    if is_anomaly or report.is_anomaly:
        return -0.45
    return 0.25


def _persist_aptas_risk_log(report, raw_anomaly_score):
    if not report.barangay_id:
        return None
    try:
        return compute_and_log_barangay_risk(
            report.barangay.barangay_name,
            report.syndrome_type,
            raw_anomaly_score,
        )
    except Exception as exc:
        logger.exception('APTAS risk log failed for report %s: %s', report.id, exc)
        return None




def trigger_aptas_for_report(report_id, *, is_anomaly=False):

    """

    Evaluate risk and dispatch dashboard alerts after ML-analyzed submission.



    Outbreak anomaly flags escalate to high/critical APTAS thresholds immediately.

    """

    report = SurveillanceReport.objects.filter(id=report_id).select_related('barangay').first()

    if not report:

        return None

    _persist_aptas_risk_log(report, _raw_anomaly_for_report(report, is_anomaly=is_anomaly))

    if is_anomaly or report.is_anomaly:

        risk_level = 'critical'

        anomaly_score = report.ml_anomaly_score or Decimal('0.9000')

    else:

        risk_level = 'moderate'

        anomaly_score = report.ml_anomaly_score or Decimal('0.3500')



    score_map = {

        'low': Decimal('0.2500'),

        'moderate': Decimal('0.5000'),

        'high': Decimal('0.7500'),

        'critical': Decimal('1.0000'),

    }

    risk_score = score_map.get(risk_level, Decimal('0.5000'))



    assessment = RiskAssessment.objects.create(

        report_id=report.id,

        barangay_id=report.barangay_id,

        anomaly_score=anomaly_score,

        risk_score=risk_score,

        risk_level=risk_level,

        model_version='isolation-forest-v1' if is_anomaly else 'random-forest-v1',

        evaluation_status='completed',

        evaluated_at=timezone.now(),

        recommended_action=_recommended_action(risk_level, report.syndrome_type),

        created_at=timezone.now(),

    )



    if risk_level in ('high', 'critical'):

        _create_alert(assessment, report.barangay, report, is_anomaly=is_anomaly)



    return assessment





def evaluate_report_risk(report_id):

    """Legacy entry point — delegates to APTAS trigger."""

    report = SurveillanceReport.objects.filter(id=report_id).select_related('barangay').first()

    if not report:

        return None

    return trigger_aptas_for_report(report_id, is_anomaly=report.is_anomaly)





def _recommended_action(risk_level, syndrome_type):

    actions = {

        'critical': f'Immediate outbreak investigation required for {syndrome_type}.',

        'high': f'Enhanced surveillance and BHW coordination for {syndrome_type}.',

        'moderate': f'Continue routine monitoring for {syndrome_type}.',

        'low': f'No immediate action required for {syndrome_type}.',

    }

    return actions.get(risk_level, actions['low'])





def _create_alert(assessment, barangay, report, *, is_anomaly=False):

    """Create a legacy-format alert row (pulse_db.alerts)."""

    alert_level = 'critical' if is_anomaly else 'high'

    summary = (

        f'OUTBREAK SPIKE: {report.syndrome_type} in {barangay.barangay_name}'

        if is_anomaly else

        f'{report.syndrome_type} alert in {barangay.barangay_name}'

    )



    alert = Alert.objects.create(

        alert_level=alert_level,

        alert_date=timezone.now(),

        status='active',

        alert_type=report.syndrome_type,

        analysis_id=assessment.id,

    )



    for role in ('admin', 'health_officer', 'surveillance_officer'):

        NotificationLog.objects.create(

            alert_id=alert.id,

            recipient_role=role,

            channel='dashboard',

            message_summary=summary,

            delivery_status='sent',

            sent_at=timezone.now(),

            created_at=timezone.now(),

        )



    return alert


def trigger_threshold_outbreak_alert(*, report_id, threshold_result):
    """
    Escalate APTAS when PIDSR category thresholds indicate probable or confirmed outbreak.
    """
    report = SurveillanceReport.objects.filter(id=report_id).select_related('barangay').first()
    if not report:
        return None

    status = threshold_result.get('status', '')
    if status == 'OUTBREAK_CONFIRMED':
        risk_level = 'critical'
        alert_level = 'critical'
    elif status == 'PROBABLE_OUTBREAK':
        risk_level = 'high'
        alert_level = 'high'
    else:
        return None

    raw_anomaly = (
        float(report.ml_anomaly_score)
        if report.ml_anomaly_score is not None
        else (-0.5 if risk_level == 'critical' else -0.35)
    )
    _persist_aptas_risk_log(report, raw_anomaly)
    anomaly_score = Decimal('0.9500') if risk_level == 'critical' else Decimal('0.7500')
    score_map = {
        'high': Decimal('0.7500'),
        'critical': Decimal('1.0000'),
    }
    risk_score = score_map[risk_level]

    assessment = RiskAssessment.objects.create(
        report_id=report.id,
        barangay_id=report.barangay_id,
        anomaly_score=anomaly_score,
        risk_score=risk_score,
        risk_level=risk_level,
        model_version='pidsr-threshold-v1',
        evaluation_status='completed',
        evaluated_at=timezone.now(),
        recommended_action=(
            f'PIDSR {threshold_result.get("category_level")} threshold breached: '
            f'{threshold_result.get("confirmed_count")} confirmed '
            f'{threshold_result.get("disease_label")} case(s) in '
            f'{threshold_result.get("barangay_name")} within '
            f'{threshold_result.get("time_window_days")} days — status {status}.'
        ),
        created_at=timezone.now(),
    )

    summary = (
        f'THRESHOLD {status}: {threshold_result.get("disease_label")} in '
        f'{threshold_result.get("barangay_name")} '
        f'({threshold_result.get("confirmed_count")} confirmed / '
        f'{threshold_result.get("time_window_days")}d)'
    )

    alert = Alert.objects.create(
        alert_level=alert_level,
        alert_date=timezone.now(),
        status='active',
        alert_type=threshold_result.get('disease_label') or report.syndrome_type,
        analysis_id=assessment.id,
    )

    for role in ('admin', 'health_officer', 'surveillance_officer'):
        NotificationLog.objects.create(
            alert_id=alert.id,
            recipient_role=role,
            channel='dashboard',
            message_summary=summary,
            delivery_status='sent',
            sent_at=timezone.now(),
            created_at=timezone.now(),
        )

    return alert


