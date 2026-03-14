from __future__ import annotations

from typing import Any, Dict, List

from flask import Blueprint, jsonify, request, session

from services.executor_service import ExecutorService
from services.gemini_service import GeminiService
from services.system_monitor_service import SystemMonitorService
from services.memory_service import MemoryService
from services.file_service import FileService
from services.reminder_service import ReminderService
from services.computer_control_service import ComputerControlService
from services.email_service import EmailService
from services.web_intelligence_service import WebIntelligenceService
from services.agent_service import AgentService
from services.tool_router_service import ToolRouterService
from services.internet_tool_service import InternetToolService

from services.wake_word_service import WakeWordService


api_bp = Blueprint("api", __name__, url_prefix="/api")

_gemini_service: GeminiService | None = None
_executor_service: ExecutorService | None = None
_system_monitor_service: SystemMonitorService | None = None
_memory_service: MemoryService | None = None
_file_service: FileService | None = None
_reminder_service: ReminderService | None = None
_computer_control_service: ComputerControlService | None = None
_email_service: EmailService | None = None
_web_intelligence_service: WebIntelligenceService | None = None
_wake_word_service: WakeWordService | None = None
_agent_service: AgentService | None = None
_tool_router_service: ToolRouterService | None = None


def _get_gemini_service() -> GeminiService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service


def _try_get_gemini_service() -> GeminiService | None:
    """Best-effort Gemini service getter.

    Returns None if Gemini is not configured (e.g. missing API key) or fails to initialize.
    This prevents /api/chat from crashing while keeping local automation features working.
    """
    try:
        return _get_gemini_service()
    except Exception:
        return None


def _is_goal_oriented(message: str) -> bool:
    text = (message or "").strip().lower()
    if not text:
        return False
    phrases = [
        "help me",
        "prepare",
        "setup",
        "set up",
        "organize",
        "start working",
        "get ready",
    ]
    return any(p in text for p in phrases)


def _get_email_service() -> EmailService:
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


def _parse_email_command(message: str) -> dict | None:
    """Parse a simple offline-safe email command.

    Format:
      send email to <recipient> subject <subject> body <body>
    """
    text = message.strip()
    lower = text.lower()
    if not lower.startswith("send email to "):
        return None

    rest = text[len("send email to "):].strip()
    parts = rest.split(" ", 1)
    if not parts:
        return None

    to_addr = parts[0].strip()
    tail = parts[1] if len(parts) > 1 else ""
    tail_lower = tail.lower()

    subject = ""
    body = ""

    if " subject " in tail_lower:
        _, after_subject = tail.split("subject", 1)
        after_subject = after_subject.strip()
        if " body " in after_subject.lower():
            subj, bod = after_subject.split("body", 1)
            subject = subj.strip()
            body = bod.strip()
        else:
            subject = after_subject.strip()
    elif " body " in tail_lower:
        _, bod = tail.split("body", 1)
        body = bod.strip()

    return {"op": "send", "to": to_addr, "subject": subject, "body": body}


def _get_memory_service() -> MemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service


def _get_file_service() -> FileService:
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service


def _get_reminder_service() -> ReminderService:
    global _reminder_service
    if _reminder_service is None:
        _reminder_service = ReminderService()
        _reminder_service.start()
    return _reminder_service


def _try_get_computer_control_service() -> ComputerControlService | None:
    global _computer_control_service
    if _computer_control_service is not None:
        return _computer_control_service
    try:
        _computer_control_service = ComputerControlService()
        return _computer_control_service
    except Exception:
        return None


def _parse_computer_command(message: str) -> dict | None:
    text = message.strip()
    lower = text.lower()

    if lower.startswith("type "):
        payload = text[len("type "):]
        return {"op": "type", "text": payload}

    if lower.startswith("press "):
        key = text[len("press "):].strip()
        return {"op": "press", "key": key}

    if lower.startswith("hotkey "):
        rest = text[len("hotkey "):].strip()
        # supports: "hotkey ctrl+shift+esc" or "hotkey ctrl shift esc"
        if "+" in rest:
            keys = [k.strip() for k in rest.split("+") if k.strip()]
        else:
            keys = [k.strip() for k in rest.split(" ") if k.strip()]
        return {"op": "hotkey", "keys": keys}

    return None


def _parse_reminder_command(message: str) -> dict | None:
    text = message.strip()
    lower = text.lower()

    if lower in {"list reminders", "show reminders", "reminders"}:
        return {"op": "list"}

    if lower.startswith("remind me in "):
        rest = text[len("remind me in "):].strip()
        parts = rest.split(" ", 1)
        if not parts:
            return None
        try:
            minutes = int(parts[0])
        except Exception:
            return None
        tail = parts[1] if len(parts) > 1 else ""
        tail_lower = tail.lower().strip()
        if tail_lower.startswith("minute"):
            tail = tail.split(" ", 1)[1] if " " in tail else ""
        if tail_lower.startswith("minutes"):
            tail = tail.split(" ", 1)[1] if " " in tail else ""
        if tail_lower.startswith("to "):
            tail = tail[3:]
        msg = tail.strip() or "Reminder"
        return {"op": "in_minutes", "minutes": minutes, "message": msg}

    if lower.startswith("remind me at "):
        rest = text[len("remind me at "):].strip()
        if " " in rest:
            hhmm, tail = rest.split(" ", 1)
        else:
            hhmm, tail = rest, ""
        tail_lower = tail.lower().strip()
        if tail_lower.startswith("to "):
            tail = tail[3:]
        msg = tail.strip() or "Reminder"
        return {"op": "at", "time": hhmm.strip(), "message": msg}

    return None


