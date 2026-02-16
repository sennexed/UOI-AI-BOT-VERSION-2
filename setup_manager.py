"""Guild setup persistence manager."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional


class SetupManager:
    """Manage per-guild allowed channel configuration."""

    def __init__(self, file_path: str = "setup_config.json") -> None:
        self.file_path = Path(file_path)
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.file_path.exists():
            self._write({"guild_channels": {}})

    def _read(self) -> Dict[str, Dict[str, int]]:
        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict) or "guild_channels" not in data:
                return {"guild_channels": {}}
            if not isinstance(data["guild_channels"], dict):
                data["guild_channels"] = {}
            return data
        except (json.JSONDecodeError, OSError):
            return {"guild_channels": {}}

    def _write(self, data: Dict[str, Dict[str, int]]) -> None:
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    def set_channel(self, guild_id: int, channel_id: int) -> None:
        data = self._read()
        data["guild_channels"][str(guild_id)] = channel_id
        self._write(data)

    def get_channel(self, guild_id: int) -> Optional[int]:
        data = self._read()
        value = data["guild_channels"].get(str(guild_id))
        if value is None:
            return None
        return int(value)

    def unset_channel(self, guild_id: int) -> None:
        data = self._read()
        data["guild_channels"].pop(str(guild_id), None)
        self._write(data)
      
