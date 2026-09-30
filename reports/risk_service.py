"""

Risk assessment and APTAS alert pipeline — adapted for pulse_db legacy alerts table.

"""

import logging
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from myapp.models import (
    Barangay, SurveillanceReport, RiskAssessment, Alert,
    MlAiPrediction, RiskAnalysis,
)
from reports.aptas_service import compute_and_log_barangay_risk, raw_anomaly_for_report
from reports.ml_display import (
    is_alertable_disease_label,
    official_disease_label,
    report_has_alertable_disease,
    report_is_category_i_high_confidence,
)

logger = logging.getLogger(__name__)

ALERT_TRIGGER_LABELS = {
    'aptas_anomaly': 'High Anomaly Score',
    'spatial_cluster': 'Spatial Cluster Spike',
    'pidsr_threshold': 'PIDSR Threshold Breach',
    'category_i_signal': 'Category I High-Confidence Case',
    'new_confirmed_case': 'New Confirmed Case',
}


def alert_trigger_label(code):
    return ALERT_TRIGGER_LABELS.get(code, 'APTAS Risk Signal')


def _default_alert_recommendation(report):
    from reports.recommendation_repository import approved_recommendation_matrix
    from reports.recommendation_service import resolve_case_recommendation, status_for_case

    bundle = resolve_case_recommendation(
        official_disease_label(report),
        status_for_case(report),
        matrix=approved_recommendation_matrix(),
    )
    actions = (bundle or {}).get('actions') or []
    recommendation = ' '.join(
        (action.get('text_en') or '').strip()
        for action in actions
        if (action.get('text_en') or '').strip()
    )
    return recommendation or _recommended_action(
        'high',
        official_disease_label(report),
    )


def _raw_anomaly_for_report(report, *, is_anomaly=False) -> float | None:
    del is_anomaly  # Boolean flags must not invent a High (0.75) score.
    return raw_anomaly_for_report(report)


