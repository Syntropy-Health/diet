"""
Tests for the Notification System

Tests cover:
- Notification handlers (in-app, push, email)
- Notification router
- Alert level routing
- User preferences
"""

import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

from diet.models.alerts import (
    AlertLevel,
    AlertNotification,
    NotificationChannel,
    UserNotificationPreferences,
)
from diet.models.events import Recommendation
from diet.notifications.handlers import (
    DeliveryResult,
    EmailHandler,
    InAppHandler,
    PushHandler,
)
from diet.notifications.router import (
    NotificationRouter,
    RoutingResult,
    get_notification_router,
)


class TestInAppHandler:
    """Tests for the InAppHandler."""

    @pytest.fixture
    def handler(self):
        return InAppHandler()

    @pytest.fixture
    def sample_notification(self):
        return AlertNotification(
            user_id="test_user_001",
            alert_level=AlertLevel.SUGGESTION,
            title="Test Notification",
            message="This is a test notification message.",
            channels=[NotificationChannel.IN_APP],
        )

    @pytest.mark.asyncio
    async def test_deliver_success(self, handler, sample_notification):
        """Test successful in-app delivery."""
        result = await handler.deliver(sample_notification)

        assert isinstance(result, DeliveryResult)
        assert result.success
        assert result.channel == NotificationChannel.IN_APP
        assert result.delivered_at is not None

    @pytest.mark.asyncio
    async def test_notification_storage(self, handler, sample_notification):
        """Test that notifications are stored."""
        await handler.deliver(sample_notification)

        notifications = handler.get_notifications(sample_notification.user_id)
        assert len(notifications) == 1
        assert notifications[0].title == sample_notification.title

    @pytest.mark.asyncio
    async def test_unread_filter(self, handler, sample_notification):
        """Test filtering unread notifications."""
        await handler.deliver(sample_notification)

        unread = handler.get_notifications(sample_notification.user_id, unread_only=True)
        assert len(unread) == 1

        handler.mark_read(sample_notification.user_id, str(sample_notification.notification_id))

        unread = handler.get_notifications(sample_notification.user_id, unread_only=True)
        assert len(unread) == 0

    @pytest.mark.asyncio
    async def test_clear_notifications(self, handler, sample_notification):
        """Test clearing notifications."""
        await handler.deliver(sample_notification)
        handler.clear_notifications(sample_notification.user_id)

        notifications = handler.get_notifications(sample_notification.user_id)
        assert len(notifications) == 0

    @pytest.mark.asyncio
    async def test_deliverability_always_true(self, handler):
        """Test that in-app is always deliverable."""
        deliverable = await handler.check_deliverability("any_user")
        assert deliverable


class TestPushHandler:
    """Tests for the PushHandler."""

    @pytest.fixture
    def handler(self):
        return PushHandler()

    @pytest.fixture
    def sample_notification(self):
        return AlertNotification(
            user_id="test_push_user",
            alert_level=AlertLevel.ALERT,
            title="Push Alert",
            message="This is a push notification.",
            channels=[NotificationChannel.PUSH],
        )

    @pytest.mark.asyncio
    async def test_deliver_without_token_fails(self, handler, sample_notification):
        """Test delivery fails without registered token."""
        result = await handler.deliver(sample_notification)

        assert not result.success
        assert "No device tokens" in result.error

    @pytest.mark.asyncio
    async def test_deliver_with_token_succeeds(self, handler, sample_notification):
        """Test delivery succeeds with registered token."""
        handler.register_token(sample_notification.user_id, "test_device_token")

        result = await handler.deliver(sample_notification)

        assert result.success
        assert result.metadata.get("tokens_sent") == 1

    @pytest.mark.asyncio
    async def test_token_registration(self, handler):
        """Test token registration and unregistration."""
        handler.register_token("user1", "token1")
        handler.register_token("user1", "token2")

        deliverable = await handler.check_deliverability("user1")
        assert deliverable

        handler.unregister_token("user1", "token1")
        handler.unregister_token("user1", "token2")

        deliverable = await handler.check_deliverability("user1")
        assert not deliverable


class TestEmailHandler:
    """Tests for the EmailHandler."""

    @pytest.fixture
    def handler(self):
        return EmailHandler()

    @pytest.fixture
    def sample_notification(self):
        return AlertNotification(
            user_id="test_email_user",
            alert_level=AlertLevel.SUGGESTION,
            title="Email Notification",
            message="This is an email notification.",
            channels=[NotificationChannel.EMAIL],
        )

    @pytest.mark.asyncio
    async def test_deliver_without_email_fails(self, handler, sample_notification):
        """Test delivery fails without registered email."""
        result = await handler.deliver(sample_notification)

        assert not result.success
        assert "No email" in result.error

    @pytest.mark.asyncio
    async def test_deliver_with_email_succeeds(self, handler, sample_notification):
        """Test delivery succeeds with registered email."""
        handler.register_email(sample_notification.user_id, "test@example.com")

        result = await handler.deliver(sample_notification)

        assert result.success
        assert result.metadata.get("email") == "test@example.com"

    @pytest.mark.asyncio
    async def test_email_logging(self, handler, sample_notification):
        """Test that sent emails are logged."""
        handler.register_email(sample_notification.user_id, "test@example.com")
        await handler.deliver(sample_notification)

        sent = handler.get_sent_emails()
        assert len(sent) == 1
        assert sent[0]["to"] == "test@example.com"
        assert sent[0]["subject"] == sample_notification.title


