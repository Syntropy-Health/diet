"""
Notification Service

Application-level service for streaming notifications and alerts
via Server-Sent Events (SSE).
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from diet.models.alerts import (
    AlertLevel,
    AlertNotification,
    NotificationChannel,
    UserNotificationPreferences,
)

logger = logging.getLogger(__name__)


class NotificationEvent(BaseModel):
    """Streamed notification event."""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str = Field(default="notification")
    user_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]


class DeliveryResult(BaseModel):
    """Result of notification delivery."""
    notification_id: str
    channel: NotificationChannel
    success: bool
    delivered_at: Optional[str] = None
    error: Optional[str] = None


class NotificationService:
    """
    Application service for notification delivery and streaming.

    Features:
    - SSE streaming for real-time notifications
    - Multi-channel delivery (in-app, push, email)
    - User preference management
    - Delivery tracking
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.NotificationService")
        self._user_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._user_preferences: Dict[str, UserNotificationPreferences] = {}
        self._notification_store: Dict[str, List[AlertNotification]] = defaultdict(list)
        self._delivery_log: List[DeliveryResult] = []
        self._connected_users: set = set()

    async def publish(self, notification: AlertNotification) -> List[DeliveryResult]:
        """
        Publish a notification to all appropriate channels.

        Args:
            notification: The notification to publish

        Returns:
            List of delivery results per channel
        """
        user_id = notification.user_id
        results = []

        prefs = self._user_preferences.get(
            user_id,
            UserNotificationPreferences(user_id=user_id)
        )

        if not self._should_notify(notification, prefs):
            self.logger.info(f"Notification filtered for user {user_id}")
            return results

        channels = self._select_channels(notification, prefs)

        for channel in channels:
            result = await self._deliver_to_channel(notification, channel)
            results.append(result)
            self._delivery_log.append(result)

        self._notification_store[user_id].append(notification)
        self._notification_store[user_id] = self._notification_store[user_id][-100:]

        if user_id in self._connected_users:
            event = NotificationEvent(
                user_id=user_id,
                data={
                    "notification_id": str(notification.notification_id),
                    "alert_level": notification.alert_level.value,
                    "title": notification.title,
                    "message": notification.message,
                    "call_to_action": notification.call_to_action,
                }
            )
            await self._user_queues[user_id].put(event)

        self.logger.info(
            f"Published notification to user {user_id}: "
            f"channels={len(channels)}, success={sum(1 for r in results if r.success)}"
        )

        return results

    async def stream(self, user_id: str) -> AsyncGenerator[str, None]:
        """
        Stream notifications for a user via SSE.

        Args:
            user_id: User to stream notifications for

        Yields:
            SSE-formatted notification events
        """
        self._connected_users.add(user_id)
        self.logger.info(f"User {user_id} connected to notification stream")

        try:
            yield f"event: connected\ndata: {json.dumps({'user_id': user_id})}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(
                        self._user_queues[user_id].get(),
                        timeout=30.0
                    )
                    yield f"event: {event.event_type}\ndata: {event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    yield f"event: ping\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"

        except asyncio.CancelledError:
            pass
        finally:
            self._connected_users.discard(user_id)
            self.logger.info(f"User {user_id} disconnected from notification stream")

    async def _deliver_to_channel(
        self,
        notification: AlertNotification,
        channel: NotificationChannel,
    ) -> DeliveryResult:
        """Deliver notification to a specific channel."""
        try:
            if channel == NotificationChannel.IN_APP:
                return DeliveryResult(
                    notification_id=str(notification.notification_id),
                    channel=channel,
                    success=True,
                    delivered_at=datetime.utcnow().isoformat(),
                )

            elif channel == NotificationChannel.PUSH:
                self.logger.info(f"Push notification queued: {notification.title}")
                return DeliveryResult(
                    notification_id=str(notification.notification_id),
                    channel=channel,
                    success=True,
                    delivered_at=datetime.utcnow().isoformat(),
                )

            elif channel == NotificationChannel.EMAIL:
                self.logger.info(f"Email notification queued: {notification.title}")
                return DeliveryResult(
                    notification_id=str(notification.notification_id),
                    channel=channel,
                    success=True,
                    delivered_at=datetime.utcnow().isoformat(),
                )

            else:
                return DeliveryResult(
                    notification_id=str(notification.notification_id),
                    channel=channel,
                    success=False,
                    error=f"Unknown channel: {channel}",
                )

        except Exception as e:
            return DeliveryResult(
                notification_id=str(notification.notification_id),
                channel=channel,
                success=False,
                error=str(e),
            )

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

        return True

    def _select_channels(
        self,
        notification: AlertNotification,
        prefs: UserNotificationPreferences,
    ) -> List[NotificationChannel]:
        """Select channels for delivery."""
        requested = notification.channels
        enabled = prefs.enabled_channels

        selected = [ch for ch in requested if ch in enabled]

        if NotificationChannel.IN_APP not in selected:
            selected.append(NotificationChannel.IN_APP)

        return selected

    def set_preferences(
        self,
        user_id: str,
        preferences: UserNotificationPreferences,
    ) -> None:
        """Set user notification preferences."""
        self._user_preferences[user_id] = preferences

    def get_preferences(self, user_id: str) -> UserNotificationPreferences:
        """Get user notification preferences."""
        return self._user_preferences.get(
            user_id,
            UserNotificationPreferences(user_id=user_id)
        )

    def get_notifications(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[AlertNotification]:
        """Get stored notifications for a user."""
        return self._notification_store.get(user_id, [])[-limit:]

    def get_connected_users(self) -> List[str]:
        """Get list of connected user IDs."""
        return list(self._connected_users)


_service_instance: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the global notification service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = NotificationService()
    return _service_instance


async def notification_stream(user_id: str) -> AsyncGenerator[str, None]:
    """Convenience function for streaming notifications."""
    service = get_notification_service()
    async for event in service.stream(user_id):
        yield event
