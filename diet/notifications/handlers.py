"""
Notification Handlers

Channel-specific handlers for delivering notifications to users.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from diet.models.alerts import AlertNotification, NotificationChannel

logger = logging.getLogger(__name__)


class DeliveryResult(BaseModel):
    """Result of a notification delivery attempt."""
    notification_id: str
    channel: NotificationChannel
    success: bool
    delivered_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationHandler(ABC):
    """Abstract base class for notification handlers."""

    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        """Return the channel this handler serves."""
        pass

    @abstractmethod
    async def deliver(self, notification: AlertNotification) -> DeliveryResult:
        """
        Deliver a notification through this channel.

        Args:
            notification: The notification to deliver

        Returns:
            Delivery result with success/failure info
        """
        pass

    @abstractmethod
    async def check_deliverability(self, user_id: str) -> bool:
        """
        Check if notifications can be delivered to a user via this channel.

        Args:
            user_id: Target user ID

        Returns:
            True if deliverable, False otherwise
        """
        pass


class InAppHandler(NotificationHandler):
    """Handler for in-app notifications."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.InAppHandler")
        self._notification_store: Dict[str, List[AlertNotification]] = {}

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.IN_APP

    async def deliver(self, notification: AlertNotification) -> DeliveryResult:
        """Store notification for in-app display."""
        try:
            user_id = notification.user_id
            if user_id not in self._notification_store:
                self._notification_store[user_id] = []

            self._notification_store[user_id].append(notification)

            self._notification_store[user_id] = self._notification_store[user_id][-100:]

            self.logger.info(f"In-app notification stored for user {user_id}")

            return DeliveryResult(
                notification_id=str(notification.notification_id),
                channel=self.channel,
                success=True,
                delivered_at=datetime.utcnow(),
            )

        except Exception as e:
            self.logger.error(f"In-app delivery failed: {e}")
            return DeliveryResult(
                notification_id=str(notification.notification_id),
                channel=self.channel,
                success=False,
                error=str(e),
            )

    async def check_deliverability(self, user_id: str) -> bool:
        """In-app notifications are always deliverable."""
        return True

    def get_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
    ) -> List[AlertNotification]:
        """Get notifications for a user."""
        notifications = self._notification_store.get(user_id, [])
        if unread_only:
            return [n for n in notifications if not n.read]
        return notifications.copy()

    def mark_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read."""
        notifications = self._notification_store.get(user_id, [])
        for n in notifications:
            if str(n.notification_id) == notification_id:
                n.read = True
                return True
        return False

    def clear_notifications(self, user_id: str) -> None:
        """Clear all notifications for a user."""
        if user_id in self._notification_store:
            del self._notification_store[user_id]


class PushHandler(NotificationHandler):
    """Handler for push notifications."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.PushHandler")
        self._device_tokens: Dict[str, List[str]] = {}
        self._delivery_log: List[DeliveryResult] = []

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.PUSH

    async def deliver(self, notification: AlertNotification) -> DeliveryResult:
        """Send push notification (mock implementation)."""
        try:
            user_id = notification.user_id
            tokens = self._device_tokens.get(user_id, [])

            if not tokens:
                self.logger.warning(f"No push tokens for user {user_id}")
                return DeliveryResult(
                    notification_id=str(notification.notification_id),
                    channel=self.channel,
                    success=False,
                    error="No device tokens registered",
                )

            self.logger.info(
                f"Push notification sent to user {user_id}: {notification.title}"
            )

            result = DeliveryResult(
                notification_id=str(notification.notification_id),
                channel=self.channel,
                success=True,
                delivered_at=datetime.utcnow(),
                metadata={"tokens_sent": len(tokens)},
            )
            self._delivery_log.append(result)
            return result

        except Exception as e:
            self.logger.error(f"Push delivery failed: {e}")
            return DeliveryResult(
                notification_id=str(notification.notification_id),
                channel=self.channel,
                success=False,
                error=str(e),
            )

    async def check_deliverability(self, user_id: str) -> bool:
        """Check if user has registered push tokens."""
        return bool(self._device_tokens.get(user_id))

    def register_token(self, user_id: str, token: str) -> None:
        """Register a device token for a user."""
        if user_id not in self._device_tokens:
            self._device_tokens[user_id] = []
        if token not in self._device_tokens[user_id]:
            self._device_tokens[user_id].append(token)

    def unregister_token(self, user_id: str, token: str) -> None:
        """Unregister a device token."""
        if user_id in self._device_tokens:
            self._device_tokens[user_id] = [
                t for t in self._device_tokens[user_id] if t != token
            ]


class EmailHandler(NotificationHandler):
    """Handler for email notifications."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.EmailHandler")
        self._user_emails: Dict[str, str] = {}
        self._sent_emails: List[Dict[str, Any]] = []

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    async def deliver(self, notification: AlertNotification) -> DeliveryResult:
        """Send email notification (mock implementation)."""
        try:
            user_id = notification.user_id
            email = self._user_emails.get(user_id)

            if not email:
                self.logger.warning(f"No email for user {user_id}")
                return DeliveryResult(
                    notification_id=str(notification.notification_id),
                    channel=self.channel,
                    success=False,
                    error="No email address registered",
                )

            email_data = {
                "to": email,
                "subject": notification.title,
                "body": notification.message,
                "sent_at": datetime.utcnow().isoformat(),
            }
            self._sent_emails.append(email_data)

            self.logger.info(f"Email sent to {email}: {notification.title}")

            return DeliveryResult(
                notification_id=str(notification.notification_id),
                channel=self.channel,
                success=True,
                delivered_at=datetime.utcnow(),
                metadata={"email": email},
            )

        except Exception as e:
            self.logger.error(f"Email delivery failed: {e}")
            return DeliveryResult(
                notification_id=str(notification.notification_id),
                channel=self.channel,
                success=False,
                error=str(e),
            )

    async def check_deliverability(self, user_id: str) -> bool:
        """Check if user has registered email."""
        return user_id in self._user_emails

    def register_email(self, user_id: str, email: str) -> None:
        """Register an email for a user."""
        self._user_emails[user_id] = email

    def get_sent_emails(self) -> List[Dict[str, Any]]:
        """Get list of sent emails (for testing)."""
        return self._sent_emails.copy()
