"""Persistent repository memory manager."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


class RepositoryManager:
    """Store and retrieve global long-term memory entries."""

    def __init__(self, file_path: str = "repository.json") -> None:
        self.file_path = Path(file_path)
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.file_path.exists():
            self.file_path.write_text(json.dumps({"global_memory": []}, indent=2), encoding="utf-8")

    def _read(self) -> Dict[str, List[Dict[str, str]]]:
        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict) or "global_memory" not in data:
                return {"global_memory": []}
            if not isinstance(data["global_memory"], list):
                data["global_memory"] = []
            return data
        except (json.JSONDecodeError, OSError):
            return {"global_memory": []}

    def _write(self, data: Dict[str, List[Dict[str, str]]]) -> None:
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

    def add_entry(self, content: str) -> None:
        """Persist a memory entry with a UTC timestamp."""
        data = self._read()
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content": content,
        }
        data["global_memory"].append(entry)
        self._write(data)

    def get_latest_entries(self, limit: int = 3) -> List[Dict[str, str]]:
        """Return most recent repository memory entries first."""
        data = self._read()
        entries = data.get("global_memory", [])
        if not isinstance(entries, list):
            return []
        return list(reversed(entries[-limit:]))
