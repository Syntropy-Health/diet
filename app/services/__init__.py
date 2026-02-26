"""
App Services Package

Application-level services for event streaming and notifications.
"""

from .notification_service import NotificationService, get_notification_service, notification_stream

__all__ = [
    "NotificationService",
    "get_notification_service",
    "notification_stream",
]
