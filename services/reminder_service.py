from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class Reminder:
    id: str
    message: str
    due_ts: float
    created_ts: float
    fired: bool


class ReminderService:
    def __init__(self, store_path: str | None = None) -> None:
        base = Path(store_path) if store_path else Path(__file__).resolve().parent.parent / "data" / "reminders.json"
        self._path = base
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text(json.dumps({"reminders": [], "notifications": []}, indent=2), encoding="utf-8")

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="ReminderService", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _read_store(self) -> dict[str, Any]:
        try:
            raw = self._path.read_text(encoding="utf-8").strip()
            if not raw:
                return {"reminders": [], "notifications": []}
            data = json.loads(raw)
            if not isinstance(data, dict):
                return {"reminders": [], "notifications": []}
            data.setdefault("reminders", [])
            data.setdefault("notifications", [])
            return data
        except Exception:
            return {"reminders": [], "notifications": []}

    def _write_store(self, data: dict[str, Any]) -> None:
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, self._path)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:
                pass
            time.sleep(1.0)

    def _tick(self) -> None:
        now_ts = time.time()
        with self._lock:
            store = self._read_store()
            reminders = store.get("reminders") or []
            notifications = store.get("notifications") or []
            changed = False

            for r in reminders:
                if not isinstance(r, dict):
                    continue
                if r.get("fired") is True:
                    continue
                due = r.get("due_ts")
                if isinstance(due, (int, float)) and float(due) <= now_ts:
                    r["fired"] = True
                    notifications.append(
                        {
                            "id": str(uuid.uuid4()),
                            "ts": now_ts,
                            "type": "reminder",
                            "message": str(r.get("message") or "Reminder"),
                        }
                    )
                    changed = True

            if changed:
                store["reminders"] = reminders
                store["notifications"] = notifications
                self._write_store(store)

    def add_in_minutes(self, minutes: int, message: str) -> dict[str, Any]:
        minutes = int(minutes)
        if minutes <= 0:
            raise ValueError("minutes must be > 0")
        msg = str(message).strip()
        if not msg:
            raise ValueError("message is required")

        now_ts = time.time()
        due_ts = now_ts + minutes * 60
        reminder = {
            "id": str(uuid.uuid4()),
            "message": msg,
            "due_ts": due_ts,
            "created_ts": now_ts,
            "fired": False,
        }

        with self._lock:
            store = self._read_store()
            reminders = store.get("reminders") or []
            reminders.append(reminder)
            store["reminders"] = reminders
            self._write_store(store)

        return reminder

    def add_at_hhmm(self, hhmm: str, message: str) -> dict[str, Any]:
        msg = str(message).strip()
        if not msg:
            raise ValueError("message is required")

        parts = str(hhmm).strip().split(":")
        if len(parts) != 2:
            raise ValueError("time must be HH:MM")
        hour = int(parts[0])
        minute = int(parts[1])
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("time must be HH:MM")

        now = datetime.now()
        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if due <= now:
            due = due + timedelta(days=1)

        now_ts = time.time()
        reminder = {
            "id": str(uuid.uuid4()),
            "message": msg,
            "due_ts": due.timestamp(),
            "created_ts": now_ts,
            "fired": False,
        }

        with self._lock:
            store = self._read_store()
            reminders = store.get("reminders") or []
            reminders.append(reminder)
            store["reminders"] = reminders
            self._write_store(store)

        return reminder

    def list_reminders(self) -> list[dict[str, Any]]:
        with self._lock:
            store = self._read_store()
            reminders = store.get("reminders") or []
            clean: list[dict[str, Any]] = []
            for r in reminders:
                if isinstance(r, dict):
                    clean.append(r)
            return clean

    def pop_notifications(self, limit: int = 10) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 50))
        with self._lock:
            store = self._read_store()
            notifications = store.get("notifications") or []
            clean = [n for n in notifications if isinstance(n, dict)]
            out = clean[:limit]
            store["notifications"] = clean[len(out):]
            self._write_store(store)
            return out
