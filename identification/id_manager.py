"""Persistent identity storage and lifecycle management for UOI identification."""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


ALLOWED_STATUSES = {"Active", "Suspended", "Revoked"}


class IDManager:
    """Manage registration records for Discord users in a JSON database."""

    def __init__(self, file_path: str = "identity_database.json") -> None:
        self.file_path = Path(file_path)
        self._ensure_file()

    @staticmethod
    def _default_data() -> Dict[str, Dict[str, Dict[str, str]]]:
        return {"users": {}}

    @staticmethod
    def _today_iso() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _ensure_file(self) -> None:
        if not self.file_path.exists():
            self._write(self._default_data())

    def _read(self) -> Dict[str, Any]:
        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict):
                return self._default_data()
            users = data.get("users")
            if not isinstance(users, dict):
                data["users"] = {}
            return data
        except (json.JSONDecodeError, OSError):
            return self._default_data()

    def _write(self, data: Dict[str, Any]) -> None:
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

    def _generate_unique_uoi_id(self, users: Dict[str, Dict[str, str]]) -> str:
        existing = {value.get("uoi_id", "") for value in users.values()}
        while True:
            candidate = f"{random.randint(0, 999999):06d}"
            if candidate not in existing:
                return candidate

    @staticmethod
    def _generate_internal_card_id() -> str:
        return str(uuid.uuid4())

    def register_user(self, user_id: int, full_name: str) -> Tuple[bool, str, Dict[str, str] | None]:
        """Register a user and return (ok, message, record)."""
        data = self._read()
        users = data["users"]
        key = str(user_id)
        existing = users.get(key)

        if isinstance(existing, dict):
            status = str(existing.get("status", "")).strip()
            if status == "Revoked":
                return False, "Registration blocked: your ID is revoked. Contact an admin.", None
            return False, "You are already registered.", existing

        clean_name = full_name.strip()
        if not clean_name:
            return False, "Full name cannot be empty.", None

        record = {
            "full_name": clean_name,
            "uoi_id": self._generate_unique_uoi_id(users),
            "role": "Member",
            "status": "Active",
            "date_joined": self._today_iso(),
            "internal_card_id": self._generate_internal_card_id(),
        }
        users[key] = record
        self._write(data)
        return True, "Registration successful.", record

    def get_user(self, user_id: int) -> Dict[str, str] | None:
        """Return the stored user record, if any."""
        data = self._read()
        user = data["users"].get(str(user_id))
        if isinstance(user, dict):
            return user
        return None

    def set_role(self, user_id: int, role: str) -> Tuple[bool, str]:
        """Set user role for an existing registration."""
        data = self._read()
        key = str(user_id)
        user = data["users"].get(key)
        if not isinstance(user, dict):
            return False, "User is not registered."

        clean_role = role.strip()
        if not clean_role:
            return False, "Role cannot be empty."

        user["role"] = clean_role
        self._write(data)
        return True, "Role updated successfully."

    def set_status(self, user_id: int, status: str) -> Tuple[bool, str]:
        """Set user status for an existing registration."""
        data = self._read()
        key = str(user_id)
        user = data["users"].get(key)
        if not isinstance(user, dict):
            return False, "User is not registered."

        normalized = status.strip().capitalize()
        if normalized not in ALLOWED_STATUSES:
            return False, "Invalid status. Allowed: Active, Suspended, Revoked."

        user["status"] = normalized
        self._write(data)
        return True, "Status updated successfully."

    def revoke_user(self, user_id: int) -> Tuple[bool, str]:
        """Mark user as revoked without removing historical record."""
        data = self._read()
        key = str(user_id)
        user = data["users"].get(key)
        if not isinstance(user, dict):
            return False, "User is not registered."

        user["status"] = "Revoked"
        self._write(data)
        return True, "User has been revoked."
