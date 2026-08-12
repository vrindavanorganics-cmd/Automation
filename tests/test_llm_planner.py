"""LLMPlanner, exercised against a fake `anthropic` module (the real one
needs network + a real API key, unavailable here).
"""
from __future__ import annotations

import json
import sys
import types

import pytest

from orbit.agent.intent import parse_intent
from orbit.agent.llm_planner import LLMPlanError, LLMPlanner
from orbit.config import Settings


class FakeTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class FakeMessage:
    def __init__(self, text):
        self.content = [FakeTextBlock(text)]


class FakeMessages:
    def __init__(self, response_text=None, error=None):
        self._response_text = response_text
        self._error = error
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self._error:
            raise self._error
        return FakeMessage(self._response_text)


class FakeAnthropicClient:
    def __init__(self, messages: FakeMessages, api_key=None):
        self.messages = messages


def _install_fake_anthropic(monkeypatch, messages: FakeMessages):
    module = types.ModuleType("anthropic")
    module.Anthropic = lambda api_key=None: FakeAnthropicClient(messages, api_key=api_key)
    monkeypatch.setitem(sys.modules, "anthropic", module)


def _settings(api_key="test-key"):
    return Settings(anthropic_api_key=api_key)


def test_unavailable_without_api_key():
    planner = LLMPlanner(Settings(anthropic_api_key=None))
    assert planner.available() is False
    with pytest.raises(LLMPlanError):
        planner.plan(parse_intent("do something vague"))


def test_successful_plan_parsed_into_steps(monkeypatch):
    response = json.dumps(
        {
            "summary": "Open Chrome and search",
            "steps": [
                {"tool": "windows_apps", "action": "open_app", "params": {"app": "Google Chrome"}},
                {
                    "tool": "browser",
                    "action": "search",
                    "params": {"query": "buyer leads"},
                    "requires_approval": False,
                },
            ],
        }
    )
    messages = FakeMessages(response_text=response)
    _install_fake_anthropic(monkeypatch, messages)

    planner = LLMPlanner(_settings())
    intent = parse_intent("open chrome and search for buyer leads")
    plan = planner.plan(intent)

    assert plan.summary == "Open Chrome and search"
    assert len(plan.steps) == 2
    assert plan.steps[0].tool == "windows_apps"
    assert plan.steps[0].action == "open_app"
    assert plan.steps[1].params == {"query": "buyer leads"}
    assert messages.last_kwargs["messages"][0]["content"] == intent.interpreted_text


def test_rejects_invented_tool_action(monkeypatch):
    response = json.dumps({"summary": "x", "steps": [{"tool": "system", "action": "delete_everything"}]})
    _install_fake_anthropic(monkeypatch, FakeMessages(response_text=response))

    planner = LLMPlanner(_settings())
    with pytest.raises(LLMPlanError):
        planner.plan(parse_intent("do something"))


def test_malformed_json_raises_plan_error(monkeypatch):
    _install_fake_anthropic(monkeypatch, FakeMessages(response_text="not json at all"))

    planner = LLMPlanner(_settings())
    with pytest.raises(LLMPlanError):
        planner.plan(parse_intent("do something"))


def test_empty_steps_raises_plan_error(monkeypatch):
    response = json.dumps({"summary": "clarify", "steps": []})
    _install_fake_anthropic(monkeypatch, FakeMessages(response_text=response))

    planner = LLMPlanner(_settings())
    with pytest.raises(LLMPlanError):
        planner.plan(parse_intent("do something"))


def test_network_error_raises_plan_error(monkeypatch):
    _install_fake_anthropic(monkeypatch, FakeMessages(error=RuntimeError("connection refused")))

    planner = LLMPlanner(_settings())
    with pytest.raises(LLMPlanError):
        planner.plan(parse_intent("do something"))


def test_missing_anthropic_package_raises_plan_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic", None)  # simulate ImportError

    planner = LLMPlanner(_settings())
    with pytest.raises(LLMPlanError):
        planner.plan(parse_intent("do something"))
