"""Simple file logger for prompts, usage, and runtime errors."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class BotLogger:
    """Append structured bot events to a local log file."""

    def __init__(self, file_path: str = "logs.txt") -> None:
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            self.file_path.write_text("", encoding="utf-8")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _append_line(self, line: str) -> None:
        with self.file_path.open("a", encoding="utf-8") as file:
            file.write(line)

    def log_prompt(
        self,
        user_id: int,
        username: str,
        prompt: str,
        model_used: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
    ) -> None:
        """Record prompt and token usage details."""
        line = (
            f"[{self._now_iso()}] user_id={user_id} username={username!r} "
            f"model={model_used} prompt={prompt!r} "
            f"tokens(prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens})\n"
        )
        self._append_line(line)

    def log_error(self, context: str, error: Exception) -> None:
        """Record unexpected runtime exceptions."""
        line = f"[{self._now_iso()}] ERROR context={context!r} detail={error!r}\n"
        self._append_line(line)
