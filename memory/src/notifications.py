"""Notification persistence for memory system.

Stores notifications (suggestions, captures, errors) so users can review them later.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Notifications file path
NOTIFICATIONS_FILE = Path.home() / ".claude" / "memory" / "data" / "notifications.json"
MAX_NOTIFICATIONS = 100  # Keep last 100 notifications


class Notification(BaseModel):
    """Notification model."""
    id: str
    type: str  # "suggestion", "capture", "error", "info"
    title: str
    message: str
    data: dict = {}
    read: bool = False
    created_at: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


def ensure_data_dir():
    """Ensure notifications data directory exists."""
    NOTIFICATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not NOTIFICATIONS_FILE.exists():
        NOTIFICATIONS_FILE.write_text("[]")


def load_notifications() -> List[Notification]:
    """Load all notifications from file."""
    ensure_data_dir()
    try:
        with open(NOTIFICATIONS_FILE, 'r') as f:
            data = json.load(f)
            return [Notification(**n) for n in data]
    except Exception as e:
        logger.error(f"Failed to load notifications: {e}")
        return []


def save_notifications(notifications: List[Notification]):
    """Save notifications to file."""
    ensure_data_dir()
    try:
        with open(NOTIFICATIONS_FILE, 'w') as f:
            data = [n.dict() for n in notifications]
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save notifications: {e}")


def store_notification(notification: Notification) -> Notification:
    """Store a new notification.

    Args:
        notification: Notification to store

    Returns:
        The stored notification
    """
    notifications = load_notifications()

    # Add new notification at the beginning
    notifications.insert(0, notification)

    # Keep only the last MAX_NOTIFICATIONS
    notifications = notifications[:MAX_NOTIFICATIONS]

    save_notifications(notifications)
    logger.debug(f"Stored notification: {notification.type} - {notification.title}")

    return notification


def get_notifications(
    unread_only: bool = False,
    type_filter: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Notification]:
    """Get notifications with optional filters.

    Args:
        unread_only: Only return unread notifications
        type_filter: Filter by notification type
        limit: Maximum number to return

    Returns:
        List of notifications
    """
    notifications = load_notifications()

    # Apply filters
    if unread_only:
        notifications = [n for n in notifications if not n.read]

    if type_filter:
        notifications = [n for n in notifications if n.type == type_filter]

    # Apply limit
    if limit:
        notifications = notifications[:limit]

    return notifications


def mark_notification_read(notification_id: str) -> bool:
    """Mark a notification as read.

    Args:
        notification_id: ID of notification to mark

    Returns:
        True if successful, False otherwise
    """
    notifications = load_notifications()

    for n in notifications:
        if n.id == notification_id:
            n.read = True
            save_notifications(notifications)
            logger.debug(f"Marked notification {notification_id} as read")
            return True

    logger.warning(f"Notification {notification_id} not found")
    return False


def mark_all_read() -> int:
    """Mark all notifications as read.

    Returns:
        Number of notifications marked
    """
    notifications = load_notifications()
    count = 0

    for n in notifications:
        if not n.read:
            n.read = True
            count += 1

    if count > 0:
        save_notifications(notifications)
        logger.debug(f"Marked {count} notifications as read")

    return count


def delete_notification(notification_id: str) -> bool:
    """Delete a notification.

    Args:
        notification_id: ID of notification to delete

    Returns:
        True if successful, False otherwise
    """
    notifications = load_notifications()
    original_count = len(notifications)

    notifications = [n for n in notifications if n.id != notification_id]

    if len(notifications) < original_count:
        save_notifications(notifications)
        logger.debug(f"Deleted notification {notification_id}")
        return True

    logger.warning(f"Notification {notification_id} not found")
    return False


def clear_all_notifications() -> int:
    """Clear all notifications.

    Returns:
        Number of notifications cleared
    """
    notifications = load_notifications()
    count = len(notifications)

    if count > 0:
        save_notifications([])
        logger.info(f"Cleared {count} notifications")

    return count


def get_notification_stats() -> dict:
    """Get notification statistics.

    Returns:
        Dictionary with notification stats
    """
    notifications = load_notifications()

    unread_count = sum(1 for n in notifications if not n.read)

    by_type = {}
    for n in notifications:
        by_type[n.type] = by_type.get(n.type, 0) + 1

    return {
        "total": len(notifications),
        "unread": unread_count,
        "read": len(notifications) - unread_count,
        "by_type": by_type
    }
