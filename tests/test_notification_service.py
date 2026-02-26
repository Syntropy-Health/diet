"""
Unit tests for the Notification Service.

Tests cover:
- NotificationService publish and delivery
- SSE streaming functionality
- User preference management
- Delivery result tracking
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.services.notification_service import (
    DeliveryResult,
    NotificationEvent,
    NotificationService,
    get_notification_service,
)
from diet.models.alerts import (
    AlertLevel,
    AlertNotification,
    NotificationChannel,
    UserNotificationPreferences,
)


class TestNotificationService:
    """Tests for NotificationService."""

    @pytest.fixture
    def service(self):
        """Create a fresh notification service for each test."""
        return NotificationService()

    @pytest.fixture
    def sample_notification(self):
        """Create a sample notification."""
        return AlertNotification(
            user_id="user_123",
            alert_level=AlertLevel.SUGGESTION,
            title="Test Notification",
            message="This is a test message",
            call_to_action="Take action",
            channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH],
        )

    @pytest.mark.asyncio
    async def test_publish_notification(self, service, sample_notification):
        """Test publishing a notification."""
        results = await service.publish(sample_notification)

        assert len(results) >= 1
        assert all(isinstance(r, DeliveryResult) for r in results)
        assert any(r.success for r in results)

    @pytest.mark.asyncio
    async def test_publish_stores_notification(self, service, sample_notification):
        """Test that published notifications are stored."""
        await service.publish(sample_notification)

        stored = service.get_notifications("user_123")
        assert len(stored) == 1
        assert stored[0].title == "Test Notification"

    @pytest.mark.asyncio
    async def test_in_app_channel_always_included(self, service, sample_notification):
        """Test that IN_APP channel is always included."""
        sample_notification.channels = [NotificationChannel.EMAIL]

        results = await service.publish(sample_notification)

        channels = [r.channel for r in results]
        assert NotificationChannel.IN_APP in channels

    @pytest.mark.asyncio
    async def test_user_preferences_filtering(self, service, sample_notification):
        """Test notification filtering based on user preferences."""
        prefs = UserNotificationPreferences(
            user_id="user_123",
            suggestions_enabled=False,
        )
        service.set_preferences("user_123", prefs)

        results = await service.publish(sample_notification)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_channel_selection_respects_preferences(self, service, sample_notification):
        """Test that channel selection respects user preferences."""
        prefs = UserNotificationPreferences(
            user_id="user_123",
            enabled_channels=[NotificationChannel.IN_APP],
        )
        service.set_preferences("user_123", prefs)

        results = await service.publish(sample_notification)

        assert all(r.channel == NotificationChannel.IN_APP for r in results)

    @pytest.mark.asyncio
    async def test_delivery_result_tracking(self, service, sample_notification):
        """Test that delivery results are tracked."""
        await service.publish(sample_notification)

        assert len(service._delivery_log) >= 1
        assert all(isinstance(r, DeliveryResult) for r in service._delivery_log)

    @pytest.mark.asyncio
    async def test_notification_limit(self, service):
        """Test that stored notifications are limited."""
        for i in range(150):
            notif = AlertNotification(
                user_id="user_123",
                alert_level=AlertLevel.TIPS,
                title=f"Notification {i}",
                message="Test",
            )
            await service.publish(notif)

        stored = service.get_notifications("user_123")
        assert len(stored) <= 100

    def test_set_and_get_preferences(self, service):
        """Test setting and getting user preferences."""
        prefs = UserNotificationPreferences(
            user_id="user_456",
            alerts_enabled=False,
            enabled_channels=[NotificationChannel.EMAIL],
        )

        service.set_preferences("user_456", prefs)
        retrieved = service.get_preferences("user_456")

        assert retrieved.user_id == "user_456"
        assert retrieved.alerts_enabled is False

    def test_default_preferences(self, service):
        """Test default preferences for new user."""
        prefs = service.get_preferences("new_user")

        assert prefs.user_id == "new_user"
        assert prefs.alerts_enabled is True
        assert prefs.suggestions_enabled is True
        assert prefs.tips_enabled is True


class TestNotificationEvent:
    """Tests for NotificationEvent model."""

    def test_event_creation(self):
        """Test creating a notification event."""
        event = NotificationEvent(
            user_id="user_123",
            data={"key": "value"},
        )

        assert event.user_id == "user_123"
        assert event.event_type == "notification"
        assert event.event_id is not None
        assert event.timestamp is not None

    def test_event_serialization(self):
        """Test event JSON serialization."""
        event = NotificationEvent(
            user_id="user_123",
            data={"title": "Test"},
        )

        json_str = event.model_dump_json()
        assert "user_123" in json_str
        assert "Test" in json_str


class TestDeliveryResult:
    """Tests for DeliveryResult model."""

    def test_successful_result(self):
        """Test creating a successful delivery result."""
        result = DeliveryResult(
            notification_id="notif_123",
            channel=NotificationChannel.IN_APP,
            success=True,
            delivered_at="2025-01-14T12:00:00Z",
        )

        assert result.success is True
        assert result.error is None

    def test_failed_result(self):
        """Test creating a failed delivery result."""
        result = DeliveryResult(
            notification_id="notif_123",
            channel=NotificationChannel.PUSH,
            success=False,
            error="Device token not found",
        )

        assert result.success is False
        assert "token" in result.error


class TestSSEStreaming:
    """Tests for SSE streaming functionality."""

    @pytest.fixture
    def service(self):
        return NotificationService()

    @pytest.mark.asyncio
    async def test_stream_connection(self, service):
        """Test SSE stream connection event."""
        stream = service.stream("user_123")

        first_event = await stream.__anext__()

        assert "event: connected" in first_event
        assert "user_123" in first_event

    @pytest.mark.asyncio
    async def test_connected_users_tracking(self, service):
        """Test that connected users are tracked."""
        stream = service.stream("user_789")

        await stream.__anext__()

        assert "user_789" in service.get_connected_users()

    @pytest.mark.asyncio
    async def test_notification_pushed_to_stream(self, service):
        """Test that notifications are pushed to connected users."""
        stream = service.stream("user_123")
        await stream.__anext__()

        notif = AlertNotification(
            user_id="user_123",
            alert_level=AlertLevel.ALERT,
            title="Urgent Alert",
            message="This is urgent",
        )
        await service.publish(notif)

        queue = service._user_queues["user_123"]
        assert not queue.empty()


class TestGlobalInstance:
    """Tests for global service instance."""

    def test_singleton_pattern(self):
        """Test that get_notification_service returns singleton."""
        service1 = get_notification_service()
        service2 = get_notification_service()

        assert service1 is service2

    def test_service_type(self):
        """Test that singleton is correct type."""
        service = get_notification_service()
        assert isinstance(service, NotificationService)


class TestAlertLevelRouting:
    """Tests for alert level-based routing."""

    @pytest.fixture
    def service(self):
        return NotificationService()

    @pytest.mark.asyncio
    async def test_alert_level_uses_all_channels(self, service):
        """Test that ALERT level uses all channels."""
        prefs = UserNotificationPreferences(
            user_id="user_123",
            enabled_channels=[
                NotificationChannel.IN_APP,
                NotificationChannel.PUSH,
                NotificationChannel.EMAIL,
            ],
        )
        service.set_preferences("user_123", prefs)

        notif = AlertNotification(
            user_id="user_123",
            alert_level=AlertLevel.ALERT,
            title="Alert",
            message="Urgent",
            channels=[
                NotificationChannel.IN_APP,
                NotificationChannel.PUSH,
                NotificationChannel.EMAIL,
            ],
        )

        results = await service.publish(notif)

        assert len(results) == 3
        channels = {r.channel for r in results}
        assert NotificationChannel.IN_APP in channels
        assert NotificationChannel.PUSH in channels
        assert NotificationChannel.EMAIL in channels

    @pytest.mark.asyncio
    async def test_tips_level_minimal_channels(self, service):
        """Test that TIPS level uses minimal channels."""
        notif = AlertNotification(
            user_id="user_123",
            alert_level=AlertLevel.TIPS,
            title="Tip",
            message="Helpful tip",
            channels=[NotificationChannel.IN_APP],
        )

        results = await service.publish(notif)

        assert len(results) == 1
        assert results[0].channel == NotificationChannel.IN_APP
