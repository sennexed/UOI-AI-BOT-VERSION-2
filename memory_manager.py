"""Short-term in-memory session management for user conversations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List


class MemoryManager:
    """Manage short-lived user sessions with inactivity expiration."""

    def __init__(self, expiry_minutes: int = 30, max_exchanges: int = 6) -> None:
        self.expiry_minutes = expiry_minutes
        self.max_messages = max_exchanges * 2
        self._sessions: Dict[int, Dict[str, object]] = {}

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _is_expired(self, last_active: datetime) -> bool:
        return self._now() - last_active > timedelta(minutes=self.expiry_minutes)

    def _ensure_session(self, user_id: int) -> None:
        session = self._sessions.get(user_id)
        if not session:
            self._sessions[user_id] = {"messages": [], "last_active": self._now()}
            return

        last_active = session["last_active"]
        if isinstance(last_active, datetime) and self._is_expired(last_active):
            self._sessions[user_id] = {"messages": [], "last_active": self._now()}

    def add_message(self, user_id: int, role: str, content: str) -> None:
        """Append a message to a user's session and enforce retention rules."""
        self._ensure_session(user_id)
        session = self._sessions[user_id]
        messages = session["messages"]
        if isinstance(messages, list):
            messages.append({"role": role, "content": content})
            if len(messages) > self.max_messages:
                del messages[:-self.max_messages]
        session["last_active"] = self._now()

    def get_session_messages(self, user_id: int) -> List[Dict[str, str]]:
        """Return session messages if active, otherwise an empty list."""
        self._ensure_session(user_id)
        session = self._sessions.get(user_id, {})
        session_messages = session.get("messages", [])
        if isinstance(session_messages, list):
            return list(session_messages)
        return []

    def clear_expired_sessions(self) -> None:
        """Remove all expired sessions from memory."""
        now = self._now()
        to_remove = []
        for user_id, session in self._sessions.items():
            last_active = session.get("last_active")
            if isinstance(last_active, datetime) and now - last_active > timedelta(minutes=self.expiry_minutes):
                to_remove.append(user_id)

        for user_id in to_remove:
            self._sessions.pop(user_id, None)