def _persist_aptas_risk_log(report, raw_anomaly_score, force_activate=False):
    if not report.barangay_id:
        return None
    try:
        return compute_and_log_barangay_risk(
            report.barangay.barangay_name,
            official_disease_label(report),
            raw_anomaly_score,
            force_activate=force_activate,
            report=report,
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

    raw_anomaly = _raw_anomaly_for_report(report)
    aptas_log = _persist_aptas_risk_log(report, raw_anomaly)

    if aptas_log:
        risk_level = aptas_log.risk_level.lower()
        anomaly_score = Decimal(str(aptas_log.anomaly_score))
        risk_score = Decimal(str(aptas_log.final_risk_score)) / Decimal('100.0')
    else:
        risk_level = 'low'
        anomaly_score = (
            Decimal(str(raw_anomaly)) if raw_anomaly is not None else Decimal('0')
        )
        risk_score = Decimal('0')

    assessment = RiskAssessment.objects.create(
        report_id=report.id,
        barangay_id=report.barangay_id,
        anomaly_score=anomaly_score,
        risk_score=risk_score,
        risk_level=risk_level,
        model_version='aptas-engine-v1' if aptas_log else ('isolation-forest-v1' if is_anomaly else 'random-forest-v1'),
        evaluation_status='completed',
        evaluated_at=timezone.now(),
        recommended_action=_recommended_action(risk_level, official_disease_label(report)),
        created_at=timezone.now(),
    )

    is_active_alert = False
    if report_has_alertable_disease(report):
        if aptas_log:
            is_active_alert = aptas_log.is_active_alert
        else:
            is_active_alert = risk_level in ('high', 'critical')

    if is_active_alert:
        _create_alert(assessment, report.barangay, report, is_anomaly=is_anomaly, alert_level=risk_level)
    elif report_is_category_i_high_confidence(report):
        _create_alert(
            assessment,
            report.barangay,
            report,
            alert_level='high',
            trigger_code='category_i_signal',
        )

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


def _create_risk_analysis_bridge(
    report,
    *,
    risk_score,
    anomaly_score,
    risk_level,
    algorithm_used='aptas-engine-v1',
):
    """
  Create legacy ``ml_ai_predictions`` + ``risk_analysis`` rows required by
    ``alerts.analysis_id`` FK (must reference ``risk_analysis.analysis_id``).
    """
    now_ts = timezone.now()
    disease_type = official_disease_label(report) or 'Unknown'
    prediction = MlAiPrediction.objects.create(
        disease_type=disease_type,
        risk_score=float(risk_score),
        prediction_probability=float(anomaly_score),
        severity_level=str(risk_level),
        algorithm_used=algorithm_used,
        prediction_date=now_ts,
    )
    analysis = RiskAnalysis.objects.create(
        risk_score=float(risk_score),
        anomaly_flag=str(risk_level).lower() == 'critical',
        analysis_date=now_ts,
        prediction=prediction,
    )
    return analysis





def _get_purok_for_report(report):
    patient_case = report.patient_case.first() if hasattr(report, 'patient_case') else None
    if patient_case and patient_case.purok_street:
        return patient_case.purok_street
    if report.patient and report.patient.address:
        return report.patient.address
    return ""

def _create_alert(assessment, barangay, report, *, is_anomaly=False, alert_level=None, trigger_code=None):
    """Create or refresh an alert pending administrator review."""
    if not report_has_alertable_disease(report):
        logger.info(
            'Skipped APTAS alert for report %s — inconclusive until clinically validated.',
            getattr(report, 'id', None),
        )
        return None
    if not alert_level:
        alert_level = 'critical' if is_anomaly else 'high'

    disease = official_disease_label(report)
    purok = _get_purok_for_report(report)
    if not trigger_code:
        trigger_code = (
            'aptas_anomaly'
            if float(assessment.anomaly_score or 0) >= 0.50 or is_anomaly
            else 'spatial_cluster'
        )
    trigger_source = alert_trigger_label(trigger_code)
    recommendation_text = _default_alert_recommendation(report)

    from dashboard.models import AppNotification
    from django.utils import timezone
    today = timezone.now().date()

    active_cases = SurveillanceReport.objects.filter(
        barangay_id=report.barangay_id,
        status__in=['Pending ML Analysis', 'Suspected', 'Probable', 'Confirmed'],
    ).filter(
        Q(syndrome_type=disease)
        | Q(suspected_disease=disease)
        | Q(remarks__icontains=f'ML Top Prediction: {disease}')
    ).count()
    
    existing_notif = AppNotification.objects.filter(
        disease=disease,
        barangay_name=barangay.barangay_name,
        purok=purok,
        created_at__date=today
    ).order_by('-created_at').first()
    
    if existing_notif and existing_notif.alert_id:
        alert = Alert.objects.filter(id=existing_notif.alert_id).exclude(
            status__in=('resolved', 'rejected'),
        ).first()
        if alert:
            if alert_level == 'critical' and alert.alert_level != 'critical':
                alert.alert_level = 'critical'
                existing_notif.severity_level = 'Critical'
            alert.status = 'pending_review'
            alert.save(update_fields=['alert_level', 'status'])
            
            score_shift = float(assessment.risk_score) - float(existing_notif.final_risk_score or 0)
            existing_notif.score_shift = score_shift
            existing_notif.final_risk_score = assessment.risk_score
            existing_notif.anomaly_score = assessment.anomaly_score
            existing_notif.active_cases = active_cases
            existing_notif.source_report_id = report.id
            existing_notif.trigger_code = trigger_code
            existing_notif.trigger_source = trigger_source
            existing_notif.review_status = 'pending'
            existing_notif.recommendation_text = recommendation_text
            existing_notif.reviewed_by_id = None
            existing_notif.reviewed_by_role = ''
            existing_notif.reviewed_at = None
            existing_notif.sent_at = None
            existing_notif.last_evaluated_at = timezone.now()
            existing_notif.save(update_fields=[
                'final_risk_score', 'anomaly_score', 'severity_level', 
                'score_shift', 'active_cases', 'source_report_id',
                'trigger_code', 'trigger_source', 'review_status',
                'recommendation_text', 'reviewed_by_id', 'reviewed_by_role',
                'reviewed_at', 'sent_at', 'last_evaluated_at',
            ])
            return alert

    analysis = _create_risk_analysis_bridge(
        report,
        risk_score=assessment.risk_score,
        anomaly_score=assessment.anomaly_score,
        risk_level=alert_level,
        algorithm_used=assessment.model_version or 'aptas-engine-v1',
    )

    alert = Alert.objects.create(
        alert_level=alert_level,
        alert_date=timezone.now(),
        status='pending_review',
        alert_type=disease,
        analysis_id=analysis.id,
    )

    AppNotification.objects.create(
        alert_id=alert.id,
        source_report_id=report.id,
        disease=disease,
        barangay_name=barangay.barangay_name,
        purok=purok,
        severity_level=alert_level.title(),
        final_risk_score=assessment.risk_score,
        anomaly_score=assessment.anomaly_score,
        active_cases=active_cases,
        trigger_code=trigger_code,
        trigger_source=trigger_source,
        review_status='pending',
        recommendation_text=recommendation_text,
        last_evaluated_at=timezone.now(),
        spatial_metric=f"Spatial Risk: {assessment.risk_score} — Elevated risk in {barangay.barangay_name}",
        temporal_metric=f"Temporal Surge: {assessment.anomaly_score} — Recent anomaly detected",
    )

    return alert


def trigger_threshold_outbreak_alert(*, report_id, threshold_result):
    """
    Escalate APTAS when PIDSR category thresholds indicate probable or confirmed outbreak.
    """
    report = SurveillanceReport.objects.filter(id=report_id).select_related('barangay').first()
    if not report:
        return None

    disease_label = (
        threshold_result.get('disease_label')
        or report.syndrome_type
        or report.suspected_disease
        or ''
    )
    if not is_alertable_disease_label(disease_label):
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
    _persist_aptas_risk_log(report, raw_anomaly, force_activate=True)
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

    purok = _get_purok_for_report(report)
    from django.utils import timezone
    today = timezone.now().date()
    
    active_cases = SurveillanceReport.objects.filter(
        barangay_id=report.barangay_id,
        syndrome_type=report.syndrome_type,
        status__in=['Pending ML Analysis', 'Suspected', 'Probable', 'Confirmed']
    ).count()

    from dashboard.models import AppNotification
    
    existing_notif = AppNotification.objects.filter(
        disease=threshold_result.get('disease_label') or report.syndrome_type,
        barangay_name=threshold_result.get("barangay_name") or report.barangay.barangay_name,
        purok=purok,
        created_at__date=today
    ).order_by('-created_at').first()
    
    recommendation_text = _default_alert_recommendation(report)
    if existing_notif and existing_notif.alert_id:
        alert = Alert.objects.filter(id=existing_notif.alert_id).exclude(
            status__in=('resolved', 'rejected'),
        ).first()
        if alert:
            if alert_level == 'critical' and alert.alert_level != 'critical':
                alert.alert_level = 'critical'
                existing_notif.severity_level = 'Critical'
            alert.status = 'pending_review'
            alert.save(update_fields=['alert_level', 'status'])
            
            score_shift = float(risk_score) - float(existing_notif.final_risk_score or 0)
            existing_notif.score_shift = score_shift
            existing_notif.final_risk_score = risk_score
            existing_notif.anomaly_score = anomaly_score
            existing_notif.active_cases = active_cases
            existing_notif.source_report_id = report.id
            existing_notif.trigger_code = 'pidsr_threshold'
            existing_notif.trigger_source = alert_trigger_label('pidsr_threshold')
            existing_notif.review_status = 'pending'
            existing_notif.recommendation_text = recommendation_text
            existing_notif.reviewed_by_id = None
            existing_notif.reviewed_by_role = ''
            existing_notif.reviewed_at = None
            existing_notif.sent_at = None
            existing_notif.last_evaluated_at = timezone.now()
            existing_notif.save(update_fields=[
                'final_risk_score', 'anomaly_score', 'severity_level', 
                'score_shift', 'active_cases', 'source_report_id',
                'trigger_code', 'trigger_source', 'review_status',
                'recommendation_text', 'reviewed_by_id', 'reviewed_by_role',
                'reviewed_at', 'sent_at', 'last_evaluated_at',
            ])
            return alert
    
    # Bridge to legacy schema: alerts.analysis_id FK + risk_analysis.analysis_id
    now_ts = timezone.now()
    analysis = _create_risk_analysis_bridge(
        report,
        risk_score=risk_score,
        anomaly_score=anomaly_score,
        risk_level=risk_level,
        algorithm_used='pidsr-threshold-v1',
    )

    alert = Alert.objects.create(
        alert_level=alert_level,
        alert_date=now_ts,
        status='pending_review',
        alert_type=threshold_result.get('disease_label') or report.syndrome_type,
        analysis_id=analysis.id,
    )

    AppNotification.objects.create(
        alert_id=alert.id,
        source_report_id=report.id,
        disease=threshold_result.get('disease_label') or report.syndrome_type,
        barangay_name=threshold_result.get("barangay_name") or report.barangay.barangay_name,
        purok=purok,
        severity_level=alert_level.title(),
        final_risk_score=risk_score,
        anomaly_score=anomaly_score,
        active_cases=active_cases,
        trigger_code='pidsr_threshold',
        trigger_source=alert_trigger_label('pidsr_threshold'),
        review_status='pending',
        recommendation_text=recommendation_text,
        last_evaluated_at=timezone.now(),
        spatial_metric=f"Spatial Cluster Score: {risk_score} — High density in {threshold_result.get('barangay_name')}",
        temporal_metric=f"Temporal Surge Score: {anomaly_score} — {threshold_result.get('confirmed_count')} cases within {threshold_result.get('time_window_days')} days",
    )

    return alert


