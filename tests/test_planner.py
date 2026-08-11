from orbit.agent.intent import parse_intent
from orbit.agent.planner import TaskPlanner


def test_plan_open_app_single_step():
    planner = TaskPlanner()
    intent = parse_intent("open chrome")
    plan = planner.plan(intent)
    assert len(plan.steps) == 1
    assert plan.steps[0].tool == "windows_apps"
    assert plan.steps[0].action == "open_app"


def test_plan_send_requires_approval():
    planner = TaskPlanner()
    intent = parse_intent("send it")
    plan = planner.plan(intent)
    assert plan.steps[0].requires_approval is True


def test_plan_draft_email_no_approval():
    planner = TaskPlanner()
    intent = parse_intent("draft an email")
    plan = planner.plan(intent)
    assert plan.steps[0].requires_approval is False


def test_plan_unknown_asks_clarification():
    planner = TaskPlanner()
    intent = parse_intent("blah blah nonsense")
    plan = planner.plan(intent)
    assert plan.steps[0].tool == "system"
    assert plan.steps[0].action == "ask_clarification"


def test_plan_bulk_outreach_has_eight_steps_with_approval_gates():
    planner = TaskPlanner()
    plan = planner.plan_bulk_outreach(["Acme Foods", "Globex Traders"], template="Hello {company}")
    assert len(plan.steps) == 8
    approval_steps = [s for s in plan.steps if s.requires_approval]
    assert len(approval_steps) >= 2  # ask_approval + send_bulk
    assert plan.steps[-1].action == "verify_sent"