def _parse_memory_command(message: str) -> dict | None:
    text = message.strip()
    lower = text.lower()

    if lower.startswith("remember "):
        rest = text[len("remember "):].strip()
        if " is " in rest:
            key, value = rest.split(" is ", 1)
            return {"op": "remember", "key": key.strip(), "value": value.strip()}
        if " = " in rest:
            key, value = rest.split(" = ", 1)
            return {"op": "remember", "key": key.strip(), "value": value.strip()}
        return None

    if lower.startswith("forget "):
        key = text[len("forget "):].strip()
        return {"op": "forget", "key": key}

    if lower.startswith("what is "):
        key = text[len("what is "):].strip().rstrip("?")
        return {"op": "recall", "key": key}

    if lower.startswith("recall "):
        key = text[len("recall "):].strip().rstrip("?")
        return {"op": "recall", "key": key}

    return None


def _parse_file_command(message: str) -> dict | None:
    text = message.strip()
    lower = text.lower()

    if lower.startswith("create folder "):
        path = text[len("create folder "):].strip()
        return {"op": "create_folder", "path": path}

    if lower.startswith("rename ") and " to " in lower:
        left, right = text.split(" to ", 1)
        src = left[len("rename "):].strip()
        new_name = right.strip()
        return {"op": "rename", "src": src, "new_name": new_name}

    if lower.startswith("move ") and " to " in lower:
        left, right = text.split(" to ", 1)
        src = left[len("move "):].strip()
        dst = right.strip()
        return {"op": "move", "src": src, "dst": dst}

    if lower.startswith("delete "):
        target = text[len("delete "):].strip()
        return {"op": "delete", "path": target}

    if lower.startswith("find files "):
        q = text[len("find files "):].strip()
        return {"op": "find", "query": q}

    return None


def _get_executor_service() -> ExecutorService:
    global _executor_service
    if _executor_service is None:
        _executor_service = ExecutorService()
    return _executor_service


def _try_get_system_monitor_service() -> SystemMonitorService | None:
    global _system_monitor_service
    if _system_monitor_service is not None:
        return _system_monitor_service
    try:
        _system_monitor_service = SystemMonitorService()
        return _system_monitor_service
    except Exception:
        return None


def _get_web_intelligence_service() -> WebIntelligenceService:
    global _web_intelligence_service
    if _web_intelligence_service is None:
        _web_intelligence_service = WebIntelligenceService()
    return _web_intelligence_service


def _try_get_agent_service() -> AgentService | None:
    global _agent_service
    if _agent_service is not None:
        return _agent_service
    gemini = _try_get_gemini_service()
    if gemini is None:
        return None
    try:
        _agent_service = AgentService(gemini=gemini, executor=_get_executor_service())
        return _agent_service
    except Exception:
        return None


def _try_get_tool_router_service() -> ToolRouterService | None:
    global _tool_router_service
    if _tool_router_service is not None:
        return _tool_router_service
    gemini = _try_get_gemini_service()
    if gemini is None:
        return None
    try:
        _tool_router_service = ToolRouterService(gemini=gemini, executor=_get_executor_service())
        return _tool_router_service
    except Exception:
        return None
    global _wake_word_service
    if _wake_word_service is not None:
        return _wake_word_service
    try:
        _wake_word_service = WakeWordService()
        return _wake_word_service
    except Exception:
        return None


