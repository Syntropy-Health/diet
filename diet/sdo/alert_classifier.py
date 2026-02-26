"""
SDO Alert Classifier

Classifies analysis results into appropriate alert levels
for notification routing.
"""

import logging
from typing import List, Optional

from diet.models.alerts import (
    AlertClassificationInput,
    AlertClassificationResult,
    AlertClassifier,
    AlertLevel,
    AlertNotification,
    NotificationChannel,
)
from diet.models.events import Recommendation
from diet.sdo.analyzer import SymptomAnalysisOutput
from diet.sdo.correlator import CorrelationResult
from diet.sdo.recommender import RecommendationResult

logger = logging.getLogger(__name__)


class SDOAlertClassifier:
    """
    Classifies SDO analysis results into alert levels.

    Uses multiple factors:
    - Symptom severity
    - Analysis confidence
    - Pattern detection
    - Risk indicators
    - Deficiency count and priority
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SDOAlertClassifier")
        self._base_classifier = AlertClassifier()

    def classify(
        self,
        analysis: SymptomAnalysisOutput,
        correlation: Optional[CorrelationResult] = None,
        recommendations: Optional[RecommendationResult] = None,
    ) -> AlertClassificationResult:
        """
        Classify the analysis into an alert level.

        Args:
            analysis: Symptom analysis output
            correlation: Optional correlation results
            recommendations: Optional recommendation results

        Returns:
            Alert classification result
        """
        urgency_indicators = list(analysis.urgency_indicators)

        if correlation:
            urgency_indicators.extend(correlation.risk_indicators)
            if correlation.overall_trend == "worsening":
                urgency_indicators.append("worsening_trend")

        high_priority_deficiencies = [
            d for d in analysis.deficiencies
            if d.priority >= 4 or d.deficiency_likelihood >= 0.8
        ]
        if high_priority_deficiencies:
            urgency_indicators.append("high_priority_deficiency")

        input_data = AlertClassificationInput(
            severity_score=analysis.severity_score,
            confidence_score=analysis.confidence_score,
            deficiency_count=len(analysis.deficiencies),
            symptom_count=len(analysis.insights),
            urgency_indicators=urgency_indicators,
        )

        result = self._base_classifier.classify(input_data)

        if recommendations and recommendations.priority_actions:
            if len(recommendations.priority_actions) >= 3 and result.alert_level == AlertLevel.TIPS:
                result.alert_level = AlertLevel.SUGGESTION
                result.reasoning += "; upgraded due to multiple priority actions"

        return result

    def create_notification(
        self,
        user_id: str,
        classification: AlertClassificationResult,
        analysis: SymptomAnalysisOutput,
        recommendations: Optional[RecommendationResult] = None,
    ) -> AlertNotification:
        """
        Create a notification based on classification.

        Args:
            user_id: Target user ID
            classification: Alert classification result
            analysis: Symptom analysis output
            recommendations: Optional recommendations

        Returns:
            Alert notification ready for delivery
        """
        title = self._generate_title(classification.alert_level, analysis)
        message = self._generate_message(classification.alert_level, analysis, recommendations)

        notification_recs = []
        if recommendations:
            for action in recommendations.priority_actions[:3]:
                notification_recs.append(Recommendation(
                    type="action",
                    title="Priority Action",
                    description=action,
                    priority=1,
                    evidence_basis="symptom_analysis",
                ))

            for lifestyle in recommendations.lifestyle_recommendations[:2]:
                notification_recs.append(lifestyle)

        channels = self._determine_channels(classification.alert_level)

        return AlertNotification(
            user_id=user_id,
            alert_level=classification.alert_level,
            title=title,
            message=message,
            recommendations=notification_recs,
            channels=channels,
            call_to_action=self._get_cta(classification.alert_level),
        )

    def _generate_title(
        self,
        level: AlertLevel,
        analysis: SymptomAnalysisOutput,
    ) -> str:
        """Generate notification title based on alert level."""
        if level == AlertLevel.ALERT:
            if analysis.deficiencies:
                return f"🚨 Health Alert: {analysis.deficiencies[0].nutrient.replace('_', ' ').title()} Attention Needed"
            return "🚨 Health Alert: Immediate Attention Recommended"

        elif level == AlertLevel.SUGGESTION:
            if analysis.deficiencies:
                return f"📋 Health Suggestion: Consider {analysis.deficiencies[0].nutrient.replace('_', ' ').title()}"
            return "📋 Health Suggestion: Dietary Optimization Available"

        else:  # TIPS
            return "💡 Health Tip: Wellness Insights Available"

    def _generate_message(
        self,
        level: AlertLevel,
        analysis: SymptomAnalysisOutput,
        recommendations: Optional[RecommendationResult] = None,
    ) -> str:
        """Generate notification message based on alert level."""
        parts = []

        if level == AlertLevel.ALERT:
            parts.append("Based on your recent symptoms, we've identified some important health insights that need your attention.")

            if analysis.deficiencies:
                top_def = analysis.deficiencies[0]
                parts.append(f"Potential {top_def.nutrient.replace('_', ' ')} deficiency detected with {top_def.deficiency_likelihood:.0%} confidence.")

        elif level == AlertLevel.SUGGESTION:
            parts.append("Your symptom patterns suggest some dietary adjustments could help.")

            if analysis.patterns_detected:
                parts.append(f"We noticed patterns in: {', '.join(p.replace('_', ' ') for p in analysis.patterns_detected[:2])}.")

        else:  # TIPS
            parts.append("Here are some wellness tips based on your recent health data.")

            if analysis.insights:
                parts.append(f"We have {len(analysis.insights)} insights to share.")

        if recommendations and recommendations.priority_actions:
            parts.append(f"Top action: {recommendations.priority_actions[0]}")

        return " ".join(parts)

    def _determine_channels(
        self,
        level: AlertLevel,
    ) -> List[NotificationChannel]:
        """Determine notification channels based on alert level."""
        if level == AlertLevel.ALERT:
            return [
                NotificationChannel.PUSH,
                NotificationChannel.IN_APP,
                NotificationChannel.EMAIL,
            ]
        elif level == AlertLevel.SUGGESTION:
            return [
                NotificationChannel.PUSH,
                NotificationChannel.IN_APP,
            ]
        else:  # TIPS
            return [NotificationChannel.IN_APP]

    def _get_cta(self, level: AlertLevel) -> str:
        """Get call-to-action text for alert level."""
        if level == AlertLevel.ALERT:
            return "View Details & Take Action"
        elif level == AlertLevel.SUGGESTION:
            return "See Recommendations"
        else:
            return "View Tips"
