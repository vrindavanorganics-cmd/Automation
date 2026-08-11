"""Tool: resolve a spoken skill reference and run it."""
from __future__ import annotations

from orbit.skills.engine import SkillEngine
from orbit.tools.base import Tool, ToolResult


class SkillsTool(Tool):
    name = "skills"

    def __init__(self, engine: SkillEngine):
        self.engine = engine

    def do_run_skill(self, query: str, variables: dict | None = None) -> ToolResult:
        skill = self.engine.find_skill_by_query(query)
        if not skill:
            return ToolResult.fail(f"No matching skill found for '{query}'")
        run_result = self.engine.run_skill(skill, variables or {})
        return ToolResult(
            success=run_result.success,
            message=f"Ran skill '{skill.name}' ({'success' if run_result.success else 'failed'})",
            data={
                "skill": skill.name,
                "steps": [
                    {"description": r.step.description, "success": r.success, "message": r.message}
                    for r in run_result.step_results
                ],
            },
        )