def _get_history() -> List[Dict[str, str]]:
    history = session.get("history")
    if not isinstance(history, list):
        history = []
    clean: List[Dict[str, str]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        text = item.get("text")
        if role in {"user", "assistant"} and isinstance(text, str) and text.strip():
            clean.append({"role": role, "text": text.strip()})
    return clean


def _set_history(history: List[Dict[str, str]]) -> None:
    session["history"] = history


def _is_low_signal(message: str) -> bool:
    m = message.strip().lower()
    if not m:
        return True
    greetings = {"hi", "hii", "hiii", "hello", "hey", "yo", "sup", "hola"}
    if m in greetings:
        return True
    if len(m) <= 3 and all(ch.isalpha() for ch in m):
        return True
    return False


def _concise_bootstrap_reply() -> str:
    return (
        "MISSION ANALYSIS:\n"
        "- Greeting received; mission parameters not provided.\n\n"
        "OBJECTIVE BREAKDOWN:\n"
        "- Share your mission goal in 1 sentence (what you want done).\n\n"
        "EXECUTION STRATEGY:\n"
        "- I will break it into steps, tools, and checkpoints.\n\n"
        "RISK ASSESSMENT:\n"
        "- Low risk; awaiting scope.\n\n"
        "FINAL RECOMMENDATION:\n"
        "- Provide objective + constraints (time, budget, platform)."
    )


def _execution_to_history_text(summary: str, steps: list[dict]) -> str:
    lines: list[str] = [summary]
    for idx, step in enumerate(steps, 1):
        intent = step.get("intent", "unknown")
        status = step.get("status", "error")
        if status == "success":
            lines.append(f"Step {idx}: {intent} - success")
        else:
            err = step.get("error") or "error"
            lines.append(f"Step {idx}: {intent} - error - {err}")
    return "\n".join(lines)


def _requires_confirmation(actions: list[dict]) -> bool:
    for a in actions:
        if not isinstance(a, dict):
            continue
        intent = str(a.get("intent") or "").strip().lower()
        if intent == "file_delete":
            return True
        if intent.startswith("computer_"):
            return True
        if intent == "email_send":
            return True
    return False


def _execute_actions(actions: list, message: str) -> dict:
    if not actions or not isinstance(actions, list):
        return {
            "summary": "Execution failed.",
            "steps": [{"intent": "unknown", "status": "error", "error": "No valid actions provided."}],
        }

    executor = _get_executor_service()
    memory = _get_memory_service()
    files = _get_file_service()
    reminders = _get_reminder_service()
    comp = _try_get_computer_control_service()
    email = _get_email_service()
    web_intel = _get_web_intelligence_service()

    steps: list[dict] = []
    ok_count = 0

    for action in actions:
        if not isinstance(action, dict) or "intent" not in action:
            steps.append({"intent": "unknown", "status": "error", "error": "Invalid action format."})
            continue

        intent = str(action.get("intent") or "").strip().lower()

        # Existing executor intents
        if intent in executor.SAFE_INTENTS:
            result = executor.execute(intent, message)
            if result is None:
                steps.append({"intent": intent, "status": "error", "error": "Execution returned no result."})
            elif isinstance(result, str) and result.startswith("SYSTEM ERROR:"):
                steps.append({"intent": intent, "status": "error", "error": result})
            else:
                ok_count += 1
                steps.append({"intent": intent, "status": "success"})
            continue

        # Memory intents
        if intent == "memory_remember":
            key = str(action.get("key") or "").strip()
            value = str(action.get("value") or "").strip()
            if not key or not value:
                steps.append({"intent": intent, "status": "error", "error": "Missing key/value."})
                continue
            try:
                memory.remember(key, value)
                ok_count += 1
                steps.append({"intent": intent, "status": "success"})
            except Exception:
                steps.append({"intent": intent, "status": "error", "error": "Failed to store memory."})
            continue

        if intent == "memory_recall":
            key = str(action.get("key") or "").strip()
            try:
                _ = memory.recall(key)
                ok_count += 1
                steps.append({"intent": intent, "status": "success"})
            except Exception:
                steps.append({"intent": intent, "status": "error", "error": "Failed to recall memory."})
            continue

        if intent == "memory_forget":
            key = str(action.get("key") or "").strip()
            try:
                memory.forget(key)
                ok_count += 1
                steps.append({"intent": intent, "status": "success"})
            except Exception:
                steps.append({"intent": intent, "status": "error", "error": "Failed to clear memory."})
            continue

        # File intents
        if intent == "file_create_folder":
            path = str(action.get("path") or "").strip()
            try:
                res = files.create_folder(path)
                if res.get("ok"):
                    ok_count += 1
                    steps.append({"intent": intent, "status": "success"})
                else:
                    steps.append({"intent": intent, "status": "error", "error": res.get("error") or "Failed."})
            except Exception:
                steps.append({"intent": intent, "status": "error", "error": "Failed."})
            continue

        if intent == "file_rename":
            src = str(action.get("src") or "").strip()
            new_name = str(action.get("new_name") or "").strip()
            try:
                res = files.rename_path(src, new_name)
                if res.get("ok"):
                    ok_count += 1
                    steps.append({"intent": intent, "status": "success"})
                else:
                    steps.append({"intent": intent, "status": "error", "error": res.get("error") or "Failed."})
            except Exception:
                steps.append({"intent": intent, "status": "error", "error": "Failed."})
            continue

        if intent == "file_move":
            src = str(action.get("src") or "").strip()
            dst = str(action.get("dst") or "").strip()
            try:
                res = files.move_path(src, dst)
                if res.get("ok"):
                    ok_count += 1
                    steps.append({"intent": intent, "status": "success"})
                else:
                    steps.append({"intent": intent, "status": "error", "error": res.get("error") or "Failed."})
            except Exception:
                steps.append({"intent": intent, "status": "error", "error": "Failed."})
            continue

        if intent == "file_find":
            query = str(action.get("query") or "").strip()
            try:
                res = files.find_files(query)
                if res.get("ok"):
                    ok_count += 1
                    steps.append({"intent": intent, "status": "success"})
                else:
                    steps.append({"intent": intent, "status": "error", "error": res.get("error") or "Failed."})
            except Exception:
                steps.append({"intent": intent, "status": "error", "error": "Failed."})
            continue

        if intent == "file_delete":
            path = str(action.get("path") or "").strip()
            try:
                res = files.delete_path(path)
                if res.get("ok"):
                    ok_count += 1
                    steps.append({"intent": intent, "status": "success"})
                else:
                    steps.append({"intent": intent, "status": "error", "error": res.get("error") or "Failed."})
            except Exception:
                steps.append({"intent": intent, "status": "error", "error": "Failed."})
            continue

        # Reminder intents
        if intent == "reminder_in_minutes":
            try:
                minutes = int(action.get("minutes") or 0)
                msg = str(action.get("message") or "Reminder")
                reminders.add_in_minutes(minutes, msg)
                ok_count += 1
                steps.append({"intent": intent, "status": "success"})
            except Exception:
                steps.append({"intent": intent, "status": "error", "error": "Failed."})
            continue

        if intent == "reminder_at":
            try:
                hhmm = str(action.get("time") or "").strip()
                msg = str(action.get("message") or "Reminder")
                reminders.add_at_hhmm(hhmm, msg)
                ok_count += 1
                steps.append({"intent": intent, "status": "success"})
            except Exception:
                steps.append({"intent": intent, "status": "error", "error": "Failed."})
            continue

        if intent == "reminder_list":
            try:
                reminders.list_reminders()
                ok_count += 1
                steps.append({"intent": intent, "status": "success"})
            except Exception:
                steps.append({"intent": intent, "status": "error", "error": "Failed."})
            continue

        # Computer control intents
        if intent.startswith("computer_"):
            if comp is None:
                steps.append({"intent": intent, "status": "error", "error": "Computer control unavailable."})
                continue
            if intent == "computer_type":
                res = comp.type_text(str(action.get("text") or ""))
            elif intent == "computer_press":
                res = comp.press_key(str(action.get("key") or ""))
            elif intent == "computer_hotkey":
                keys = action.get("keys")
                keys_list = keys if isinstance(keys, list) else []
                res = comp.hotkey([str(k) for k in keys_list])
            else:
                steps.append({"intent": intent, "status": "error", "error": "Computer intent not supported."})
                continue

            if res.get("ok"):
                ok_count += 1
                steps.append({"intent": intent, "status": "success"})
            else:
                steps.append({"intent": intent, "status": "error", "error": res.get("error") or "Failed."})
            continue

        # Email
        if intent == "email_send":
            to_addr = str(action.get("to") or "").strip()
            subject = str(action.get("subject") or "").strip()
            body = str(action.get("body") or "").strip()
            res = email.send_email(to_addr, subject, body)
            if res.get("ok"):
                ok_count += 1
                steps.append({"intent": intent, "status": "success"})
            else:
                steps.append({"intent": intent, "status": "error", "error": res.get("error") or "Failed."})
            continue

        # Web search / intelligence
        if intent == "search_web":
            try:
                res = web_intel.search(message, summarize=True, max_results=5)
                if res.get("ok") and res.get("results"):
                    ok_count += 1
                    steps.append({"intent": intent, "status": "success"})
                else:
                    steps.append({"intent": intent, "status": "error", "error": res.get("error") or "No results."})
            except Exception:
                steps.append({"intent": intent, "status": "error", "error": "Search failed."})
            continue

        steps.append({"intent": intent or "unknown", "status": "error", "error": "Intent not supported."})

    summary = f"Execution completed. ({ok_count}/{len(steps)} successful)" if steps else "Execution failed."
    return {"summary": summary, "steps": steps}


def _detect_preset_mode(message: str) -> str | None:
    """
    Detect workspace preset activation phrases.
    
    Returns:
        Preset name (coding_mode, research_mode, presentation_mode) or None.
    """
    text = message.strip().lower()
    
    # Coding mode patterns
    if any(phrase in text for phrase in ["activate coding mode", "coding mode", "start coding mode"]):
        return "coding_mode"
    
    # Research mode patterns
    if any(phrase in text for phrase in ["activate research mode", "research mode", "start research mode"]):
        return "research_mode"
    
    # Presentation mode patterns
    if any(phrase in text for phrase in ["activate presentation mode", "presentation mode", "start presentation mode"]):
        return "presentation_mode"
    
    return None


@api_bp.post("/chat")
def chat() -> Any:
    payload = request.get_json(silent=True) or {}
    message = payload.get("message")

    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Missing 'message'"}), 400

    message = message.strip()
    history = _get_history()
    
    # ── UNIVERSAL TOOL ROUTER ─────────────────────────────────────────────
    router = _try_get_tool_router_service()
    if router:
        plan = router.route_request(message, history[-10:])
        
        # Check for confirmation requirements (Safety Feature)
        if plan.get("mode") == "execute":
            actions = plan.get("actions", [])
            if _requires_confirmation(actions):
                session["pending_actions"] = actions
                session["pending_message"] = message
                return jsonify({
                    "type": "pending_execution",
                    "summary": "This action requires mission confirmation.",
                    "steps": actions
                })
        
        # Execute (or Chat)
        result = router.execute_and_format(plan, message)
        
        # Update history
        history.append({"role": "user", "text": message})
        if result.get("type") == "chat":
            history.append({"role": "assistant", "text": result.get("reply")})
        else:
            history.append({"role": "assistant", "text": result.get("summary")})
            
        _set_history(history[-20:]) # Keep longer history 
        return jsonify(result)

    # ── FALLBACK (Old logic) ─────────────────────────────────────────────
    # ... rest of the original chat function ...

        op = file_cmd.get("op")

        if op == "delete":
            # Always require confirmation for deletes
            session["pending_actions"] = [{"intent": "file_delete", "path": file_cmd.get("path") or ""}]
            session["pending_message"] = message
            return jsonify({
                "type": "pending_execution",
                "summary": "Delete operation requires confirmation.",
                "steps": session["pending_actions"],
            })

        try:
            if op == "create_folder":
                result = files.create_folder(str(file_cmd.get("path") or ""))
                reply = f"FILE OK: Folder ready - {result.get('path')}"
            elif op == "rename":
                result = files.rename_path(str(file_cmd.get("src") or ""), str(file_cmd.get("new_name") or ""))
                reply = f"FILE OK: Renamed to {result.get('to')}" if result.get("ok") else f"FILE ERROR: {result.get('error')}"
            elif op == "move":
                result = files.move_path(str(file_cmd.get("src") or ""), str(file_cmd.get("dst") or ""))
                reply = f"FILE OK: Moved to {result.get('to')}" if result.get("ok") else f"FILE ERROR: {result.get('error')}"
            elif op == "find":
                result = files.find_files(str(file_cmd.get("query") or ""))
                if result.get("ok"):
                    results = result.get("results") or []
                    if results:
                        reply = "FILES FOUND:\n" + "\n".join([f"- {r}" for r in results])
                    else:
                        reply = "FILES FOUND: 0 results."
                else:
                    reply = f"FILE ERROR: {result.get('error')}"
            else:
                reply = "FILE ERROR: Unsupported file operation."
        except PermissionError:
            reply = "FILE ERROR: Path is outside allowed workspace root."
        except Exception:
            reply = "FILE ERROR: Operation failed."

        history.append({"role": "user", "text": message})
        history.append({"role": "assistant", "text": reply})
        history = history[-10:]
        _set_history(history)
        return jsonify({"type": "chat", "reply": reply})

    # Step 2.5: Autonomous Goal Mode (requires Gemini)
    # Runs after offline-safe command handlers (memory/email/computer/reminder/file).
    if gemini is not None and _is_goal_oriented(message):
        try:
            goal_plan = gemini.plan_goal(message, context_history)
        except Exception:
            goal_plan = {"mode": "chat", "response": ""}

        if isinstance(goal_plan, dict) and goal_plan.get("mode") == "goal":
            goal = str(goal_plan.get("goal") or message).strip()
            intents = goal_plan.get("actions")
            intents_list = intents if isinstance(intents, list) else []
            actions = [{"intent": str(i).strip().lower()} for i in intents_list if isinstance(i, str) and str(i).strip()]
            actions = [a for a in actions if a.get("intent") in executor.SAFE_INTENTS]

            if actions:
                goal_meta = {"goal": goal, "plan": actions}

                if len(actions) > 1 or _requires_confirmation(actions):
                    session["pending_actions"] = actions
                    session["pending_message"] = message
                    session["pending_goal"] = goal_meta
                    return jsonify({
                        "type": "pending_execution",
                        "summary": f"Goal plan generated: {goal}",
                        "steps": actions,
                        "goal": goal,
                        "plan": actions,
                    })

                result = executor.execute_multiple(actions, message)
                summary = result.get("summary", "Execution completed.")
                steps = result.get("steps", [])
                history.append({"role": "user", "text": message})
                history.append({"role": "assistant", "text": _execution_to_history_text(summary, steps)})
                history = history[-10:]
                _set_history(history)
                return jsonify({
                    "type": "execution",
                    "summary": summary,
                    "steps": steps,
                    "goal": goal,
                    "plan": actions,
                })

    # Step 0: Check for workspace preset activation (no API call)
    preset_name = _detect_preset_mode(message)
    if preset_name:
        preset_actions = executor.get_preset_actions(preset_name)
        if preset_actions and len(preset_actions) > 0:
            # Store pending actions for confirmation (trigger risk confirmation layer)
            session["pending_actions"] = preset_actions
            session["pending_message"] = message
            preset_display_name = preset_name.replace("_", " ").title()
            return jsonify({
                "type": "pending_execution",
                "summary": f"NeuroPilot detected {len(preset_actions)} actions for {preset_display_name}.",
                "steps": preset_actions
            })

    # Step 1: Try fast keyword detection (no API call)
    intents = executor.detect_intents(message)
    if len(intents) >= 2:
        actions = [{"intent": i} for i in intents]
        # Store pending actions for confirmation
        session["pending_actions"] = actions
        session["pending_message"] = message
        return jsonify({
            "type": "pending_execution",
            "summary": f"NeuroPilot detected {len(actions)} planned actions.",
            "steps": actions
        })

    if len(intents) == 1:
        intent = intents[0]
        system_result = executor.execute(intent, message)
        if system_result is not None:
            history.append({"role": "user", "text": message})
            history.append({"role": "assistant", "text": system_result})
            history = history[-10:]
            _set_history(history)
            return jsonify({"type": "chat", "reply": system_result})

    # Step 2: Check for low-signal greetings (no API call)
    if _is_low_signal(message):
        reply = _concise_bootstrap_reply()
        history.append({"role": "user", "text": message})
        history.append({"role": "assistant", "text": reply})
        history = history[-10:]
        _set_history(history)
        return jsonify({"type": "chat", "reply": reply})

    # Step 3: Use AI planning for complex/multi-step requests
    if gemini is None:
        reply = (
            "AI planning is currently unavailable (missing or invalid GEMINI_API_KEY).\n\n"
            "You can still:\n"
            "- Run system commands (e.g., 'open notepad')\n"
            "- Run multiple commands (e.g., 'open chrome and calculator')\n"
            "- Use workspace presets (e.g., 'activate coding mode')\n\n"
            "If you want AI chat/planning, set GEMINI_API_KEY and restart the server."
        )

        history.append({"role": "user", "text": message})
        history.append({"role": "assistant", "text": reply})
        history = history[-10:]
        _set_history(history)
        return jsonify({"type": "chat", "reply": reply})

    try:
        plan = gemini.plan_actions(message, context_history)
    except Exception:
        # API error - return helpful guidance without another API call
        reply = (
            "I'm here to help! You can:\n\n"
            "• Ask me questions (e.g., 'what is Python?')\n"
            "• Control your system (e.g., 'open notepad')\n"
            "• Run multiple commands (e.g., 'open chrome and calculator')\n\n"
            "What would you like to do?"
        )
        history.append({"role": "user", "text": message})
        history.append({"role": "assistant", "text": reply})
        history = history[-10:]
        _set_history(history)
        return jsonify({"type": "chat", "reply": reply})

    if plan.get("mode") == "execute":
        # Check for multi-step execution requiring confirmation
        actions = plan.get("actions", [])
        if len(actions) > 1 or _requires_confirmation(actions):
            # Store pending actions for confirmation
            session["pending_actions"] = actions
            session["pending_message"] = message
            return jsonify({
                "type": "pending_execution",
                "summary": f"NeuroPilot detected {len(actions)} planned actions.",
                "steps": actions
            })
        elif actions:
            # Single action - execute immediately
            system_result = _execute_actions(actions, message)
            summary = system_result.get("summary", "Execution completed.")
            steps = system_result.get("steps", [])
            history.append({"role": "user", "text": message})
            history.append({"role": "assistant", "text": _execution_to_history_text(summary, steps)})
            history = history[-10:]
            _set_history(history)
            return jsonify({"type": "execution", "summary": summary, "steps": steps})

    # Mode is "chat" - use the AI-generated response directly (single API call)
    reply = plan.get("response", "I'm here to help! What would you like to know?")

    history.append({"role": "user", "text": message})
    history.append({"role": "assistant", "text": reply})
    history = history[-10:]
    _set_history(history)

    return jsonify({"type": "chat", "reply": reply})


def _run_agent_until_pause(goal: str, history: List[Dict[str, str]], max_steps: int = 10) -> dict:
    agent = _try_get_agent_service()
    if agent is None:
        return {"type": "chat", "reply": "AGENT MODE ERROR: Gemini is unavailable or not configured."}

    executed_steps = session.get("agent_executed_steps")
    executed: list[dict] = executed_steps if isinstance(executed_steps, list) else []

    last_plans = session.get("agent_last_plans")
    last_plans_list: list[list[str]] = last_plans if isinstance(last_plans, list) else []

    remaining_raw = session.get("agent_remaining_budget")
    try:
        remaining = int(remaining_raw) if remaining_raw is not None else max_steps
    except Exception:
        remaining = max_steps

    state_obj = type("S", (), {"goal": goal, "executed": executed, "remaining_budget": remaining, "last_plans": last_plans_list})()
    state = agent.propose_next_actions(
        state=state_obj,
        history=history,
    )
    session["agent_last_plans"] = state_obj.last_plans

    if not state:
        session.pop("agent_executed_steps", None)
        session.pop("agent_last_plans", None)
        session.pop("agent_remaining_budget", None)
        return {
            "type": "execution",
            "summary": "Agent mode completed: no further safe actions required.",
            "steps": executed,
            "goal": goal,
            "agent": {"active": False, "max_steps": max_steps, "executed_steps": len(executed)},
        }

    actions = state

    if len(actions) > 1 or _requires_confirmation(actions):
        session["pending_actions"] = actions
        session["pending_message"] = goal
        session["pending_agent"] = {"goal": goal, "max_steps": max_steps}
        return {
            "type": "pending_execution",
            "summary": f"AGENT MODE ACTIVE: {goal}",
            "steps": actions,
            "goal": goal,
            "plan": actions,
            "agent": {"active": True, "max_steps": max_steps, "executed_steps": len(executed)},
        }

    result = _get_executor_service().execute_multiple(actions, goal)
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for s in steps:
            if isinstance(s, dict):
                executed.append(s)

    session["agent_executed_steps"] = executed
    session["agent_remaining_budget"] = max(0, max_steps - len(executed))

    if any(isinstance(s, dict) and s.get("status") != "success" for s in steps):
        session.pop("agent_last_plans", None)
        session.pop("agent_remaining_budget", None)
        session.pop("pending_agent", None)
        return {
            "type": "execution",
            "summary": "Agent mode stopped due to an error.",
            "steps": executed,
            "goal": goal,
            "agent": {"active": False, "max_steps": max_steps, "executed_steps": len(executed)},
        }

    if len(executed) >= max_steps:
        session.pop("agent_last_plans", None)
        session.pop("agent_remaining_budget", None)
        session.pop("pending_agent", None)
        return {
            "type": "execution",
            "summary": "Agent mode stopped: max step budget reached.",
            "steps": executed,
            "goal": goal,
            "agent": {"active": False, "max_steps": max_steps, "executed_steps": len(executed)},
        }

    return _run_agent_until_pause(goal=goal, history=history, max_steps=max_steps)


def _requires_confirmation(actions: List[dict]) -> bool:
    """Check if any action requires explicit user confirmation."""
    RISKY_INTENTS = {"delete_file", "send_email", "computer_type", "computer_press", "computer_hotkey"}
    for action in actions:
        if isinstance(action, dict) and action.get("intent") in RISKY_INTENTS:
            return True
    return False


@api_bp.post("/agent_goal")
def agent_goal() -> Any:
    payload = request.get_json(silent=True) or {}
    goal = payload.get("goal") or payload.get("message")
    if not isinstance(goal, str) or not goal.strip():
        return jsonify({"error": "Missing 'goal'"}), 400

    goal = goal.strip()

    session.pop("agent_executed_steps", None)
    session.pop("agent_last_plans", None)
    session.pop("agent_remaining_budget", None)
    session.pop("pending_agent", None)

    history = _get_history()
    result = _run_agent_until_pause(goal=goal, history=history, max_steps=10)
    return jsonify(result)


@api_bp.post("/confirm")
def confirm() -> Any:
    pending_actions = session.get("pending_actions")
    pending_message = session.get("pending_message", "")
    pending_goal = session.get("pending_goal")
    pending_agent = session.get("pending_agent")

    if not pending_actions or not isinstance(pending_actions, list):
        return jsonify({"error": "No pending actions to confirm"}), 400

    if pending_agent and isinstance(pending_agent, dict):
        system_result = _get_executor_service().execute_multiple(pending_actions, pending_message)
    elif pending_goal and isinstance(pending_goal, dict):
        system_result = _get_executor_service().execute_multiple(pending_actions, pending_message)
    else:
        system_result = _execute_actions(pending_actions, pending_message)

    session.pop("pending_actions", None)
    session.pop("pending_message", None)
    session.pop("pending_goal", None)

    summary = system_result.get("summary", "Execution completed.")
    steps = system_result.get("steps", [])

    history = _get_history()
    history.append({"role": "user", "text": pending_message})
    history.append({"role": "assistant", "text": _execution_to_history_text(summary, steps)})
    history = history[-10:]
    _set_history(history)

    if pending_agent and isinstance(pending_agent, dict):
        executed_steps = session.get("agent_executed_steps")
        executed: list[dict] = executed_steps if isinstance(executed_steps, list) else []
        if isinstance(steps, list):
            for s in steps:
                if isinstance(s, dict):
                    executed.append(s)

        session["agent_executed_steps"] = executed
        session["agent_remaining_budget"] = max(0, 10 - len(executed))

        goal = str(pending_agent.get("goal") or pending_message).strip() or pending_message
        next_payload = _run_agent_until_pause(goal=goal, history=history, max_steps=10)
        session.pop("pending_agent", None)
        return jsonify(next_payload)

    payload = {
        "type": "execution",
        "summary": summary,
        "steps": steps,
    }
    if pending_goal and isinstance(pending_goal, dict):
        payload["goal"] = pending_goal.get("goal")
        payload["plan"] = pending_goal.get("plan")
    return jsonify(payload)


@api_bp.post("/cancel")
def cancel() -> Any:
    """Cancel pending multi-step actions."""
    session.pop("pending_actions", None)
    session.pop("pending_message", None)
    session.pop("pending_goal", None)
    session.pop("pending_agent", None)
    session.pop("agent_executed_steps", None)
    session.pop("agent_last_plans", None)
    session.pop("agent_remaining_budget", None)
    
    return jsonify({"type": "cancelled"})


@api_bp.post("/reset")
def reset() -> Any:
    session.pop("history", None)
    return jsonify({"ok": True})


@api_bp.get("/system_status")
def system_status() -> Any:
    monitor = _try_get_system_monitor_service()
    if monitor is None:
        return jsonify({"error": "System monitor unavailable (psutil not installed)."}), 503
    try:
        return jsonify(monitor.get_status())
    except Exception:
        return jsonify({"error": "Failed to read system status."}), 500


@api_bp.get("/notifications")
def notifications() -> Any:
    reminders = _get_reminder_service()
    try:
        limit_raw = request.args.get("limit", "10")
        limit = int(limit_raw)
    except Exception:
        limit = 10
    try:
        items = reminders.pop_notifications(limit=limit)
        return jsonify({"notifications": items})
    except Exception:
        return jsonify({"notifications": []})


@api_bp.post("/web_search")
def web_search() -> Any:
    """Perform web search with optional AI summarization.
    
    Request body:
        - query: Search query string
        - summarize: bool (default True) - whether to use Gemini to summarize results
        - max_results: int (default 5) - maximum number of results to fetch
    
    Returns:
        {
            "ok": True/False,
            "query": "extracted query",
            "results": [{"title": "...", "url": "...", "snippet": "..."}],
            "summary": "AI-generated summary or None",
            "error": "error message if failed"
        }
    """
    payload = request.get_json(silent=True) or {}
    query = payload.get("query") or payload.get("message", "")
    
    if not isinstance(query, str) or not query.strip():
        return jsonify({"ok": False, "error": "Missing 'query'", "results": [], "summary": None}), 400
    
    summarize = payload.get("summarize", True)
    max_results = payload.get("max_results", 5)
    
    try:
        max_results = int(max_results)
        if max_results < 1 or max_results > 10:
            max_results = 5
    except Exception:
        max_results = 5
    
    web_intel = _get_web_intelligence_service()
    result = web_intel.search(query, summarize=bool(summarize), max_results=max_results)
    
    return jsonify(result)


# Wake word endpoints
@api_bp.get("/wake_word/status")
def wake_word_status() -> Any:
    """Get wake word detection status and availability."""
    wake = _try_get_wake_word_service()
    if wake is None:
        return jsonify({
            "available": False,
            "listening": False,
            "backend": None,
            "wake_phrases": [],
            "error": "Wake word service unavailable. Install SpeechRecognition or Vosk."
        })
    return jsonify(wake.get_status())


@api_bp.post("/wake_word/start")
def wake_word_start() -> Any:
    """Start listening for wake word.
    
    Request body (optional):
        - wake_phrases: List of phrases to detect (default: ["hey neuro", "neuropilot", ...])
        - backend: "auto", "speech_recognition", or "vosk"
    """
    payload = request.get_json(silent=True) or {}
    
    wake = _try_get_wake_word_service()
    if wake is None:
        return jsonify({"ok": False, "error": "Wake word service unavailable. Install SpeechRecognition or Vosk."}), 503
    
    # Update phrases if provided
    phrases = payload.get("wake_phrases")
    if isinstance(phrases, list) and phrases:
        wake.update_wake_phrases(phrases)
    
    # Update backend if provided (requires reinit)
    backend = payload.get("backend")
    if backend in ["speech_recognition", "vosk", "auto"]:
        wake._backend = backend
        wake._detect_backend()
    
    # Set up callback to store detection in session for polling
    def on_wake(phrase: str) -> None:
        # Store in a global detection buffer that can be polled
        if "wake_word_detections" not in session:
            session["wake_word_detections"] = []
        session["wake_word_detections"].append({
            "phrase": phrase,
            "timestamp": time.time()
        })
        # Keep only last 10
        session["wake_word_detections"] = session["wake_word_detections"][-10:]
    
    import time
    wake.on_wake_word = on_wake
    
    result = wake.start_listening()
    return jsonify(result)


@api_bp.post("/wake_word/stop")
def wake_word_stop() -> Any:
    """Stop listening for wake word."""
    wake = _try_get_wake_word_service()
    if wake is None:
        return jsonify({"ok": False, "error": "Wake word service unavailable."}), 503
    
    result = wake.stop_listening()
    return jsonify(result)


@api_bp.get("/wake_word/detections")
def wake_word_detections() -> Any:
    """Get recent wake word detections (polling endpoint)."""
    detections = session.get("wake_word_detections", [])
    # Clear after reading
    session["wake_word_detections"] = []
    return jsonify({"detections": detections})


@api_bp.post("/wake_word/phrases")
def wake_word_phrases() -> Any:
    """Update wake word phrases.
    
    Request body:
        - phrases: List of phrases to detect
    """
    payload = request.get_json(silent=True) or {}
    phrases = payload.get("phrases")
    
    wake = _try_get_wake_word_service()
    if wake is None:
        return jsonify({"ok": False, "error": "Wake word service unavailable."}), 503
    
    if not isinstance(phrases, list) or not phrases:
        return jsonify({"ok": False, "error": "Missing 'phrases' list."}), 400
    
    wake.update_wake_phrases(phrases)
    return jsonify({"ok": True, "wake_phrases": phrases})
