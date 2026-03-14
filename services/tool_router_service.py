from typing import List, Dict, Any, Optional
import json
from services.executor_service import ExecutorService
from services.gemini_service import GeminiService

class ToolRouterService:
    """
    Translates natural language requests into structured tool actions.
    """
    
    def __init__(self, gemini: GeminiService, executor: ExecutorService):
        self._gemini = gemini
        self._executor = executor

    def route_request(self, user_message: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Plans and returns structured actions for a user request.
        Prioritizes local intent detection.
        """
        if history is None:
            history = []
            
        # Step 1: Fast Local Intent Detection (Offline Fallback)
        local_intents = self._executor.detect_intents(user_message)
        if local_intents:
            actions = [{"intent": i} for i in local_intents]
            return {"mode": "execute", "actions": actions}
            
        # Step 2: Use Gemini to plan complex actions
        try:
            plan = self._gemini.plan_actions(user_message, history)
            if not isinstance(plan, dict):
                raise ValueError("Invalid plan format from Gemini.")
            return plan
        except Exception:
            # Step 3: Friendly Fallback for AI failures
            return {
                "mode": "chat", 
                "response": "I couldn't create an AI plan right now, but you can try direct commands like 'open chrome and downloads' or 'start vs code'."
            }

    def execute_and_format(self, plan: Dict[str, Any], original_message: str) -> Dict[str, Any]:
        """
        Executes the plan and returns a formatted result for the UI.
        """
        mode = plan.get("mode", "chat")
        
        if mode == "chat":
            return {
                "type": "chat",
                "reply": plan.get("response", "No response generated.")
            }
            
        if mode == "execute":
            actions = plan.get("actions", [])
            # execute_multiple handles the actual calls to ExecutorService
            result = self._executor.execute_multiple(actions, original_message)
            
            return {
                "type": "execution",
                "summary": result.get("summary", "Execution completed."),
                "steps": result.get("steps", [])
            }
            
        return {"type": "chat", "reply": "Unknown routing mode."}
