from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from services.executor_service import ExecutorService
from services.gemini_service import GeminiService


@dataclass
class AgentRunState:
    goal: str
    executed: List[dict]
    remaining_budget: int
    last_plans: List[List[str]]


class AgentService:
    def __init__(self, gemini: GeminiService, executor: ExecutorService) -> None:
        self._gemini = gemini
        self._executor = executor

    def _filter_actions(self, intents: List[str]) -> List[dict]:
        actions: List[dict] = []
        for i in intents:
            if not isinstance(i, str):
                continue
            intent = i.strip().lower()
            if not intent:
                continue
            if intent not in self._executor.SAFE_INTENTS:
                continue
            actions.append({"intent": intent})
        return actions

    def propose_next_actions(self, state: AgentRunState, history: List[Dict[str, str]]) -> List[dict]:
        if state.remaining_budget <= 0:
            return []

        progress_lines: List[str] = []
        for s in state.executed[-10:]:
            if not isinstance(s, dict):
                continue
            intent = s.get("intent")
            status = s.get("status")
            progress_lines.append(f"- {intent}: {status}")

        progress = "\n".join(progress_lines) if progress_lines else "- (none)"
        agent_message = (
            f"AUTONOMOUS AGENT MODE\n"
            f"GOAL: {state.goal}\n\n"
            f"PROGRESS SO FAR:\n{progress}\n\n"
            f"Generate the NEXT small set of SAFE local actions to move toward completion. "
            f"If the goal is complete or no safe actions remain, return an empty actions list."
        )

        plan = self._gemini.plan_goal(agent_message, history)
        if not isinstance(plan, dict) or plan.get("mode") != "goal":
            return []

        intents = plan.get("actions")
        intents_list = intents if isinstance(intents, list) else []
        proposed = [str(x).strip().lower() for x in intents_list if isinstance(x, str) and str(x).strip()]

        if state.last_plans and proposed == state.last_plans[-1]:
            return []

        state.last_plans.append(proposed)
        state.last_plans = state.last_plans[-3:]

        actions = self._filter_actions(proposed)
        return actions[: max(0, min(len(actions), state.remaining_budget))]

    def run(self, goal: str, history: List[Dict[str, str]], max_steps: int = 10) -> Dict[str, Any]:
        """
        Execute a high-level goal autonomously by planning and executing multiple steps.
        """
        state = AgentRunState(goal=goal.strip(), executed=[], remaining_budget=max_steps, last_plans=[])

        # Step 1: Generate initial plan
        plan_result = self._gemini.plan_goal(goal, history)
        if plan_result.get("mode") != "goal":
            return {
                "summary": "Failed to generate an autonomous plan.",
                "steps": [],
                "goal": goal
            }
        
        goal_text = plan_result.get("goal", goal)
        actions = plan_result.get("actions", [])
        
        # Convert simple intent strings to action dicts
        action_dicts = [{"intent": i} for i in actions]
        
        # Step 2: Execute actions
        result = self._executor.execute_multiple(action_dicts, goal_text)
        
        return {
            "summary": result.get("summary", "Agent execution completed."),
            "steps": result.get("steps", []),
            "goal": goal_text,
            "status": "completed"
        }
