import json
import os
from typing import List, Dict

from google import genai

from services.executor_service import ExecutorService


SECTION_ORDER = [
    "MISSION ANALYSIS:",
    "OBJECTIVE BREAKDOWN:",
    "EXECUTION STRATEGY:",
    "RISK ASSESSMENT:",
    "FINAL RECOMMENDATION:",
]

# Whitelist of safe intents for multi-step execution
SAFE_INTENTS = {
    "open_notepad", "open_calculator", "open_chrome", "open_edge",
    "open_word", "open_excel", "open_powerpoint", "open_explorer",
    "open_cmd", "open_settings", "open_task_manager", "open_whatsapp",
    "open_calendar", "open_vscode",
    "volume_up", "volume_down", "volume_mute",
    "take_screenshot", "create_text_file", "create_folder", "open_documents", "open_downloads",
    "get_time", "get_date", "calculate", "search_web", "get_weather",
    # Files
    "rename_file", "move_file", "delete_file",
    # Memory
    "memory_remember", "memory_recall", "memory_forget",
    # Reminders
    "reminder_in_minutes", "reminder_at", "reminder_list",
    # Computer control
    "computer_type", "computer_press", "computer_hotkey",
    # Email
    "send_email",
}


class GeminiService:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        self._client = genai.Client(api_key=api_key)
        self._model = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")

    def _build_prompt(self, user_message: str, history: List[Dict[str, str]]) -> str:
        system = (
            "You are NeuroPilot, an autonomous AI mission operator. "
            "You must respond in a clean, readable plain-text format with the EXACT section headers below, "
            "in this order, each on its own line, followed by concise bullet points or short paragraphs.\n\n"
            "MISSION ANALYSIS:\n"
            "OBJECTIVE BREAKDOWN:\n"
            "EXECUTION STRATEGY:\n"
            "RISK ASSESSMENT:\n"
            "FINAL RECOMMENDATION:\n\n"
            "Rules:\n"
            "- Do not include any extra top-level headings outside the five required headers.\n"
            "- Keep output scannable. Prefer short bullets.\n"
            "- If user input is vague, ask up to 2 clarifying questions inside OBJECTIVE BREAKDOWN.\n"
        )

        transcript_lines: List[str] = []
        for turn in history:
            role = turn.get("role", "")
            text = (turn.get("text") or "").strip()
            if not text:
                continue
            if role == "user":
                transcript_lines.append(f"USER: {text}")
            else:
                transcript_lines.append(f"NEUROPILOT: {text}")

        transcript = "\n".join(transcript_lines).strip()
        if transcript:
            transcript = "PREVIOUS CONTEXT:\n" + transcript + "\n\n"

        return f"{system}\n{transcript}CURRENT USER MESSAGE:\n{user_message.strip()}\n"

    def _ensure_sections(self, text: str) -> str:
        """Ensure the response has the required mission sections."""
        required = ["MISSION ANALYSIS:", "OBJECTIVE BREAKDOWN:", "EXECUTION STRATEGY:", "RISK ASSESSMENT:", "FINAL RECOMMENDATION:"]
        missing = [r for r in required if r not in text]
        
        if not missing:
            return text
            
        # If it's a direct conversational response, don't force sections
        if len(text.split('\n')) < 5 and not any(r in text for r in required):
            return text

        result = text
        for m in missing:
            result += f"\n\n{m}\n- Data point initialized."
        return result

    def generate_mission_response(self, user_message: str, history: List[Dict[str, str]]) -> str:
        prompt = self._build_prompt(user_message=user_message, history=history)

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )

        return self._ensure_sections(getattr(response, "text", ""))

    def generate_chat_response(self, user_message: str, history: List[Dict[str, str]]) -> str:
        """
        Generate a natural, conversational AI response like ChatGPT/Gemini.
        
        Used for general questions and information requests.
        Returns plain, helpful responses without the mission format structure.
        
        Args:
            user_message: The user's question or message
            history: Chat history for context
            
        Returns:
            Natural conversational response string
        """
        # Build context from history
        transcript_lines: List[str] = []
        for turn in history:
            role = turn.get("role", "")
            text = (turn.get("text") or "").strip()
            if not text:
                continue
            if role == "user":
                transcript_lines.append(f"User: {text}")
            else:
                transcript_lines.append(f"Assistant: {text}")

        transcript = "\n".join(transcript_lines).strip()
        if transcript:
            transcript = "Previous conversation:\n" + transcript + "\n\n"

        system_prompt = (
            "You are a helpful AI assistant. Provide clear, natural, conversational responses "
            "like ChatGPT or Google Gemini. Be friendly, informative, and concise.\n\n"
            "Guidelines:\n"
            "- Answer questions directly and helpfully\n"
            "- Use natural language, not structured formats\n"
            "- Be conversational but professional\n"
            "- If unsure, say so honestly\n"
            "- Keep responses concise but informative\n\n"
            f"{transcript}User: {user_message.strip()}\n\n"
            "Assistant:"
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=system_prompt,
            )
            
            return getattr(response, "text", "").strip()
        except Exception:
            return "I'm sorry, I couldn't process your request right now. Please try again."

    def classify_system_intent(self, message: str) -> str | None:
        """
        Classify user message into a system automation intent.

        Uses Gemini to determine if the message is requesting a local system action.
        Only returns predefined safe intents to prevent arbitrary command execution.

        Args:
            message: The user's input message.

        Returns:
            Intent string (open_notepad, open_calculator, take_screenshot, create_text_file)
            or "none" if no system intent detected.
            Returns None on API error.
        """
        # Whitelist of valid intents - safety check
        valid_intents = {
            "open_notepad", "open_calculator", "open_chrome", "open_edge",
            "open_word", "open_excel", "open_powerpoint", "open_explorer",
            "open_cmd", "open_settings", "open_task_manager", "open_whatsapp",
            "open_calendar",
            "volume_up", "volume_down", "volume_mute",
            "take_screenshot", "create_text_file", "open_documents", "open_downloads",
            "get_time", "get_date", "calculate", "search_web",
            "none"
        }

        allowed_fields_by_intent: dict[str, set[str]] = {
            # Memory
            "memory_remember": {"key", "value"},
            "memory_recall": {"key"},
            "memory_forget": {"key"},
            # Files
            "create_folder": {"name"},
            "rename_file": {"src", "dst"},
            "move_file": {"src", "dst"},
            "delete_file": {"path"},
            "file_find": {"query"}, # Keeping for backward compat
            # Reminders
            "reminder_in_minutes": {"minutes", "message"},
            "reminder_at": {"time", "message"},
            "reminder_list": set(),
            # Computer control
            "computer_type": {"text"},
            "computer_press": {"key"},
            "computer_hotkey": {"keys"},
            # Email
            "send_email": {"to", "subject", "body"},
        }

        system_prompt = (
            "You are an intent classifier for a system automation assistant. "
            "Classify the user message into exactly one of these categories:\n\n"
            # Applications
            "- open_notepad: User wants to open Notepad\n"
            "- open_calculator: User wants to open Calculator\n"
            "- open_chrome: User wants to open Google Chrome\n"
            "- open_edge: User wants to open Microsoft Edge\n"
            "- open_word: User wants to open Microsoft Word\n"
            "- open_excel: User wants to open Microsoft Excel\n"
            "- open_powerpoint: User wants to open Microsoft PowerPoint\n"
            "- open_explorer: User wants to open File Explorer\n"
            "- open_cmd: User wants to open Command Prompt\n"
            "- open_settings: User wants to open Windows Settings\n"
            "- open_task_manager: User wants to open Task Manager\n"
            "- open_whatsapp: User wants to open WhatsApp Desktop\n"
            "- open_calendar: User wants to open Calendar\n"
            # System control
            "- volume_up: User wants to increase system volume\n"
            "- volume_down: User wants to decrease system volume\n"
            "- volume_mute: User wants to mute system volume\n"
            # File operations
            "- take_screenshot: User wants to capture a screenshot\n"
            "- create_text_file: User wants to create a text file\n"
            "- open_documents: User wants to open Documents folder\n"
            "- open_downloads: User wants to open Downloads folder\n"
            # Utilities
            "- get_time: User wants to know current time\n"
            "- get_date: User wants to know current date\n"
            "- calculate: User wants to perform a calculation (e.g., 'calculate 5+5')\n"
            "- search_web: User wants to search the web (e.g., 'search for Python')\n"
            "- none: Message is not requesting any of the above system actions\n\n"
            "Rules:\n"
            "- Return ONLY the intent identifier (one word, no explanation)\n"
            "- If unclear or ambiguous, return 'none'\n"
            "- Never generate shell commands or executable code\n"
            "- Only classify as system intent if the user explicitly asks for the action\n\n"
            f"User message: {message.strip()}\n\n"
            "Intent:"
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=system_prompt,
            )

            intent = getattr(response, "text", "").strip().lower()

            # Safety: only return whitelisted intents
            if intent in valid_intents:
                return intent if intent != "none" else None
            return None

        except Exception:
            # On API error, default to None (no system intent)
            return None

    def plan_actions(self, user_message: str, history: List[Dict[str, str]]) -> dict:
        """
        Plan multi-step actions or determine if normal chat response needed.

        Uses Gemini to analyze the user request and decide whether to:
        - Execute a sequence of system commands (mode: "execute")
        - Provide a normal chat response (mode: "chat")

        Args:
            user_message: The user's input message.
            history: Chat history for context.

        Returns:
            dict with structure:
            {
                "mode": "execute",
                "actions": [{"intent": "open_notepad"}, ...]
            }
            or
            {
                "mode": "chat",
                "response": "Mission structured response..."
            }
        """
        canned_fallback = {
            "mode": "chat",
            "response": (
                "MISSION ANALYSIS:\n"
                "- Request received; AI planning channel may be unavailable or returned invalid data.\n\n"
                "OBJECTIVE BREAKDOWN:\n"
                "- Try a direct command: 'open notepad', 'open chrome and calculator'\n"
                "- Or ask a question directly.\n\n"
                "EXECUTION STRATEGY:\n"
                "- Use whitelisted system intents only.\n\n"
                "RISK ASSESSMENT:\n"
                "- Multi-step or computer/file-delete operations require confirmation.\n\n"
                "FINAL RECOMMENDATION:\n"
                "- Rephrase with specific actions or retry when network is stable."
            ),
        }

        # Build context from history
        transcript_lines: List[str] = []
        for turn in history:
            role = turn.get("role", "")
            text = (turn.get("text") or "").strip()
            if not text:
                continue
            if role == "user":
                transcript_lines.append(f"USER: {text}")
            else:
                transcript_lines.append(f"NEUROPILOT: {text}")

        transcript = "\n".join(transcript_lines).strip()
        if transcript:
            transcript = "PREVIOUS CONTEXT:\n" + transcript + "\n\n"

        # Available intents for AI to choose from
        available_intents = sorted(SAFE_INTENTS)
        # Add get_weather if not in SAFE_INTENTS for some reason, though it should be
        if "get_weather" not in available_intents:
            available_intents.append("get_weather")

        system_prompt = (
            "You are NeuroPilot, an autonomous AI mission operator with system automation capabilities. "
            "Analyze the user's request and respond with valid JSON only.\n\n"
            "DECISION RULES:\n"
            "1. If user wants system actions (open apps, screenshots, etc.):\n"
            "   Return: {\"mode\": \"execute\", \"actions\": [{\"intent\": \"action_name\"}, ...]}\n"
            "2. If user asks questions or wants conversation:\n"
            "   Return: {\"mode\": \"chat\", \"response\": \"Your natural, helpful answer here...\"}\n\n"
            "AVAILABLE SYSTEM INTENTS (execution only):\n"
            f"{', '.join(available_intents)}\n\n"
            "PARAMETER RULES (for execute mode):\n"
            "- memory_remember requires: key, value\n"
            "- memory_recall requires: key\n"
            "- memory_forget requires: key\n"
            "- create_folder requires: name\n"
            "- rename_file requires: src, dst\n"
            "- move_file requires: src, dst\n"
            "- delete_file requires: path (dangerous; requires confirmation)\n"
            "- reminder_in_minutes requires: minutes, message\n"
            "- reminder_at requires: time (HH:MM), message\n"
            "- computer_type requires: text (dangerous; requires confirmation)\n"
            "- computer_press requires: key (dangerous; requires confirmation)\n"
            "- computer_hotkey requires: keys (array of key names; dangerous; requires confirmation)\n"
            "- send_email requires: to, subject, body (dangerous; requires confirmation)\n"
            "- search_web requires: query\n"
            "- memory_remember requires: key, value\n"
            "- memory_recall requires: key\n"
            "- memory_forget requires: key\n"
            "RULES:\n"
            "- For multi-step: include multiple intents in actions array\n"
            "- For chat: provide natural, conversational responses like ChatGPT\n"
            "- Only use intents from AVAILABLE list for execute mode\n"
            "- If unsure, use chat mode with helpful guidance\n"
            "- Output MUST be valid JSON only, no markdown, no explanation outside JSON\n\n"
            "OUTPUT FORMAT EXAMPLES:\n"
            '{"mode": "execute", "actions": [{"intent": "open_notepad"}, {"intent": "open_chrome"}]}\n'
            '{"mode": "chat", "response": "Python is a versatile programming language..."}\n\n'
            f"{transcript}CURRENT USER MESSAGE:\n{user_message.strip()}\n\n"
            "JSON Response:"
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=system_prompt,
            )

            response_text = getattr(response, "text", "").strip()

            # Clean up markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON response
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Invalid JSON - fallback to chat with a generic mission response
                # Don't call generate_mission_response to avoid double API usage
                return {
                    "mode": "chat",
                    "response": (
                        "MISSION ANALYSIS:\n"
                        "- Request received; interpreting intent.\n\n"
                        "OBJECTIVE BREAKDOWN:\n"
                        "- Clarification needed for precise execution.\n\n"
                        "EXECUTION STRATEGY:\n"
                        "- Try specifying apps like: 'open notepad and chrome'\n"
                        "- Or ask for information directly.\n\n"
                        "RISK ASSESSMENT:\n"
                        "- Low risk; awaiting specific parameters.\n\n"
                        "FINAL RECOMMENDATION:\n"
                        "- Rephrase with specific system commands or questions."
                    )
                }

            # Validate structure
            if not isinstance(result, dict) or "mode" not in result:
                return canned_fallback

            mode = result.get("mode", "chat")

            if mode == "execute":
                # Validate actions against whitelist
                actions = result.get("actions", [])
                if not isinstance(actions, list):
                    actions = []

                valid_actions = []
                for action in actions:
                    if isinstance(action, dict) and "intent" in action:
                        intent = action["intent"].strip().lower()
                        if intent in SAFE_INTENTS:
                            clean: dict = {"intent": intent}
                            allowed_fields = allowed_fields_by_intent.get(intent)
                            if allowed_fields is not None:
                                for k in allowed_fields:
                                    if k in action:
                                        clean[k] = action.get(k)
                            valid_actions.append(clean)

                if valid_actions:
                    return {"mode": "execute", "actions": valid_actions}
                else:
                    # No valid actions, fallback to chat
                    return canned_fallback

            if mode == "chat":
                response_text = result.get("response", "")
                if not response_text:
                    return canned_fallback
                return {"mode": "chat", "response": response_text}

            return canned_fallback

        except Exception:
            # On any error, return a generic response without calling API again
            return canned_fallback

    def plan_goal(self, user_message: str, history: List[Dict[str, str]]) -> dict:
        """Convert a high-level goal into a list of executable local system actions.

        Output format:
            {
              "mode": "goal",
              "goal": "prepare coding environment",
              "actions": ["open_vscode", "open_chrome", "open_documents"]
            }

        Only returns intents that exist in ExecutorService.SAFE_INTENTS.
        """
        canned_fallback = {
            "mode": "chat",
            "response": (
                "MISSION ANALYSIS:\n"
                "- Goal planning channel returned invalid data or is unavailable.\n\n"
                "OBJECTIVE BREAKDOWN:\n"
                "- Try a direct command like: 'open vscode and chrome'.\n\n"
                "EXECUTION STRATEGY:\n"
                "- I can also generate a goal plan if Gemini is available.\n\n"
                "RISK ASSESSMENT:\n"
                "- Multi-step execution may require confirmation.\n\n"
                "FINAL RECOMMENDATION:\n"
                "- Rephrase your goal with the outcome you want."
            ),
        }

        transcript_lines: List[str] = []
        for turn in history:
            role = turn.get("role", "")
            text = (turn.get("text") or "").strip()
            if not text:
                continue
            if role == "user":
                transcript_lines.append(f"USER: {text}")
            else:
                transcript_lines.append(f"NEUROPILOT: {text}")

        transcript = "\n".join(transcript_lines).strip()
        if transcript:
            transcript = "PREVIOUS CONTEXT:\n" + transcript + "\n\n"

        available_intents = sorted(ExecutorService.SAFE_INTENTS)

        system_prompt = (
            "You are NeuroPilot operating in AUTONOMOUS GOAL MODE. "
            "Convert the user's high-level goal into a short, safe plan of local system actions. "
            "Return valid JSON only.\n\n"
            "OUTPUT FORMAT (JSON only):\n"
            '{"mode":"goal","goal":"...","actions":["intent1","intent2"]}\n\n'
            "RULES:\n"
            "- actions must ONLY contain intents from AVAILABLE_INTENTS\n"
            "- keep actions to 2-6 steps\n"
            "- prefer workspace setup actions (open apps/folders)\n"
            "- if goal is unclear, return mode=chat with a brief question in response\n\n"
            "AVAILABLE_INTENTS:\n"
            f"{', '.join(available_intents)}\n\n"
            f"{transcript}CURRENT USER GOAL:\n{user_message.strip()}\n\n"
            "JSON Response:"
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=system_prompt,
            )
            response_text = getattr(response, "text", "").strip()

            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                return canned_fallback

            if not isinstance(result, dict):
                return canned_fallback

            mode = str(result.get("mode") or "").strip().lower()
            if mode != "goal":
                if mode == "chat" and isinstance(result.get("response"), str) and result.get("response"):
                    return {"mode": "chat", "response": str(result.get("response"))}
                return canned_fallback

            goal = str(result.get("goal") or user_message).strip()
            actions = result.get("actions", [])
            if not isinstance(actions, list):
                actions = []

            valid_actions: list[str] = []
            for a in actions:
                if not isinstance(a, str):
                    continue
                intent = a.strip().lower()
                if intent in ExecutorService.SAFE_INTENTS:
                    valid_actions.append(intent)

            seen: set[str] = set()
            ordered: list[str] = []
            for i in valid_actions:
                if i in seen:
                    continue
                seen.add(i)
                ordered.append(i)

            if not ordered:
                return canned_fallback

            return {"mode": "goal", "goal": goal, "actions": ordered}
        except Exception:
            return canned_fallback
