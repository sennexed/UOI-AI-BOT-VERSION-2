"""Persistent token tracking and daily reset handling."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict


class TokenManager:
    """Track and persist token usage statistics."""

    def __init__(self, file_path: str = "token_stats.json") -> None:
        self.file_path = Path(file_path)
        self._ensure_file()

    def _default_stats(self) -> Dict[str, int | str]:
        return {
            "total_prompt": 0,
            "total_completion": 0,
            "total_tokens": 0,
            "daily_prompt": 0,
            "daily_completion": 0,
            "daily_tokens": 0,
            "last_reset_date": "",
        }

    def _today_utc(self) -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _ensure_file(self) -> None:
        if not self.file_path.exists():
            self._write(self._default_stats())

    def _read(self) -> Dict[str, int | str]:
        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            default = self._default_stats()
            for key, value in default.items():
                data.setdefault(key, value)
            return data
        except (json.JSONDecodeError, OSError):
            return self._default_stats()

    def _write(self, data: Dict[str, int | str]) -> None:
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    def _reset_daily_if_needed(self, data: Dict[str, int | str]) -> Dict[str, int | str]:
        today = self._today_utc()
        if data.get("last_reset_date") != today:
            data["daily_prompt"] = 0
            data["daily_completion"] = 0
            data["daily_tokens"] = 0
            data["last_reset_date"] = today
        return data

    def update_usage(self, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> Dict[str, int | str]:
        """Update persistent totals and return latest stats."""
        data = self._reset_daily_if_needed(self._read())

        data["total_prompt"] = int(data["total_prompt"]) + prompt_tokens
        data["total_completion"] = int(data["total_completion"]) + completion_tokens
        data["total_tokens"] = int(data["total_tokens"]) + total_tokens

        data["daily_prompt"] = int(data["daily_prompt"]) + prompt_tokens
        data["daily_completion"] = int(data["daily_completion"]) + completion_tokens
        data["daily_tokens"] = int(data["daily_tokens"]) + total_tokens

        self._write(data)
        return data

    def get_stats(self) -> Dict[str, int | str]:
        """Return current stats after applying daily reset rule."""
        data = self._reset_daily_if_needed(self._read())
        self._write(data)
        return data
