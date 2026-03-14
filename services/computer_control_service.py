from __future__ import annotations

import time
from typing import Any


class ComputerControlService:
    def __init__(self) -> None:
        try:
            import pyautogui  # type: ignore
        except Exception as exc:
            raise RuntimeError("pyautogui is required for ComputerControlService") from exc

        self._pyautogui = pyautogui

        # Safety defaults
        self._pyautogui.FAILSAFE = True
        self._pyautogui.PAUSE = 0.06

        self._allowed_keys: set[str] = {
            "enter",
            "tab",
            "esc",
            "escape",
            "backspace",
            "delete",
            "space",
            "up",
            "down",
            "left",
            "right",
            "home",
            "end",
            "pageup",
            "pagedown",
            "win",
            "command",
            "ctrl",
            "alt",
            "shift",
            "capslock",
            "f1",
            "f2",
            "f3",
            "f4",
            "f5",
            "f6",
            "f7",
            "f8",
            "f9",
            "f10",
            "f11",
            "f12",
        }

    def type_text(self, text: str) -> dict[str, Any]:
        t = str(text)
        if not t.strip():
            return {"ok": False, "error": "No text provided."}

        # Small extra delay before typing so user can refocus window after confirming
        time.sleep(0.35)
        try:
            self._pyautogui.write(t, interval=0.01)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def press_key(self, key: str) -> dict[str, Any]:
        k = str(key).strip().lower()
        if not k:
            return {"ok": False, "error": "No key provided."}
        if k not in self._allowed_keys and len(k) != 1:
            return {"ok": False, "error": "Key not allowed."}

        time.sleep(0.2)
        try:
            self._pyautogui.press(k)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def hotkey(self, keys: list[str]) -> dict[str, Any]:
        clean: list[str] = []
        for k in keys:
            ks = str(k).strip().lower()
            if not ks:
                continue
            if ks not in self._allowed_keys and len(ks) != 1:
                return {"ok": False, "error": "Hotkey contains disallowed key."}
            clean.append(ks)

        if len(clean) < 2:
            return {"ok": False, "error": "Hotkey requires 2+ keys."}

        time.sleep(0.25)
        try:
            self._pyautogui.hotkey(*clean)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