class TestNotificationRouter:
    """Tests for the NotificationRouter."""

    @pytest.fixture
    def router(self):
        return NotificationRouter()

    @pytest.fixture
    def alert_notification(self):
        return AlertNotification(
            user_id="router_test_user",
            alert_level=AlertLevel.ALERT,
            title="Alert Test",
            message="Testing alert routing.",
            channels=[NotificationChannel.PUSH, NotificationChannel.IN_APP, NotificationChannel.EMAIL],
        )

    @pytest.fixture
    def suggestion_notification(self):
        return AlertNotification(
            user_id="router_test_user",
            alert_level=AlertLevel.SUGGESTION,
            title="Suggestion Test",
            message="Testing suggestion routing.",
            channels=[NotificationChannel.PUSH, NotificationChannel.IN_APP],
        )

    @pytest.fixture
    def tips_notification(self):
        return AlertNotification(
            user_id="router_test_user",
            alert_level=AlertLevel.TIPS,
            title="Tips Test",
            message="Testing tips routing.",
            channels=[NotificationChannel.IN_APP],
        )

    @pytest.mark.asyncio
    async def test_route_alert(self, router, alert_notification):
        """Test routing an alert notification."""
        result = await router.route(alert_notification)

        assert isinstance(result, RoutingResult)
        assert result.alert_level == AlertLevel.ALERT
        assert result.success

    @pytest.mark.asyncio
    async def test_route_suggestion(self, router, suggestion_notification):
        """Test routing a suggestion notification."""
        result = await router.route(suggestion_notification)

        assert result.success
        assert NotificationChannel.IN_APP in result.channels_attempted

    @pytest.mark.asyncio
    async def test_route_tips(self, router, tips_notification):
        """Test routing a tips notification."""
        result = await router.route(tips_notification)

        assert result.success
        assert result.alert_level == AlertLevel.TIPS

    @pytest.mark.asyncio
    async def test_user_preferences_filtering(self, router, tips_notification):
        """Test that user preferences filter notifications."""
        prefs = UserNotificationPreferences(
            user_id=tips_notification.user_id,
            tips_enabled=False,
        )

        result = await router.route(tips_notification, preferences=prefs)

        assert not result.success

    @pytest.mark.asyncio
    async def test_channel_selection(self, router, alert_notification):
        """Test channel selection based on preferences."""
        prefs = UserNotificationPreferences(
            user_id=alert_notification.user_id,
            enabled_channels=[NotificationChannel.IN_APP],
        )

        result = await router.route(alert_notification, preferences=prefs)

        assert NotificationChannel.IN_APP in result.channels_attempted
        assert len(result.channels_attempted) == 1

    @pytest.mark.asyncio
    async def test_batch_routing(self, router):
        """Test batch routing of multiple notifications."""
        notifications = [
            AlertNotification(
                user_id=f"batch_user_{i}",
                alert_level=AlertLevel.TIPS,
                title=f"Batch Test {i}",
                message="Testing batch routing.",
                channels=[NotificationChannel.IN_APP],
            )
            for i in range(3)
        ]

        results = await router.route_batch(notifications)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_preference_management(self, router):
        """Test user preference management."""
        prefs = UserNotificationPreferences(
            user_id="pref_test_user",
            tips_enabled=False,
            suggestions_enabled=True,
            alerts_enabled=True,
        )

        router.set_user_preferences("pref_test_user", prefs)

        retrieved = router.get_user_preferences("pref_test_user")
        assert not retrieved.tips_enabled
        assert retrieved.suggestions_enabled

    def test_routing_history(self, router, tips_notification):
        """Test routing history tracking."""
        asyncio.get_event_loop().run_until_complete(router.route(tips_notification))

        history = router.get_routing_history(tips_notification.user_id)
        assert len(history) > 0

    def test_router_singleton(self):
        """Test global router singleton."""
        router1 = get_notification_router()
        router2 = get_notification_router()
        assert router1 is router2


class TestAlertLevelRouting:
    """Integration tests for alert level-based routing."""

    @pytest.fixture
    def router(self):
        r = NotificationRouter()

        push_handler = r.get_handler(NotificationChannel.PUSH)
        if push_handler:
            push_handler.register_token("integration_user", "test_token")

        email_handler = r.get_handler(NotificationChannel.EMAIL)
        if email_handler:
            email_handler.register_email("integration_user", "test@example.com")

        prefs = UserNotificationPreferences(
            user_id="integration_user",
            enabled_channels=[
                NotificationChannel.IN_APP,
                NotificationChannel.PUSH,
                NotificationChannel.EMAIL,
            ],
        )
        r.set_user_preferences("integration_user", prefs)

        return r

    @pytest.mark.asyncio
    async def test_alert_uses_all_channels(self, router):
        """Test that ALERT level uses push, in-app, and email."""
        notification = AlertNotification(
            user_id="integration_user",
            alert_level=AlertLevel.ALERT,
            title="Critical Alert",
            message="This is a critical alert.",
            channels=[NotificationChannel.PUSH, NotificationChannel.IN_APP, NotificationChannel.EMAIL],
        )

        result = await router.route(notification)

        assert result.success
        successful_channels = [dr.channel for dr in result.delivery_results if dr.success]
        assert NotificationChannel.IN_APP in successful_channels
        assert NotificationChannel.PUSH in successful_channels
        assert NotificationChannel.EMAIL in successful_channels

    @pytest.mark.asyncio
    async def test_suggestion_skips_email(self, router):
        """Test that SUGGESTION level skips email by default."""
        notification = AlertNotification(
            user_id="integration_user",
            alert_level=AlertLevel.SUGGESTION,
            title="Suggestion",
            message="This is a suggestion.",
            channels=[NotificationChannel.PUSH, NotificationChannel.IN_APP],
        )

        result = await router.route(notification)

        assert result.success
        assert NotificationChannel.EMAIL not in result.channels_attempted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
