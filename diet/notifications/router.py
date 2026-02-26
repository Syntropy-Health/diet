"""
Notification Router

Routes notifications to appropriate handlers based on alert level
and user preferences.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from diet.models.alerts import (
    AlertLevel,
    AlertNotification,
    NotificationChannel,
    UserNotificationPreferences,
)
from diet.notifications.handlers import (
    DeliveryResult,
    EmailHandler,
    InAppHandler,
    NotificationHandler,
    PushHandler,
)

logger = logging.getLogger(__name__)


class RoutingResult(BaseModel):
    """Result of notification routing."""
    notification_id: str
    user_id: str
    alert_level: AlertLevel
    channels_attempted: List[NotificationChannel] = Field(default_factory=list)
    delivery_results: List[DeliveryResult] = Field(default_factory=list)
    success: bool = False
    routed_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationRouter:
    """
    Routes notifications to appropriate delivery handlers.

    Features:
    - Channel selection based on alert level
    - User preference filtering
    - Quiet hours enforcement
    - Delivery tracking
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.NotificationRouter")

        self._handlers: Dict[NotificationChannel, NotificationHandler] = {
            NotificationChannel.IN_APP: InAppHandler(),
            NotificationChannel.PUSH: PushHandler(),
            NotificationChannel.EMAIL: EmailHandler(),
        }

        self._user_preferences: Dict[str, UserNotificationPreferences] = {}
        self._routing_history: List[RoutingResult] = []

    async def route(
        self,
        notification: AlertNotification,
        preferences: Optional[UserNotificationPreferences] = None,
    ) -> RoutingResult:
        """
        Route a notification through appropriate channels.

        Args:
            notification: The notification to route
            preferences: Optional user preferences override

        Returns:
            Routing result with delivery status
        """
        user_id = notification.user_id

        prefs = preferences or self._user_preferences.get(
            user_id,
            UserNotificationPreferences(user_id=user_id)
        )

        if not self._should_notify(notification, prefs):
            self.logger.info(f"Notification filtered by preferences for user {user_id}")
            return RoutingResult(
                notification_id=str(notification.notification_id),
                user_id=user_id,
                alert_level=notification.alert_level,
                success=False,
            )

        channels = self._select_channels(notification, prefs)

        result = RoutingResult(
            notification_id=str(notification.notification_id),
            user_id=user_id,
            alert_level=notification.alert_level,
            channels_attempted=channels,
        )

        delivery_tasks = []
        for channel in channels:
            handler = self._handlers.get(channel)
            if handler:
                delivery_tasks.append(handler.deliver(notification))

        if delivery_tasks:
            delivery_results = await asyncio.gather(*delivery_tasks, return_exceptions=True)

            for dr in delivery_results:
                if isinstance(dr, DeliveryResult):
                    result.delivery_results.append(dr)
                elif isinstance(dr, Exception):
                    self.logger.error(f"Delivery exception: {dr}")

        result.success = any(dr.success for dr in result.delivery_results)

        self._routing_history.append(result)
        self._routing_history = self._routing_history[-1000:]

        self.logger.info(
            f"Routed notification for user {user_id}: "
            f"level={notification.alert_level}, "
            f"channels={len(channels)}, "
            f"success={result.success}"
        )

        return result

    async def route_batch(
        self,
        notifications: List[AlertNotification],
    ) -> List[RoutingResult]:
        """Route multiple notifications in batch."""
        tasks = [self.route(n) for n in notifications]
        return await asyncio.gather(*tasks)

    def _should_notify(
        self,
        notification: AlertNotification,
        prefs: UserNotificationPreferences,
    ) -> bool:
        """Check if notification should be sent based on preferences."""
        level = notification.alert_level

        if level == AlertLevel.TIPS and not prefs.tips_enabled:
            return False
        if level == AlertLevel.SUGGESTION and not prefs.suggestions_enabled:
            return False
        if level == AlertLevel.ALERT and not prefs.alerts_enabled:
            return False

        if prefs.quiet_hours_start is not None and prefs.quiet_hours_end is not None:
            current_hour = datetime.utcnow().hour
            if prefs.quiet_hours_start <= current_hour < prefs.quiet_hours_end:
                if level != AlertLevel.ALERT:
                    return False

        return True

    def _select_channels(
        self,
        notification: AlertNotification,
        prefs: UserNotificationPreferences,
    ) -> List[NotificationChannel]:
        """Select channels for delivery based on notification and preferences."""
        requested = notification.channels
        enabled = prefs.enabled_channels

        selected = [ch for ch in requested if ch in enabled]

        if NotificationChannel.IN_APP in enabled and NotificationChannel.IN_APP not in selected:
            selected.append(NotificationChannel.IN_APP)

        return selected

    def set_user_preferences(
        self,
        user_id: str,
        preferences: UserNotificationPreferences,
    ) -> None:
        """Set notification preferences for a user."""
        self._user_preferences[user_id] = preferences

    def get_user_preferences(
        self,
        user_id: str,
    ) -> UserNotificationPreferences:
        """Get notification preferences for a user."""
        return self._user_preferences.get(
            user_id,
            UserNotificationPreferences(user_id=user_id)
        )

    def get_handler(
        self,
        channel: NotificationChannel,
    ) -> Optional[NotificationHandler]:
        """Get handler for a specific channel."""
        return self._handlers.get(channel)

    def register_handler(
        self,
        channel: NotificationChannel,
        handler: NotificationHandler,
    ) -> None:
        """Register a custom handler for a channel."""
        self._handlers[channel] = handler

    def get_routing_history(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[RoutingResult]:
        """Get routing history, optionally filtered by user."""
        history = self._routing_history
        if user_id:
            history = [r for r in history if r.user_id == user_id]
        return history[-limit:]


_router_instance: Optional[NotificationRouter] = None


def get_notification_router() -> NotificationRouter:
    """Get or create the global notification router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = NotificationRouter()
    return _router_instance
