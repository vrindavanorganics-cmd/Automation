"""Task planner: turns an Intent into an ordered, executable Plan.

Simple intents (open an app, create a folder) become a single PlanStep.
Complex intents become a multi-step plan with explicit approval and
verification points, mirroring the ORBIT spec example:

    "Send quotation to these 5 companies" ->
        1. Find contacts
        2. Find quotation
        3. Draft personalized emails
        4. Attach quotation
        5. Show summary
        6. Ask approval
        7. Send
        8. Verify
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from orbit.agent.intent import Intent
from orbit.permissions.engine import SENSITIVE_ACTIONS


@dataclass
class PlanStep:
    id: str
    tool: str
    action: str
    params: dict = field(default_factory=dict)
    description: str = ""
    requires_approval: bool = False
    verification: dict = field(default_factory=dict)
    retry: int = 0


@dataclass
class Plan:
    summary: str
    steps: list[PlanStep] = field(default_factory=list)
    source_intent: Optional[Intent] = None

    def __iter__(self):
        return iter(self.steps)

    def __len__(self):
        return len(self.steps)


def _requires_approval(action: str) -> bool:
    return action in SENSITIVE_ACTIONS


class TaskPlanner:
    """Rule-based planner for V1. A cloud-LLM-backed planner can be swapped
    in later for genuinely ambiguous multi-step requests without changing
    the Plan/PlanStep contract that tools and the executor rely on.
    """

    def plan(self, intent: Intent) -> Plan:
        method = getattr(self, f"_plan_{intent.action}", None)
        if method is None:
            return self._plan_unknown(intent)
        return method(intent)

    # ---- simple, single-step intents ----

    def _plan_open_app(self, intent: Intent) -> Plan:
        app = intent.entities.get("app", "")
        step = PlanStep(
            id="1",
            tool="windows_apps",
            action="open_app",
            params={"app": app},
            description=f"Open {app or 'the requested application'}",
            verification={"type": "window_open", "app_name": app},
        )
        return Plan(summary=f"Open {app or 'application'}", steps=[step], source_intent=intent)

    def _plan_close_app(self, intent: Intent) -> Plan:
        app = intent.entities.get("app", "")
        step = PlanStep(
            id="1",
            tool="windows_apps",
            action="close_app",
            params={"app": app},
            description=f"Close {app or 'the requested application'}",
        )
        return Plan(summary=f"Close {app or 'application'}", steps=[step], source_intent=intent)

    def _plan_create_folder(self, intent: Intent) -> Plan:
        name = intent.entities.get("folder_name", "New Folder")
        step = PlanStep(
            id="1",
            tool="files",
            action="create_folder",
            params={"name": name},
            description=f"Create folder '{name}'",
            verification={"type": "file_exists"},
        )
        return Plan(summary=f"Create folder '{name}'", steps=[step], source_intent=intent)

    def _plan_create_file(self, intent: Intent) -> Plan:
        step = PlanStep(
            id="1",
            tool="files",
            action="create_file",
            params={},
            description="Create file",
            verification={"type": "file_exists"},
        )
        return Plan(summary="Create file", steps=[step], source_intent=intent)

    def _plan_read_pdf(self, intent: Intent) -> Plan:
        # An empty hint means "no name given" -- find_and_read then falls
        # back to the most recently modified PDF (usually "the one I just
        # got"), rather than making the user name the file every time.
        hint = intent.entities.get("file_hint", "")
        step = PlanStep(
            id="1",
            tool="pdf",
            action="find_and_read",
            params={"hint": hint, "folder_hint": intent.entities.get("folder_hint")},
            description=f"Read PDF matching '{hint}'" if hint else "Read the most recent PDF",
        )
        return Plan(summary=step.description, steps=[step], source_intent=intent)

    def _plan_summarize(self, intent: Intent) -> Plan:
        hint = intent.entities.get("file_hint", "")
        step = PlanStep(
            id="1",
            tool="pdf",
            action="find_and_summarize",
            params={"hint": hint, "folder_hint": intent.entities.get("folder_hint")},
            description=f"Summarize PDF matching '{hint}'" if hint else "Summarize the most recent PDF",
        )
        return Plan(summary=step.description, steps=[step], source_intent=intent)

    def _plan_create_excel(self, intent: Intent) -> Plan:
        step = PlanStep(
            id="1",
            tool="excel",
            action="create",
            params={},
            description="Create Excel sheet",
            verification={"type": "file_exists"},
        )
        return Plan(summary="Create Excel sheet", steps=[step], source_intent=intent)

    def _plan_draft_email(self, intent: Intent) -> Plan:
        to = intent.entities.get("to")
        if not to:
            return self._ask(
                "Who should I send this to? Include an email address, e.g. "
                "'draft email to buyer@example.com saying thanks for your order'.",
                intent,
            )
        body = intent.entities.get("body", "")
        subject = intent.entities.get("subject") or (body[:60] if body else "(no subject)")
        step = PlanStep(
            id="1",
            tool="email",
            action="draft",
            params={"to": to, "subject": subject, "body": body},
            description=f"Draft email to {to}",
            requires_approval=False,
        )
        return Plan(summary=f"Draft email to {to}", steps=[step], source_intent=intent)

    def _plan_read_email(self, intent: Intent) -> Plan:
        step = PlanStep(id="1", tool="email", action="read", params={}, description="Check inbox")
        return Plan(summary="Check inbox", steps=[step], source_intent=intent)

    def _plan_send(self, intent: Intent) -> Plan:
        step = PlanStep(
            id="1",
            tool="email",
            action="send_email",
            params={},
            description="Send the drafted email",
            requires_approval=True,
        )
        return Plan(summary="Send email", steps=[step], source_intent=intent)

    def _plan_cancel_send(self, intent: Intent) -> Plan:
        step = PlanStep(id="1", tool="email", action="cancel_send", params={}, description="Cancel pending send")
        return Plan(summary="Cancel send", steps=[step], source_intent=intent)

    def _plan_organize_files(self, intent: Intent) -> Plan:
        step = PlanStep(id="1", tool="files", action="organize", params={}, description="Organize files")
        return Plan(summary="Organize files", steps=[step], source_intent=intent)

    def _plan_search(self, intent: Intent) -> Plan:
        query = intent.entities.get("query", intent.interpreted_text)
        step = PlanStep(
            id="1", tool="browser", action="search", params={"query": query}, description=f"Search: {query}"
        )
        return Plan(summary=f"Search: {query}", steps=[step], source_intent=intent)

    def _plan_research(self, intent: Intent) -> Plan:
        return self._plan_search(intent)

    def _plan_run_skill(self, intent: Intent) -> Plan:
        step = PlanStep(
            id="1",
            tool="skills",
            action="run_skill",
            params={"query": intent.interpreted_text},
            description="Run a learned skill",
        )
        return Plan(summary="Run learned skill", steps=[step], source_intent=intent)

    def _plan_stop(self, intent: Intent) -> Plan:
        step = PlanStep(id="1", tool="system", action="stop", params={}, description="Stop current action")
        return Plan(summary="Stop", steps=[step], source_intent=intent)

    def _plan_unknown(self, intent: Intent) -> Plan:
        step = PlanStep(
            id="1",
            tool="system",
            action="ask_clarification",
            params={"heard": intent.interpreted_text},
            description="Ask the user to clarify the command",
        )
        return Plan(summary="Clarification needed", steps=[step], source_intent=intent)

    def _ask(self, message: str, intent: Intent) -> Plan:
        """Used when an action was understood but is missing a required
        detail (recipient, filename, ...) -- asks instead of failing.
        """
        step = PlanStep(
            id="1", tool="system", action="ask", params={"message": message}, description="Ask for missing detail"
        )
        return Plan(summary="Need more detail", steps=[step], source_intent=intent)

    # ---- complex multi-step plan builder (spec example: bulk outreach) ----

    def plan_bulk_outreach(self, companies: list[str], template: str, attachment: Optional[str] = None) -> Plan:
        """Builds the 8-step outreach plan described in the ORBIT spec:
        find contacts -> find quotation -> draft -> attach -> summary ->
        approval -> send -> verify.
        """
        steps = [
            PlanStep(
                id="1",
                tool="browser",
                action="find_contacts",
                params={"companies": companies},
                description=f"Find contact emails for {len(companies)} companies",
            ),
            PlanStep(
                id="2",
                tool="files",
                action="find_file",
                params={"query": attachment or "quotation"},
                description="Find the quotation/attachment file",
            ),
            PlanStep(
                id="3",
                tool="email",
                action="draft_bulk",
                params={"companies": companies, "template": template},
                description=f"Draft {len(companies)} personalized emails",
            ),
            PlanStep(
                id="4",
                tool="email",
                action="attach",
                params={"attachment": attachment},
                description="Attach quotation to each draft",
            ),
            PlanStep(
                id="5",
                tool="system",
                action="show_summary",
                params={},
                description="Show summary of prepared emails",
            ),
            PlanStep(
                id="6",
                tool="system",
                action="ask_approval",
                params={},
                description="Ask user for approval before sending",
                requires_approval=True,
            ),
            PlanStep(
                id="7",
                tool="email",
                action="send_bulk",
                params={"companies": companies},
                description=f"Send {len(companies)} emails",
                requires_approval=True,
            ),
            PlanStep(
                id="8",
                tool="email",
                action="verify_sent",
                params={"companies": companies},
                description="Verify all emails were sent",
            ),
        ]
        return Plan(summary=f"Buyer outreach to {len(companies)} companies", steps=steps)
