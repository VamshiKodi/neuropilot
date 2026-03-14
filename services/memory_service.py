from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class MemoryService:
    def __init__(self, memory_path: str | None = None) -> None:
        base = Path(memory_path) if memory_path else Path(__file__).resolve().parent.parent / "data" / "memory.json"
        self._path = base
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def _read_all(self) -> dict[str, Any]:
        try:
            raw = self._path.read_text(encoding="utf-8").strip()
            if not raw:
                return {}
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_all(self, data: dict[str, Any]) -> None:
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, self._path)

    def remember(self, key: str, value: str) -> None:
        key = str(key).strip().lower()
        value = str(value).strip()
        if not key:
            raise ValueError("Key is required")
        data = self._read_all()
        data[key] = value
        self._write_all(data)

    def recall(self, key: str) -> str | None:
        key = str(key).strip().lower()
        if not key:
            return None
        data = self._read_all()
        val = data.get(key)
        return str(val) if val is not None else None

    def forget(self, key: str) -> bool:
        key = str(key).strip().lower()
        if not key:
            return False
        data = self._read_all()
        if key not in data:
            return False
        data.pop(key, None)
        self._write_all(data)
        return True
