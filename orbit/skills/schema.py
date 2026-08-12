"""Skill schema: a reusable, named workflow made of steps.

Supports variables (substituted into step params with {var} placeholders),
conditions (simple truthy/negated variable checks), loops (repeat a step
over a list variable), approval gating, verification, and retries — the
set of primitives named in the ORBIT spec, kept intentionally simple
rather than a full scripting language.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SkillStep:
    tool: str
    action: str
    params: dict = field(default_factory=dict)
    description: str = ""
    condition: Optional[str] = None  # e.g. "attachment" (truthy) or "not:attachment" (falsy)
    loop_over: Optional[str] = None  # variable name holding a list to iterate
    loop_as: Optional[str] = None  # loop variable name exposed to params during iteration
    requires_approval: bool = False
    verification: dict = field(default_factory=dict)
    retry: int = 0

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "action": self.action,
            "params": self.params,
            "description": self.description,
            "condition": self.condition,
            "loop_over": self.loop_over,
            "loop_as": self.loop_as,
            "requires_approval": self.requires_approval,
            "verification": self.verification,
            "retry": self.retry,
        }

    @staticmethod
    def from_dict(data: dict) -> "SkillStep":
        return SkillStep(**data)


@dataclass
class Skill:
    name: str
    description: str = ""
    variables: list[str] = field(default_factory=list)
    steps: list[SkillStep] = field(default_factory=list)
    source: str = "manual"  # "manual" | "taught"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "variables": self.variables,
            "steps": [s.to_dict() for s in self.steps],
            "source": self.source,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Skill":
        return Skill(
            name=data["name"],
            description=data.get("description", ""),
            variables=data.get("variables", []),
            steps=[SkillStep.from_dict(s) for s in data.get("steps", [])],
            source=data.get("source", "manual"),
            created_at=data.get("created_at", time.time()),
        )
