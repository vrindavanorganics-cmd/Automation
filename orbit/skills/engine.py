"""SkillEngine: Teach Mode recording + reusable skill execution.

Teach Mode: the user performs a workflow once (each action they take through
ORBIT is recorded as a step); ORBIT converts it into a named, reusable
Skill. Later, "Orbit, run <skill>" resolves the closest matching skill by
name and replays its steps, substituting variables, honoring loops,
conditions, approval gates, verification, and retries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rapidfuzz import fuzz, process

from orbit.memory.store import MemoryStore
from orbit.permissions.engine import PermissionDenied, PermissionEngine
from orbit.skills.schema import Skill, SkillStep
from orbit.tools.registry import ToolRegistry
from orbit.verification import verifier as verification_mod


@dataclass
class StepRunResult:
    step: SkillStep
    success: bool
    message: str
    data: dict = field(default_factory=dict)
    verified: Optional[bool] = None
    skipped: bool = False


@dataclass
class SkillRunResult:
    skill_name: str
    success: bool
    step_results: list[StepRunResult] = field(default_factory=list)


def _substitute(value, context: dict):
    if isinstance(value, str):
        try:
            return value.format(**context)
        except (KeyError, IndexError):
            return value
    if isinstance(value, dict):
        return {k: _substitute(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, context) for v in value]
    return value


def _condition_met(condition: Optional[str], context: dict) -> bool:
    if not condition:
        return True
    negate = condition.startswith("not:")
    key = condition[4:] if negate else condition
    truthy = bool(context.get(key))
    return (not truthy) if negate else truthy


class TeachSession:
    """Accumulates steps while the user demonstrates a workflow."""

    def __init__(self, name: str):
        self.name = name
        self.steps: list[SkillStep] = []

    def record(self, tool: str, action: str, params: dict, description: str = "") -> None:
        self.steps.append(SkillStep(tool=tool, action=action, params=params, description=description))

    def finish(self, description: str = "", variables: Optional[list[str]] = None) -> Skill:
        return Skill(
            name=self.name,
            description=description,
            variables=variables or [],
            steps=self.steps,
            source="taught",
        )


class SkillEngine:
    def __init__(self, memory: MemoryStore, tool_registry: ToolRegistry, permission_engine: PermissionEngine):
        self.memory = memory
        self.tool_registry = tool_registry
        self.permission_engine = permission_engine
        self._active_session: Optional[TeachSession] = None

    # ---- Teach Mode ----

    def start_teaching(self, name: str) -> None:
        self._active_session = TeachSession(name)

    @property
    def is_teaching(self) -> bool:
        return self._active_session is not None

    def record_step(self, tool: str, action: str, params: dict, description: str = "") -> None:
        if self._active_session:
            self._active_session.record(tool, action, params, description)

    def finish_teaching(self, description: str = "", variables: Optional[list[str]] = None) -> Skill:
        if not self._active_session:
            raise RuntimeError("No active teaching session")
        skill = self._active_session.finish(description=description, variables=variables)
        self.save_skill(skill)
        self._active_session = None
        return skill

    def cancel_teaching(self) -> None:
        self._active_session = None

    # ---- storage ----

    def save_skill(self, skill: Skill) -> None:
        self.memory.upsert_workflow(skill.name, skill.to_dict())

    def get_skill(self, name: str) -> Optional[Skill]:
        data = self.memory.get_workflow(name)
        return Skill.from_dict(data) if data else None

    def list_skills(self) -> list[Skill]:
        return [Skill.from_dict(d) for d in self.memory.list_workflows()]

    def delete_skill(self, name: str) -> None:
        self.memory.delete_workflow(name)

    def find_skill_by_query(self, query: str, threshold: int = 60) -> Optional[Skill]:
        skills = self.list_skills()
        if not skills:
            return None
        names = [s.name for s in skills]
        match = process.extractOne(query, names, scorer=fuzz.partial_ratio)
        if match and match[1] >= threshold:
            return self.get_skill(match[0])
        return None

    # ---- execution ----

    def run_skill(self, skill: Skill, variables: Optional[dict] = None) -> SkillRunResult:
        context = dict(variables or {})
        results: list[StepRunResult] = []
        overall_success = True

        for step in skill.steps:
            if step.loop_over and step.loop_as:
                items = context.get(step.loop_over, [])
                for item in items:
                    loop_context = {**context, step.loop_as: item}
                    result = self._run_step(step, loop_context)
                    results.append(result)
                    if not result.success:
                        overall_success = False
            else:
                result = self._run_step(step, context)
                results.append(result)
                if not result.success:
                    overall_success = False

            if not overall_success:
                break

        return SkillRunResult(skill_name=skill.name, success=overall_success, step_results=results)

    def _run_step(self, step: SkillStep, context: dict) -> StepRunResult:
        if not _condition_met(step.condition, context):
            return StepRunResult(step=step, success=True, message="Condition not met, skipped", skipped=True)

        params = _substitute(step.params, context)

        if step.requires_approval:
            try:
                self.permission_engine.require(
                    step.action, step.description or f"{step.tool}.{step.action}", params, force_sensitive=True
                )
            except PermissionDenied as exc:
                return StepRunResult(step=step, success=False, message=str(exc))

        attempts = step.retry + 1
        last_result = None
        for _ in range(attempts):
            last_result = self.tool_registry.run(step.tool, step.action, params)
            if last_result.success:
                break

        assert last_result is not None
        verified: Optional[bool] = None
        if step.verification and last_result.success:
            v_type = step.verification.get("type")
            verifier_map = {
                "file_exists": verification_mod.FileExistsVerifier(),
                "text_present": verification_mod.TextPresentVerifier(),
                "window_open": verification_mod.WindowOpenVerifier(),
            }
            v = verifier_map.get(v_type)
            if v:
                vctx = {**step.verification, **last_result.data}
                vresult = verification_mod.verify(v, vctx)
                verified = vresult.verified

        return StepRunResult(
            step=step,
            success=last_result.success,
            message=last_result.message,
            data=last_result.data,
            verified=verified,
        )
