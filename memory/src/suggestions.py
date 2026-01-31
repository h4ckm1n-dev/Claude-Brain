"""Smart notification suppression and suggestion throttling.

Reduces notification fatigue by:
- Time-based throttling (hourly/daily limits)
- Context-aware suppression (rapid-fire detection)
- Quality filtering (low-relevance suggestions)
"""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from collections import defaultdict

logger = logging.getLogger(__name__)

# State file path
STATE_FILE = Path.home() / ".claude" / "memory" / "data" / "suggestion_state.json"

# Default throttling settings
DEFAULT_SETTINGS = {
    "suggestionFrequency": "always",  # "always", "hourly", "daily", "never"
    "suggestionMinScore": 0.7,
    "notificationEnabled": True
}


class SuggestionThrottler:
    """Manages suggestion frequency and notification suppression."""

    def __init__(self):
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load throttler state from file."""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load suggestion state: {e}")

        # Default state
        return {
            "last_suggestion_time": {},  # user_id -> timestamp
            "suggestion_count": {},      # user_id -> count
            "recent_messages": {},       # user_id -> [timestamps]
            "low_quality_count": {}      # user_id -> count
        }

    def _save_state(self):
        """Save throttler state to file."""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save suggestion state: {e}")

    def should_show_suggestions(
        self,
        user_id: str,
        context: Dict,
        settings: Optional[Dict] = None
    ) -> bool:
        """
        Determine if suggestions should be shown.

        Args:
            user_id: User identifier
            context: Current context (branch, project, files)
            settings: User settings (from settings.json)

        Returns:
            True if suggestions should be shown
        """
        if settings is None:
            settings = DEFAULT_SETTINGS

        frequency = settings.get('suggestionFrequency', 'always')

        # Always disabled
        if frequency == 'never':
            logger.debug("Suggestions disabled by user setting")
            return False

        # Always enabled (default)
        if frequency == 'always':
            # Still check rapid-fire and low-quality
            if self._is_rapid_fire(user_id):
                logger.debug("Suppressing: rapid-fire detected")
                return False
            if self._recent_suggestions_low_quality(user_id):
                logger.debug("Suppressing: recent suggestions were low quality")
                return False
            return True

        # Time-based throttling
        last_time_str = self.state["last_suggestion_time"].get(user_id)
        if not last_time_str:
            # First time, allow
            return self._update_and_allow(user_id)

        last_time = datetime.fromisoformat(last_time_str)
        now = datetime.now()

        # Hourly throttling
        if frequency == 'hourly':
            if (now - last_time) < timedelta(hours=1):
                logger.debug(f"Suppressing: shown within last hour ({last_time})")
                return False
            return self._update_and_allow(user_id)

        # Daily throttling
        if frequency == 'daily':
            if (now - last_time) < timedelta(days=1):
                logger.debug(f"Suppressing: shown within last day ({last_time})")
                return False
            return self._update_and_allow(user_id)

        return True

    def _update_and_allow(self, user_id: str) -> bool:
        """Update state and allow suggestion."""
        self.state["last_suggestion_time"][user_id] = datetime.now().isoformat()
        self.state["suggestion_count"][user_id] = self.state["suggestion_count"].get(user_id, 0) + 1
        self._save_state()
        return True

    def _is_rapid_fire(self, user_id: str, window_minutes: int = 2, max_messages: int = 5) -> bool:
        """
        Detect rapid-fire messaging (>5 messages in 2 minutes).

        Args:
            user_id: User identifier
            window_minutes: Time window in minutes
            max_messages: Maximum messages in window

        Returns:
            True if rapid-fire detected
        """
        now = datetime.now()
        recent_messages = self.state["recent_messages"].get(user_id, [])

        # Convert to datetime objects
        recent_times = [
            datetime.fromisoformat(ts)
            for ts in recent_messages
            if isinstance(ts, str)
        ]

        # Filter to within window
        cutoff = now - timedelta(minutes=window_minutes)
        recent_times = [t for t in recent_times if t > cutoff]

        # Add current message
        recent_times.append(now)

        # Update state
        self.state["recent_messages"][user_id] = [t.isoformat() for t in recent_times]
        self._save_state()

        # Check if rapid-fire
        if len(recent_times) > max_messages:
            logger.debug(f"Rapid-fire: {len(recent_times)} messages in {window_minutes}min")
            return True

        return False

    def _recent_suggestions_low_quality(
        self,
        user_id: str,
        threshold: int = 3
    ) -> bool:
        """
        Check if recent suggestions were consistently low quality.

        Low quality = low click-through or explicit dismissal

        Args:
            user_id: User identifier
            threshold: Number of consecutive low-quality suggestions

        Returns:
            True if recent suggestions were low quality
        """
        low_quality_count = self.state["low_quality_count"].get(user_id, 0)

        if low_quality_count >= threshold:
            logger.debug(f"Recent {low_quality_count} suggestions were low quality")
            return True

        return False

    def record_suggestion_quality(self, user_id: str, was_useful: bool):
        """
        Record if a suggestion was useful.

        Args:
            user_id: User identifier
            was_useful: True if suggestion was clicked/used
        """
        if was_useful:
            # Reset low quality counter
            self.state["low_quality_count"][user_id] = 0
        else:
            # Increment low quality counter
            count = self.state["low_quality_count"].get(user_id, 0) + 1
            self.state["low_quality_count"][user_id] = count

        self._save_state()

    def get_stats(self, user_id: Optional[str] = None) -> Dict:
        """Get throttler statistics."""
        if user_id:
            return {
                "last_suggestion": self.state["last_suggestion_time"].get(user_id),
                "total_suggestions": self.state["suggestion_count"].get(user_id, 0),
                "recent_messages": len(self.state["recent_messages"].get(user_id, [])),
                "low_quality_streak": self.state["low_quality_count"].get(user_id, 0)
            }

        # Overall stats
        return {
            "total_users": len(self.state["suggestion_count"]),
            "total_suggestions": sum(self.state["suggestion_count"].values()),
            "users_with_low_quality": sum(
                1 for count in self.state["low_quality_count"].values() if count > 0
            )
        }


# Global instance
_throttler = None


def get_throttler() -> SuggestionThrottler:
    """Get global throttler instance."""
    global _throttler
    if _throttler is None:
        _throttler = SuggestionThrottler()
    return _throttler


def should_show_suggestions(
    user_id: str = "default",
    context: Optional[Dict] = None,
    settings: Optional[Dict] = None
) -> bool:
    """
    Check if suggestions should be shown.

    Args:
        user_id: User identifier
        context: Current context
        settings: User settings

    Returns:
        True if suggestions should be shown
    """
    throttler = get_throttler()
    return throttler.should_show_suggestions(user_id, context or {}, settings)


def record_suggestion_quality(user_id: str = "default", was_useful: bool = False):
    """Record suggestion quality feedback."""
    throttler = get_throttler()
    throttler.record_suggestion_quality(user_id, was_useful)


def get_throttler_stats(user_id: Optional[str] = None) -> Dict:
    """Get throttler statistics."""
    throttler = get_throttler()
    return throttler.get_stats(user_id)
