"""
ExecutorService - Safe Local System Automation for NeuroPilot.

Executes predefined safe system commands based on AI-classified intent.
"""

import os
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Final, Any, List, Dict

from services.file_service import FileService
from services.internet_tool_service import InternetToolService
from services.email_service import EmailService


class ExecutorService:
    """
    Executes safe, predefined local system tasks based on intent classification.

    Only allows whitelisted intents. No arbitrary shell execution.
    Designed for Windows 10/11 compatibility.
    """

    SCREENSHOT_FILENAME: Final[str] = "screenshot.png"
    TEXT_FILE_NAME: Final[str] = "neuro_file.txt"

    # Whitelist of safe intents
    SAFE_INTENTS: Final[set[str]] = {
        # Applications
        "open_notepad", "open_calculator", "open_chrome", "open_edge",
        "open_word", "open_excel", "open_powerpoint", "open_explorer",
        "open_cmd", "open_settings", "open_task_manager", "open_whatsapp",
        "open_calendar",
        # System control
        "volume_up", "volume_down", "volume_mute",
        # File operations
        "take_screenshot", "create_text_file", "create_folder", "open_documents", "open_downloads",
        # Files (Renamed)
        "rename_file", "move_file", "delete_file",
        # Utilities
        "get_time", "get_date", "calculate", "search_web", "get_weather",
        # Workspace presets
        "open_vscode",
        # Computer
        "computer_type", "computer_press", "computer_hotkey",
        # Email
        "send_email",
    }

    # Keyword patterns for fast local intent detection (no API call needed)
    INTENT_PATTERNS: Final[dict[str, set[str]]] = {
        # Applications
        "open_notepad": {"open notepad", "launch notepad", "start notepad", "notepad"},
        "open_calculator": {"open calculator", "launch calculator", "start calculator", "open calc", "calculator", "calc"},
        "open_chrome": {"open chrome", "launch chrome", "start chrome", "open google chrome", "chrome"},
        "open_edge": {"open edge", "launch edge", "start edge", "open microsoft edge", "edge"},
        "open_word": {"open word", "launch word", "start word", "open microsoft word", "word"},
        "open_excel": {"open excel", "launch excel", "start excel", "open microsoft excel", "excel"},
        "open_powerpoint": {"open powerpoint", "launch powerpoint", "start powerpoint", "open ppt", "powerpoint", "ppt"},
        "open_explorer": {"open explorer", "launch explorer", "open file explorer", "open folder", "file explorer", "explorer"},
        "open_cmd": {"open cmd", "open command prompt", "launch cmd", "start command prompt", "command prompt", "cmd"},
        "open_settings": {"open settings", "launch settings", "open system settings", "settings"},
        "open_task_manager": {"open task manager", "launch task manager", "start task manager", "task manager"},
        "open_whatsapp": {"open whatsapp", "launch whatsapp", "start whatsapp", "open whats app", "whatsapp", "whats app"},
        "open_calendar": {"open calendar", "launch calendar", "start calendar", "open calender", "calendar", "calender"},
        # Workspace presets
        "open_vscode": {"open vscode", "open vs code", "launch vscode", "start vscode", "visual studio code", "vscode", "vs code"},
        # System control
        "volume_up": {"volume up", "increase volume", "turn up volume"},
        "volume_down": {"volume down", "decrease volume", "lower volume", "turn down volume"},
        "volume_mute": {"mute", "mute volume", "turn off sound"},
        # File operations
        "take_screenshot": {"take screenshot", "capture screenshot", "save screenshot", "screenshot"},
        "create_text_file": {"create file", "create text file", "make file", "create a file"},
        "create_folder": {"create folder", "create a folder", "make folder", "new folder"},
        "open_documents": {"open documents", "open my documents", "documents folder", "documents", "open my documents folder"},
        "open_downloads": {"open downloads", "open my downloads", "open downloads folder", "downloads folder", "downloads", "open my downloads folder"},
        # Utilities
        "get_time": {"what time", "current time", "time now", "tell me the time", "time"},
        "get_date": {"what date", "current date", "today's date", "what day is it", "date"},
        "calculate": {"calculate", "compute", "math", "how much is"},
        "search_web": {"search for", "search web", "google", "look up", "find online"},
        "get_weather": {"weather", "temperature", "forecast", "is it raining", "how is the weather"},
    }

    def __init__(self, working_dir: str | None = None) -> None:
        """
        Initialize ExecutorService.

        Args:
            working_dir: Directory for saving files (screenshots, text files).
                         Defaults to current working directory.
        """
        self._working_dir = Path(working_dir) if working_dir else Path.cwd()

    def execute(self, intent: str, message: str = "", action: dict | None = None) -> str | None:
        """
        Execute a system task based on the classified intent.

        Args:
            intent: The classified intent string (e.g., "open_notepad", "take_screenshot").
            message: Original user message (needed for some commands like calculate, search).

        Returns:
            Confirmation string like "SYSTEM ACTION: Notepad opened successfully."
            or None if intent is not recognized or not in whitelist.
        """
        intent = intent.strip().lower()

        # Safety check: only execute whitelisted intents
        if intent not in self.SAFE_INTENTS:
            return None

        # Applications
        if intent == "open_notepad":
            return self._open_notepad()
        if intent == "open_calculator":
            return self._open_calculator()
        if intent == "open_chrome":
            return self._open_chrome()
        if intent == "open_edge":
            return self._open_edge()
        if intent == "open_word":
            return self._open_word()
        if intent == "open_excel":
            return self._open_excel()
        if intent == "open_powerpoint":
            return self._open_powerpoint()
        if intent == "open_explorer":
            return self._open_explorer()
        if intent == "open_cmd":
            return self._open_cmd()
        if intent == "open_settings":
            return self._open_settings()
        if intent == "open_task_manager":
            return self._open_task_manager()
        if intent == "open_whatsapp":
            return self._open_whatsapp()
        if intent == "open_calendar":
            return self._open_calendar()
        if intent == "open_vscode":
            return self._open_vscode()

        # System control
        if intent == "volume_up":
            return self._volume_up()
        if intent == "volume_down":
            return self._volume_down()
        if intent == "volume_mute":
            return self._volume_mute()

        if intent == "create_folder":
            return self._create_folder(action or message)
        if intent == "rename_file":
            return self._rename_file(action)
        if intent == "move_file":
            return self._move_file(action)
        if intent == "delete_file":
            return self._delete_file(action)
        if intent == "open_documents":
            return self._open_documents()
        if intent == "open_downloads":
            return self._open_downloads()

        # Utilities
        if intent == "get_time":
            return self._get_time()
        if intent == "get_date":
            return self._get_date()
        if intent == "calculate":
            return self._calculate(message)
        if intent == "search_web":
            # Pass the full message so the tool can extract the query itself if the action dict is empty.
            return self._search_web_structured(message)
        if intent == "get_weather":
            return self._get_weather(message)

        # Computer
        if intent.startswith("computer_"):
            return self._computer_control(intent, action)

        # Email
        if intent == "send_email":
            return self._send_email(action)

        return None

    def _computer_control(self, intent: str, action: Any) -> str:
        try:
            from services.computer_control_service import ComputerControlService
            comp = ComputerControlService()
            if not isinstance(action, dict): action = {}
            if intent == "computer_type":
                res = comp.type_text(str(action.get("text") or ""))
            elif intent == "computer_press":
                res = comp.press_key(str(action.get("key") or ""))
            elif intent == "computer_hotkey":
                res = comp.hotkey(action.get("keys") or [])
            else:
                return f"SYSTEM ERROR: Unsupported computer intent {intent}"
            
            if res.get("ok"):
                return f"SYSTEM ACTION: {intent.replace('_', ' ').title()} executed."
            return f"SYSTEM ERROR: {res.get('error')}"
        except Exception as e:
            return f"SYSTEM ERROR: Computer control failed - {str(e)}"

    def _send_email(self, action: Any) -> str:
        if not isinstance(action, dict): return "SYSTEM ERROR: No email data."
        try:
            email_svc = EmailService()
            res = email_svc.send_email(
                to_addr=action.get("to", ""),
                subject=action.get("subject", ""),
                body=action.get("body", "")
            )
            if res.get("ok"):
                return f"SYSTEM ACTION: Email sent to {action.get('to')}."
            return f"SYSTEM ERROR: {res.get('error')}"
        except Exception as e:
            return f"SYSTEM ERROR: Email failed - {str(e)}"
    
    def _search_web_structured(self, param: Any) -> str:
        """
        Execute a structured web search. 
        Param can be an action dict or a raw message string.
        """
        query = ""
        # 1. Try to get query from dict
        if isinstance(param, dict):
            query = param.get("query") or ""
        
        # 2. If no query found (or param was a string), attempt local extraction from string
        if not query:
            search_context = param if isinstance(param, str) else ""
            # If param was a dict and query was empty, search_context is empty here.
            # But execute() usually passes message string when local intents are detected.
            if search_context:
                query = self._extract_search_query(search_context)
            
        if not query:
            return "SYSTEM ERROR: No search query identified in your request."
            
        try:
            from services.web_intelligence_service import WebIntelligenceService
            wi_svc = WebIntelligenceService()
            import asyncio
            
            # Handle the async search call
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import threading
                    result_wrapper = []
                    def run_in_thread():
                        result_wrapper.append(asyncio.run(wi_svc.search(query)))
                    t = threading.Thread(target=run_in_thread)
                    t.start()
                    t.join()
                    res = result_wrapper[0]
                else:
                    res = loop.run_until_complete(wi_svc.search(query))
            except RuntimeError:
                res = asyncio.run(wi_svc.search(query))
                
            if res.get("ok"):
                return f"SYSTEM ACTION: {res.get('summary')}"
            return f"SYSTEM ERROR: {res.get('error')}"
        except Exception as e:
            return f"SYSTEM ERROR: Search failed - {str(e)}"

    def detect_intent(self, message: str) -> str | None:
        """
        Fast keyword-based intent detection (no API call required).

        Args:
            message: User's input message.

        Returns:
            Intent string if keyword match found, None otherwise.
        """
        text = message.strip().lower()

        for intent, patterns in self.INTENT_PATTERNS.items():
            if any(pattern in text for pattern in patterns):
                return intent

        return None

    def detect_intents(self, message: str) -> list[str]:
        """
        Detect multiple intents from natural language using keyword matching.
        Preserves the order of appearance in the message.
        """
        text = message.strip().lower()
        has_open_verb = any(v in text for v in ("open ", "launch ", "start "))
        
        # Track (position, intent) pairs
        found: list[tuple[int, str]] = []

        # Special-case folder creation
        folder_name = self._extract_folder_name(message)
        if folder_name is not None:
            # Approximate position (usually at the start of the command)
            found.append((text.find("create") if "create" in text else 0, "create_folder"))

        for intent, patterns in self.INTENT_PATTERNS.items():
            if intent == "create_folder":
                continue
            for pattern in patterns:
                if pattern in text:
                    # Guardrail: single-word patterns for open_* intents should only match
                    # when the user is clearly asking to open something.
                    if " " not in pattern and intent.startswith("open_") and not has_open_verb:
                        continue
                    
                    # Find all occurrences of this pattern
                    pos = text.find(pattern)
                    found.append((pos, intent))
                    break # Only one pattern per intent

        # Sort by position and remove duplicates
        found.sort()
        
        seen: set[str] = set()
        ordered_unique: list[str] = []
        for _, intent in found:
            if intent not in seen:
                seen.add(intent)
                ordered_unique.append(intent)

        return ordered_unique

    def get_preset_actions(self, preset_name: str) -> list | None:
        """
        Get predefined workspace preset actions.

        Args:
            preset_name: Name of the preset (coding_mode, research_mode, presentation_mode).

        Returns:
            List of action dictionaries for the preset, or None if preset not found.
        """
        presets = {
            "coding_mode": [
                {"intent": "open_vscode"},
                {"intent": "open_chrome"},
                {"intent": "open_documents"},
                {"intent": "create_text_file"},
                {"intent": "get_time"},
            ],
            "research_mode": [
                {"intent": "open_chrome"},
                {"intent": "search_web"},
                {"intent": "open_downloads"},
                {"intent": "get_weather"},
                {"intent": "get_time"},
            ],
            "presentation_mode": [
                {"intent": "open_powerpoint"},
                {"intent": "open_chrome"},
                {"intent": "open_documents"},
                {"intent": "create_text_file"},
                {"intent": "get_date"},
            ],
        }
        return presets.get(preset_name)

    # ============ APPLICATIONS ============

    def _open_vscode(self) -> str:
        """Open Visual Studio Code."""
        try:
            vscode_paths = [
                r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
                r"C:\Program Files\Microsoft VS Code\Code.exe",
                r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
            ]
            # Expand environment variables
            expanded_paths = [Path(os.path.expandvars(p)) for p in vscode_paths]
            for path in expanded_paths:
                if path.exists():
                    os.startfile(str(path))
                    return "SYSTEM ACTION: Visual Studio Code opened successfully."
            # Try using 'code' command as fallback
            subprocess.Popen(["code"], shell=True)
            return "SYSTEM ACTION: Visual Studio Code opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open VS Code - {str(e)}"

    def _open_notepad(self) -> str:
        """Open Windows Notepad."""
        try:
            os.startfile("notepad.exe")
            return "SYSTEM ACTION: Notepad opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open Notepad - {str(e)}"

    def _open_calculator(self) -> str:
        """Open Windows Calculator."""
        try:
            os.startfile("calc.exe")
            return "SYSTEM ACTION: Calculator opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open Calculator - {str(e)}"

    def _open_chrome(self) -> str:
        """Open Google Chrome."""
        try:
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            for path in chrome_paths:
                if Path(path).exists():
                    os.startfile(path)
                    return "SYSTEM ACTION: Google Chrome opened successfully."
            # Try using 'start chrome' as fallback with a flag to help bypass profile selector if possible
            subprocess.Popen(["start", "chrome", "--no-first-run"], shell=True)
            return "SYSTEM ACTION: Google Chrome opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open Chrome - {str(e)}"

    def _open_edge(self) -> str:
        """Open Microsoft Edge."""
        try:
            os.startfile("msedge.exe")
            return "SYSTEM ACTION: Microsoft Edge opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open Edge - {str(e)}"

    def _open_word(self) -> str:
        """Open Microsoft Word."""
        try:
            os.startfile("winword.exe")
            return "SYSTEM ACTION: Microsoft Word opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open Word - {str(e)}"

    def _open_excel(self) -> str:
        """Open Microsoft Excel."""
        try:
            os.startfile("excel.exe")
            return "SYSTEM ACTION: Microsoft Excel opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open Excel - {str(e)}"

    def _open_powerpoint(self) -> str:
        """Open Microsoft PowerPoint."""
        try:
            os.startfile("powerpnt.exe")
            return "SYSTEM ACTION: Microsoft PowerPoint opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open PowerPoint - {str(e)}"

    def _open_explorer(self) -> str:
        """Open File Explorer."""
        try:
            os.startfile("explorer.exe")
            return "SYSTEM ACTION: File Explorer opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open File Explorer - {str(e)}"

    def _open_cmd(self) -> str:
        """Open Command Prompt."""
        try:
            os.startfile("cmd.exe")
            return "SYSTEM ACTION: Command Prompt opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open Command Prompt - {str(e)}"

    def _open_settings(self) -> str:
        """Open Windows Settings."""
        try:
            os.startfile("ms-settings:")
            return "SYSTEM ACTION: Settings opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open Settings - {str(e)}"

    def _open_task_manager(self) -> str:
        """Open Task Manager."""
        try:
            os.startfile("taskmgr.exe")
            return "SYSTEM ACTION: Task Manager opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open Task Manager - {str(e)}"

    def _open_whatsapp(self) -> str:
        """Open WhatsApp Desktop application."""
        try:
            os.startfile("whatsapp:")
            return "SYSTEM ACTION: WhatsApp opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open WhatsApp - {str(e)}"

    def _open_calendar(self) -> str:
        """Open Windows Calendar."""
        try:
            os.startfile("outlookcal:")
            return "SYSTEM ACTION: Calendar opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open Calendar - {str(e)}"

    # ============ SYSTEM CONTROL ============

    def _volume_up(self) -> str:
        """Increase system volume."""
        try:
            import ctypes
            # VK_VOLUME_UP = 0xAF
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
            return "SYSTEM ACTION: Volume increased."
        except Exception:
            # Fallback to nircmd if available, or return info
            return "SYSTEM ACTION: Volume up command sent."

    def _volume_down(self) -> str:
        """Decrease system volume."""
        try:
            import ctypes
            # VK_VOLUME_DOWN = 0xAE
            ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
            return "SYSTEM ACTION: Volume decreased."
        except Exception:
            return "SYSTEM ACTION: Volume down command sent."

    def _volume_mute(self) -> str:
        """Mute system volume."""
        try:
            import ctypes
            # VK_VOLUME_MUTE = 0xAD
            ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
            return "SYSTEM ACTION: Volume muted."
        except Exception:
            return "SYSTEM ACTION: Mute command sent."

    # ============ FILE OPERATIONS ============

    def _take_screenshot(self) -> str:
        """Capture and save screenshot using Windows native methods."""
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            save_dir = Path.home()
            filepath = save_dir / self.SCREENSHOT_FILENAME
            screenshot.save(filepath)
            return f"SYSTEM ACTION: Screenshot captured and saved to {filepath}"
        except Exception as e:
            return f"SYSTEM ERROR: Failed to capture screenshot - {str(e)}"

    def _create_text_file(self) -> str:
        """Create a text file with default content."""
        try:
            filepath = self._working_dir / self.TEXT_FILE_NAME
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("File created by NeuroPilot.")
            return f"SYSTEM ACTION: Text file '{filepath.name}' created successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to create file - {str(e)}"

    def _extract_folder_name(self, message: str) -> str | None:
        """Extract a folder name from common offline commands."""
        import re

        text = (message or "").strip()
        if not text:
            return None

        patterns = [
            r"^create\s+folder\s+(.+)$",
            r"^create\s+a\s+folder\s+called\s+(.+)$",
            r"^create\s+a\s+folder\s+named\s+(.+)$",
            r"^make\s+folder\s+(.+)$",
            r"^new\s+folder\s+(.+)$",
        ]

        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                name = (m.group(1) or "").strip().strip("\"'")
                return name or None

        return None

    def _is_safe_folder_name(self, name: str) -> bool:
        """Basic safety validation for folder names."""
        if not name or not isinstance(name, str):
            return False
        bad = {"/", ":", "*"}
        if any(ch in name for ch in bad):
            return False
        if ".." in name or "\\" in name:
            return False
        if name.strip() != name:
            return False
        return True

    def _create_folder(self, param: Any) -> str:
        """Create a folder under working directory."""
        folder_name = None
        if isinstance(param, dict):
            folder_name = param.get("name")
        else:
            folder_name = self._extract_folder_name(param)
            
        if folder_name is None:
            return "SYSTEM ERROR: Folder name missing."

        if not self._is_safe_folder_name(folder_name):
            return "SYSTEM ERROR: Invalid folder name. Avoid '/', ':', '*'."

        # Ensure folders are created inside a safe root.
        # Prefer working directory; fall back to user home if cwd isn't usable.
        root = self._working_dir
        try:
            root.mkdir(parents=True, exist_ok=True)
            test_path = root / ".neuro_write_test"
            test_path.touch(exist_ok=True)
            test_path.unlink(missing_ok=True)
        except Exception:
            root = Path.home()

        try:
            files = FileService(allowed_root=str(root))
            res = files.create_folder(folder_name)
            if res.get("ok"):
                return f"SYSTEM ACTION: Folder '{folder_name}' created successfully."
            return f"SYSTEM ERROR: Failed to create folder - {res.get('error') or 'Unknown error'}"
        except PermissionError:
            return "SYSTEM ERROR: Folder path is outside allowed root."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to create folder - {str(e)}"

    def _rename_file(self, action: dict | None) -> str:
        if not action: return "SYSTEM ERROR: Missing parameters."
        src = action.get("src")
        dst = action.get("dst")
        if not src or not dst: return "SYSTEM ERROR: Missing src or dst."
        try:
            files = FileService(allowed_root=str(self._working_dir))
            res = files.rename_path(src, dst)
            if res.get("ok"): return f"SYSTEM ACTION: Renamed {src} to {dst}."
            return f"SYSTEM ERROR: {res.get('error')}"
        except Exception as e: return f"SYSTEM ERROR: {str(e)}"

    def _move_file(self, action: dict | None) -> str:
        if not action: return "SYSTEM ERROR: Missing parameters."
        src = action.get("src")
        dst = action.get("dst")
        if not src or not dst: return "SYSTEM ERROR: Missing src or dst."
        try:
            files = FileService(allowed_root=str(self._working_dir))
            res = files.move_path(src, dst)
            if res.get("ok"): return f"SYSTEM ACTION: Moved {src} to {dst}."
            return f"SYSTEM ERROR: {res.get('error')}"
        except Exception as e: return f"SYSTEM ERROR: {str(e)}"

    def _delete_file(self, action: dict | None) -> str:
        if not action: return "SYSTEM ERROR: Missing parameters."
        path = action.get("path")
        if not path: return "SYSTEM ERROR: No path provided."
        try:
            files = FileService(allowed_root=str(self._working_dir))
            res = files.delete_path(path)
            if res.get("ok"): return f"SYSTEM ACTION: Deleted {path}."
            return f"SYSTEM ERROR: {res.get('error')}"
        except Exception as e: return f"SYSTEM ERROR: {str(e)}"
    def _open_documents(self) -> str:
        """Open Documents folder."""
        try:
            documents_path = Path.home() / "Documents"
            os.startfile(str(documents_path))
            return "SYSTEM ACTION: Documents folder opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open Documents - {str(e)}"

    def _open_downloads(self) -> str:
        """Open Downloads folder."""
        try:
            downloads_path = Path.home() / "Downloads"
            os.startfile(str(downloads_path))
            return "SYSTEM ACTION: Downloads folder opened successfully."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to open Downloads - {str(e)}"

    # ============ UTILITIES ============

    def _get_time(self) -> str:
        """Get current time."""
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        return f"SYSTEM INFO: Current time is {time_str}."

    def _get_date(self) -> str:
        """Get current date."""
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        return f"SYSTEM INFO: Today is {date_str}."

    def _calculate(self, message: str) -> str:
        """Perform simple calculation from user message."""
        try:
            import re
            # Stricter regex: must contain at least one operator and digits
            # Match patterns like "5+5", "10 * 2", "calculate 100/4"
            expr_match = re.search(r'\d+\s*[+\-*/]\s*\d+', message)
            if expr_match:
                expr = expr_match.group().strip()
                # Safely evaluate
                result = eval(expr)
                return f"SYSTEM RESULT: {expr} = {result}"
            return None  # Not a valid calculation, let AI handle it
        except Exception:
            return None  # Let AI handle calculation errors

    def _extract_search_query(self, message: str) -> str | None:
        """Extract a search query from common offline commands."""
        import re
        
        # Patterns: "search for X", "search X", "google X", "look up X", "find X"
        patterns = [
            r'search\s+for\s+(.+)',
            r'search\s+(.+)',
            r'google\s+(.+)',
            r'look\s+up\s+(.+)',
            r'find\s+(.+)',
            r'(?:search|google|find)\s+(.+)', 
        ]
        
        text = message.strip()
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                query = match.group(1).strip()
                # If there's an 'and' followed by common intents, stop there.
                # Example: "search for cats and open chrome" -> "cats"
                split_patterns = [r'\s+and\s+open\s+', r'\s+and\s+launch\s+', r'\s+and\s+start\s+', r'\s+and\s+create\s+']
                for sp in split_patterns:
                    query = re.split(sp, query, flags=re.IGNORECASE)[0]
                
                # Global 'and' split as last resort
                if " and " in query.lower():
                     query = re.split(r'\s+and\s+', query, flags=re.IGNORECASE)[0]
                     
                return query.strip() or None
        
        return None

    def _search_web(self, message: str) -> str:
        """Open browser with Google search for the query."""
        try:
            import urllib.parse
            
            query = self._extract_search_query(message)
            
            if not query:
                # If no pattern matched, use the whole message (minus common words)
                query = message.strip()
                # Remove common prefixes
                for prefix in ['search', 'google', 'look up', 'find']:
                    if query.lower().startswith(prefix):
                        query = query[len(prefix):].strip()
            
            if not query:
                return "SYSTEM ERROR: No search query."

            # Encode for URL
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://www.google.com/search?q={encoded_query}"
            
            # Open browser with search
            os.startfile(search_url)
            return f"SYSTEM ACTION: Opened browser with search for '{query}'."
        except Exception as e:
            return f"SYSTEM ERROR: Failed to perform search - {str(e)}"

    def _get_weather(self, message: str) -> str:
        """Fetch weather data using python-weather (wttr.in)."""
        import asyncio
        import python_weather
        import re

        async def fetch():
            async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
                # Try to extract city, otherwise default to "New York" or local if supported
                city_match = re.search(r'(in|for|at)\s+([a-zA-Z\s]+)', message, re.IGNORECASE)
                location = city_match.group(2).strip() if city_match else "New York"
                
                weather = await client.get(location)
                return f"SYSTEM HUD: Weather in {location}: {weather.temperature}°F, {weather.description}."

        try:
            # Handle cases where we might already be in an event loop or need a new one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # This is tricky in Flask, but for now we'll try to run it
                    import threading
                    result = []
                    def run_in_thread():
                        result.append(asyncio.run(fetch()))
                    t = threading.Thread(target=run_in_thread)
                    t.start()
                    t.join()
                    return result[0]
                return loop.run_until_complete(fetch())
            except RuntimeError:
                return asyncio.run(fetch())
        except Exception as e:
            error_str = str(e).lower()
            # Check for network/connectivity errors
            if any(keyword in error_str for keyword in ["cannot connect", "timeout", "ssl", "network", "unreachable"]):
                return "SYSTEM INFO: Weather service temporarily unavailable. Please check your internet connection or try again later."
            return f"SYSTEM ERROR: Weather fetch failed - {str(e)}"

    def execute_multiple(self, actions: list, message: str = "") -> dict:
        """
        Execute multiple system actions in sequence.

        Args:
            actions: List of action dicts, each with "intent" key.
                    Example: [{"intent": "open_notepad"}, {"intent": "open_chrome"}]
            message: Original user message (for commands that need context like calculate/search).

        Returns:
            Structured execution result:
            {
              "summary": "Execution completed.",
              "steps": [
                {"intent": "open_notepad", "status": "success"},
                {"intent": "open_chrome", "status": "error", "error": "..."}
              ]
            }
        """
        if not actions or not isinstance(actions, list):
            return {
                "summary": "Execution failed.",
                "steps": [{"intent": "unknown", "status": "error", "error": "No valid actions provided."}],
            }

        steps: list[dict] = []
        executed_count = 0
        failed_count = 0

        for action in actions:
            if not isinstance(action, dict) or "intent" not in action:
                steps.append({"intent": "unknown", "status": "error", "error": "Invalid action format."})
                failed_count += 1
                continue

            intent = str(action["intent"]).strip().lower()

            # Safety check: only execute whitelisted intents
            if intent not in self.SAFE_INTENTS:
                steps.append({"intent": intent, "status": "error", "error": "Intent not allowed."})
                failed_count += 1
                continue

            result = self.execute(intent, message, action=action)
            if result is None:
                steps.append({"intent": intent, "status": "error", "error": "Execution returned no result."})
                failed_count += 1
                continue

            if isinstance(result, str) and result.startswith("SYSTEM ERROR:"):
                steps.append({"intent": intent, "status": "error", "error": result})
                failed_count += 1
                continue

            steps.append({"intent": intent, "status": "success"})
            executed_count += 1

        total = len(steps)
        summary = f"Execution completed. ({executed_count}/{total} successful)"
        if failed_count:
            summary += f" - {failed_count} error(s)"

        return {"summary": summary, "steps": steps}
