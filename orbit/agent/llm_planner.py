"""LLM-backed planner for requests the rule-based planner can't handle.

TaskPlanner's rule-based `_plan_*` methods cover the concrete actions ORBIT
ships with (open an app, draft an email, ...). Anything genuinely ambiguous
or multi-step -- "email the last three PDFs I opened to Rahul with a short
note" -- falls through to action="unknown", which used to always become a
bare "please clarify" question. LLMPlanner instead asks a cloud LLM (Claude
by default) to produce a structured Plan directly from the free-form
request, restricted to the exact tools/actions ORBIT actually has.

Fully optional: ORBIT stays local-first. This only runs when
ANTHROPIC_API_KEY is configured (see .env.example), and any failure --
network, malformed response, a tool/action the LLM invented -- raises
LLMPlanError so the caller falls back to the existing clarification
question instead of ever executing a hallucinated tool call.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from orbit.agent.intent import Intent
from orbit.agent.planner import Plan, PlanStep
from orbit.config import Settings

# The exact tool/action surface the LLM is allowed to target, kept in sync
# by hand with the *_tool.py `do_*` methods. Deliberately explicit rather
# than reflected automatically off the tool registry, so a stray or
# renamed method can never silently become something the LLM can call.
AVAILABLE_TOOLS: dict[str, list[str]] = {
    "windows_apps": ["open_app", "close_app"],
    "files": ["create_folder", "create_file", "organize", "find_file"],
    "pdf": ["find_and_read", "find_and_summarize"],
    "excel": ["create"],
    "browser": ["open", "goto", "search", "click", "type", "extract_text", "new_tab", "switch_profile"],
    "email": ["draft", "send_email", "cancel_send", "read"],
    "skills": ["run_skill"],
}

SYSTEM_PROMPT = """You are the planner for ORBIT, a Windows desktop voice assistant.
Given a user's request, output ONLY a JSON object (no prose, no markdown fences) shaped like:
{{"summary": "short description", "steps": [{{"tool": "...", "action": "...", "params": {{}}, "description": "...", "requires_approval": false}}]}}

Rules:
- Only use these exact tool/action pairs -- never invent one:
{tools}
- requires_approval must be true for any step that sends an email, deletes something, or is otherwise irreversible.
- Keep steps minimal and concrete.
- If the request is too vague to plan safely, output {{"summary": "clarify", "steps": []}} instead of guessing.
"""


class LLMPlanError(Exception):
    """The LLM couldn't produce a usable plan -- caller should fall back
    to asking the user to clarify, never guess or execute a bad plan."""


@dataclass
class LLMPlanner:
    settings: Settings

    def available(self) -> bool:
        return bool(self.settings.anthropic_api_key)

    def plan(self, intent: Intent) -> Plan:
        if not self.available():
            raise LLMPlanError("No ANTHROPIC_API_KEY configured -- LLM planning is disabled.")

        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise LLMPlanError(
                "The 'anthropic' package is required for LLM-backed planning. "
                "Run: pip install -r requirements/base.txt"
            ) from exc

        client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        tool_list = "\n".join(f"- {tool}: {', '.join(actions)}" for tool, actions in AVAILABLE_TOOLS.items())
        try:
            response = client.messages.create(
                model=self.settings.llm_model,
                max_tokens=1024,
                system=SYSTEM_PROMPT.format(tools=tool_list),
                messages=[{"role": "user", "content": intent.interpreted_text}],
            )
            raw = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        except LLMPlanError:
            raise
        except Exception as exc:  # network error, auth error, SDK error, ...
            raise LLMPlanError(f"LLM request failed: {exc}") from exc

        return self._parse_plan(raw, intent)

    def _parse_plan(self, raw: str, intent: Intent) -> Plan:
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError as exc:
            raise LLMPlanError(f"LLM did not return valid JSON: {exc}") from exc

        steps_data = data.get("steps") or []
        if not steps_data:
            raise LLMPlanError("LLM could not produce a plan for this request.")

        steps: list[PlanStep] = []
        for i, raw_step in enumerate(steps_data, start=1):
            tool = raw_step.get("tool")
            action = raw_step.get("action")
            if tool not in AVAILABLE_TOOLS or action not in AVAILABLE_TOOLS.get(tool, []):
                raise LLMPlanError(f"LLM proposed an unknown tool/action: {tool}.{action}")
            steps.append(
                PlanStep(
                    id=str(i),
                    tool=tool,
                    action=action,
                    params=raw_step.get("params") or {},
                    description=raw_step.get("description", ""),
                    requires_approval=bool(raw_step.get("requires_approval", False)),
                )
            )

        return Plan(summary=data.get("summary", intent.interpreted_text), steps=steps, source_intent=intent)
