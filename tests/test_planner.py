from orbit.agent.intent import parse_intent
from orbit.agent.llm_planner import LLMPlanError
from orbit.agent.planner import Plan, PlanStep, TaskPlanner


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
    intent = parse_intent("draft email as hello testing to buyer@example.com")
    plan = planner.plan(intent)
    assert plan.steps[0].tool == "email"
    assert plan.steps[0].action == "draft"
    assert plan.steps[0].params == {"to": "buyer@example.com", "subject": "hello testing", "body": "hello testing"}
    assert plan.steps[0].requires_approval is False


def test_plan_draft_email_without_recipient_asks_instead_of_crashing():
    # Regression: EmailTool.do_draft requires to/subject/body -- calling it
    # with no params raised a raw Python TypeError shown to the user
    # instead of a clear, actionable question.
    planner = TaskPlanner()
    intent = parse_intent("draft an email")
    plan = planner.plan(intent)
    assert plan.steps[0].tool == "system"
    assert plan.steps[0].action == "ask"
    assert "email address" in plan.steps[0].params["message"]


def test_plan_switch_chrome_profile():
    planner = TaskPlanner()
    intent = parse_intent("switch to Rahul Soni profile")
    plan = planner.plan(intent)
    assert plan.steps[0].tool == "browser"
    assert plan.steps[0].action == "switch_profile"
    assert plan.steps[0].params == {"name": "Rahul Soni"}


def test_plan_switch_chrome_profile_without_name_asks_instead_of_crashing():
    planner = TaskPlanner()
    intent = parse_intent("switch chrome profile")  # no name given -> "chrome" isn't a real profile name
    plan = planner.plan(intent)
    assert plan.steps[0].tool == "system"
    assert plan.steps[0].action == "ask"


class _FakeLLMPlanner:
    def __init__(self, plan=None, error=None, is_available=True):
        self._plan = plan
        self._error = error
        self._is_available = is_available
        self.called_with = None

    def available(self):
        return self._is_available

    def plan(self, intent):
        self.called_with = intent
        if self._error:
            raise self._error
        return self._plan


def test_unknown_intent_delegates_to_llm_planner_when_available():
    llm_plan = Plan(summary="llm made this", steps=[PlanStep(id="1", tool="browser", action="search", params={})])
    fake_llm = _FakeLLMPlanner(plan=llm_plan)
    planner = TaskPlanner(llm_planner=fake_llm)

    intent = parse_intent("do something ORBIT has no rule for")
    assert intent.action == "unknown"
    plan = planner.plan(intent)

    assert plan is llm_plan
    assert fake_llm.called_with is intent


def test_unknown_intent_falls_back_to_clarification_when_llm_fails():
    fake_llm = _FakeLLMPlanner(error=LLMPlanError("could not plan"))
    planner = TaskPlanner(llm_planner=fake_llm)

    intent = parse_intent("do something ORBIT has no rule for")
    plan = planner.plan(intent)

    assert plan.steps[0].tool == "system"
    assert plan.steps[0].action == "ask_clarification"


def test_unknown_intent_falls_back_to_clarification_when_llm_unavailable():
    fake_llm = _FakeLLMPlanner(is_available=False)
    planner = TaskPlanner(llm_planner=fake_llm)

    intent = parse_intent("do something ORBIT has no rule for")
    plan = planner.plan(intent)

    assert plan.steps[0].action == "ask_clarification"
    assert fake_llm.called_with is None  # never invoked -- available() gated it


def test_unknown_intent_asks_for_clarification_without_any_llm_planner():
    planner = TaskPlanner()  # no llm_planner configured at all -- default/offline behavior
    intent = parse_intent("do something ORBIT has no rule for")
    plan = planner.plan(intent)
    assert plan.steps[0].action == "ask_clarification"


def test_plan_summarize_with_named_file_searches_for_it():
    planner = TaskPlanner()
    intent = parse_intent("open this camscanner pdf in downloads and summarize it")
    plan = planner.plan(intent)
    assert plan.steps[0].tool == "pdf"
    assert plan.steps[0].action == "find_and_summarize"
    assert plan.steps[0].params == {"hint": "camscanner", "folder_hint": "downloads"}


def test_plan_summarize_without_named_file_uses_most_recent():
    # Regression: PdfTool.do_summarize requires a `path` -- calling it with
    # no params raised a raw Python TypeError instead of finding a file.
    planner = TaskPlanner()
    intent = parse_intent("open this PDF and summarize it")
    plan = planner.plan(intent)
    assert plan.steps[0].tool == "pdf"
    assert plan.steps[0].action == "find_and_summarize"
    assert plan.steps[0].params == {"hint": "", "folder_hint": None}


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
