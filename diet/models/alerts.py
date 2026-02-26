"""
Alert Models for the Symptom-Diet Optimizer (SDO)

This module defines alert and notification models with tiered severity levels
for real-time user notifications.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .events import BaseEvent, EventType, Recommendation


class AlertLevel(str, Enum):
    """Alert severity levels for notification routing."""
    TIPS = "TIPS"           # Low priority - general wellness insights
    SUGGESTION = "SUGGESTION"  # Medium priority - actionable recommendations
    ALERT = "ALERT"         # High priority - critical health indicators


class NotificationChannel(str, Enum):
    """Channels for delivering notifications."""
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    SLACK = "slack"
    TEAMS = "teams"
    WHATSAPP = "whatsapp"


class AlertClassificationInput(BaseModel):
    """Input data for alert classification."""
    severity_score: float = Field(..., ge=0.0, le=1.0, description="Severity score")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    deficiency_count: int = Field(default=0, ge=0, description="Number of deficiencies")
    symptom_count: int = Field(default=0, ge=0, description="Number of symptoms")
    urgency_indicators: List[str] = Field(
        default_factory=list, description="Urgency indicator keywords"
    )
    historical_severity: Optional[float] = Field(
        default=None, description="Historical severity baseline"
    )


class AlertClassificationResult(BaseModel):
    """Result of alert classification."""
    alert_level: AlertLevel = Field(..., description="Classified alert level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    reasoning: str = Field(..., description="Classification reasoning")
    should_notify: bool = Field(default=True, description="Whether to send notification")
    priority_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Priority score")
    escalation_required: bool = Field(default=False, description="Whether escalation is needed")


class AlertNotification(BaseModel):
    """Notification payload for user alerts."""
    notification_id: UUID = Field(default_factory=uuid4, description="Unique notification ID")
    user_id: str = Field(..., description="Target user ID")
    alert_level: AlertLevel = Field(..., description="Alert severity level")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message body")

    # Recommendations and actions
    recommendations: List[Recommendation] = Field(
        default_factory=list, description="Actionable recommendations"
    )
    action_url: Optional[str] = Field(default=None, description="Deep link URL")
    call_to_action: Optional[str] = Field(default=None, description="CTA text")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None, description="Notification expiry")
    read: bool = Field(default=False, description="Read status")
    dismissed: bool = Field(default=False, description="Dismissed status")

    # Delivery preferences
    channels: List[NotificationChannel] = Field(
        default=[NotificationChannel.IN_APP], description="Delivery channels"
    )

    # Context
    source_insight_id: Optional[UUID] = Field(default=None, description="Source insight ID")
    related_products: List[Dict[str, Any]] = Field(
        default_factory=list, description="Related product data"
    )


class AlertTriggeredEvent(BaseEvent):
    """Event emitted when an alert is triggered for a user."""
    event_type: EventType = Field(default=EventType.ALERT_TRIGGERED)
    source_event_id: UUID = Field(..., description="ID of triggering insight event")
    notification: AlertNotification = Field(..., description="Alert notification payload")
    classification: AlertClassificationResult = Field(
        ..., description="Classification details"
    )


class UserNotificationPreferences(BaseModel):
    """User preferences for notification delivery."""
    user_id: str = Field(..., description="User identifier")
    enabled_channels: List[NotificationChannel] = Field(
        default=[NotificationChannel.IN_APP, NotificationChannel.PUSH],
        description="Enabled notification channels"
    )
    quiet_hours_start: Optional[int] = Field(
        default=None, ge=0, le=23, description="Quiet hours start (24h)"
    )
    quiet_hours_end: Optional[int] = Field(
        default=None, ge=0, le=23, description="Quiet hours end (24h)"
    )
    min_alert_level: AlertLevel = Field(
        default=AlertLevel.TIPS, description="Minimum alert level to notify"
    )
    frequency_cap_daily: int = Field(
        default=10, ge=1, description="Max notifications per day"
    )

    # Per-level preferences
    tips_enabled: bool = Field(default=True)
    suggestions_enabled: bool = Field(default=True)
    alerts_enabled: bool = Field(default=True)


class AlertClassifier:
    """Classifies insights into appropriate alert levels."""

    # Severity thresholds
    ALERT_THRESHOLD = 0.7
    SUGGESTION_THRESHOLD = 0.3
    MIN_CONFIDENCE = 0.5

    # Urgency keywords that escalate alert level
    URGENCY_KEYWORDS = [
        "severe", "critical", "urgent", "immediate", "emergency",
        "dangerous", "warning", "acute", "persistent", "worsening"
    ]

    @classmethod
    def classify(cls, input_data: AlertClassificationInput) -> AlertClassificationResult:
        """
        Classify an insight into an alert level.

        Args:
            input_data: Classification input data

        Returns:
            AlertClassificationResult with level and reasoning
        """
        severity = input_data.severity_score
        confidence = input_data.confidence_score

        # Check for urgency escalation
        urgency_boost = 0.0
        urgency_found = []
        for keyword in cls.URGENCY_KEYWORDS:
            if keyword in [ind.lower() for ind in input_data.urgency_indicators]:
                urgency_boost += 0.1
                urgency_found.append(keyword)

        adjusted_severity = min(severity + urgency_boost, 1.0)

        # Determine alert level
        if adjusted_severity >= cls.ALERT_THRESHOLD:
            level = AlertLevel.ALERT
            reasoning = f"High severity ({adjusted_severity:.2f}) triggers ALERT"
        elif adjusted_severity >= cls.SUGGESTION_THRESHOLD:
            level = AlertLevel.SUGGESTION
            reasoning = f"Moderate severity ({adjusted_severity:.2f}) triggers SUGGESTION"
        else:
            level = AlertLevel.TIPS
            reasoning = f"Low severity ({adjusted_severity:.2f}) triggers TIPS"

        if urgency_found:
            reasoning += f"; urgency keywords detected: {', '.join(urgency_found)}"

        # Determine if notification should be sent
        should_notify = confidence >= cls.MIN_CONFIDENCE
        if not should_notify:
            reasoning += f"; low confidence ({confidence:.2f}) - queued for review"

        # Calculate priority score
        priority_score = (adjusted_severity * 0.6) + (confidence * 0.4)

        # Check for escalation
        escalation_required = (
            level == AlertLevel.ALERT and
            input_data.deficiency_count >= 3 and
            adjusted_severity >= 0.85
        )

        return AlertClassificationResult(
            alert_level=level,
            confidence=confidence,
            reasoning=reasoning,
            should_notify=should_notify,
            priority_score=priority_score,
            escalation_required=escalation_required
        )
