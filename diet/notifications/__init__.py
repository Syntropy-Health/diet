"""
Notification Service

Handles routing and delivery of alerts to users through various channels.
"""

from .handlers import EmailHandler, InAppHandler, NotificationHandler, PushHandler
from .router import NotificationRouter, get_notification_router

__all__ = [
    "NotificationRouter",
    "get_notification_router",
    "NotificationHandler",
    "InAppHandler",
    "PushHandler",
    "EmailHandler",
]
