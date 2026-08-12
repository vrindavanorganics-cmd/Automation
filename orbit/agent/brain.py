"""OrbitBrain: the orchestrator that runs the full ORBIT loop.

VOICE -> ASR -> INTENT + CONTEXT -> TASK PLANNER -> TOOLS -> COMPUTER
-> VERIFICATION -> RESPONSE

`process_text_command` lets the whole pipeline (everything after ASR) run
and be tested without a microphone or audio file — this is what the test
suite and this browser workspace use. `process_voice_command` is the real
entry point once ORBIT is running locally with a microphone.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from orbit.agent.intent import Intent, parse_intent
from orbit.agent.planner import Plan, PlanStep, TaskPlanner
from orbit.asr.base import ASREngine, AudioInput
from orbit.asr.vocabulary import VocabularyStore
from orbit.memory.store import MemoryStore
from orbit.permissions.engine import PermissionEngine
from orbit.tools.base import ToolResult
from orbit.tools.registry import ToolRegistry
from orbit.verification import verifier as verification_mod


@dataclass
class StepOutcome:
    step: PlanStep
    result: ToolResult
    verified: Optional[bool] = None


@dataclass
class AgentResponse:
    raw_text: str
    interpreted_text: str
    intent: Intent
    plan: Optional[Plan]
    outcomes: list[StepOutcome] = field(default_factory=list)
    text: str = ""
    stopped: bool = False


_VERIFIER_MAP = {
    "file_exists": verification_mod.FileExistsVerifier,
    "text_present": verification_mod.TextPresentVerifier,
    "window_open": verification_mod.WindowOpenVerifier,
}


class OrbitBrain:
    def __init__(
        self,
        asr_engine: ASREngine,
        vocabulary: VocabularyStore,
        tool_registry: ToolRegistry,
        permission_engine: PermissionEngine,
        memory: MemoryStore,
        planner: Optional[TaskPlanner] = None,
    ):
        self.asr_engine = asr_engine
        self.vocabulary = vocabulary
        self.tool_registry = tool_registry
        self.permission_engine = permission_engine
        self.memory = memory
        self.planner = planner or TaskPlanner()
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    def reset_stop(self) -> None:
        self._stop_requested = False

    def process_voice_command(self, audio: AudioInput) -> AgentResponse:
        transcription = self.asr_engine.transcribe(audio)
        return self._process(transcription.raw_text)

    def process_text_command(self, raw_text: str) -> AgentResponse:
        return self._process(raw_text)

    def _process(self, raw_text: str) -> AgentResponse:
        self.reset_stop()
        correction = self.vocabulary.correct_transcript(raw_text)
        intent = parse_intent(raw_text, correction.interpreted_text)

        if intent.action == "stop":
            self._stop_requested = True
            self.memory.log_activity(raw_text, ["Stop requested"], "Stopped", "success")
            return AgentResponse(
                raw_text=raw_text,
                interpreted_text=correction.interpreted_text,
                intent=intent,
                plan=None,
                text="Stopped.",
                stopped=True,
            )

        plan = self.planner.plan(intent)
        outcomes: list[StepOutcome] = []
        actions_log: list[str] = []
        overall_success = True

        for step in plan.steps:
            if self._stop_requested:
                overall_success = False
                break

            if step.requires_approval:
                approved = self.permission_engine.authorize(
                    step.action, step.description, step.params, force_sensitive=True
                )
                if not approved:
                    outcomes.append(
                        StepOutcome(
                            step=step,
                            result=ToolResult.fail(f"'{step.description}' was not confirmed"),
                        )
                    )
                    overall_success = False
                    break

            result = self.tool_registry.run(step.tool, step.action, step.params)
            actions_log.append(step.description or f"{step.tool}.{step.action}")

            verified: Optional[bool] = None
            if step.verification and result.success:
                verifier_cls = _VERIFIER_MAP.get(step.verification.get("type"))
                if verifier_cls:
                    vctx = {**step.verification, **result.data}
                    vresult = verification_mod.verify(verifier_cls(), vctx)
                    verified = vresult.verified

            outcomes.append(StepOutcome(step=step, result=result, verified=verified))

            if not result.success:
                overall_success = False
                break

        status = "success" if overall_success else "failed"
        last_message = outcomes[-1].result.message if outcomes else "No steps executed"
        self.memory.log_activity(raw_text, actions_log, last_message, status)

        response_text = self._compose_response(plan, outcomes, overall_success)
        return AgentResponse(
            raw_text=raw_text,
            interpreted_text=correction.interpreted_text,
            intent=intent,
            plan=plan,
            outcomes=outcomes,
            text=response_text,
        )

    def _compose_response(self, plan: Plan, outcomes: list[StepOutcome], success: bool) -> str:
        if not outcomes:
            return "I didn't take any action."
        if success:
            result = outcomes[-1].result
            # The message alone is just a status line ("Summarized 'x.pdf'")
            # -- the actual content the user asked for (a PDF summary, etc.)
            # lives in the result data and was previously computed but never
            # shown.
            summary = result.data.get("summary")
            if summary:
                return f"{result.message}\n\n{summary}"
            return result.message
        failed = next((o for o in outcomes if not o.result.success), outcomes[-1])
        return f"Something went wrong: {failed.result.message}"
