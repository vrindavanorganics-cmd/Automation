"""End-to-end tests of the ORBIT critical demo scenarios (spec section 20),
driven through text (ASR mocked) since no microphone/Windows desktop is
available in this workspace. Everything below the ASR layer is real:
intent parsing, planning, permission gating, tool execution (against a
SimulatedController), and verification.
"""
import pytest

from orbit.bootstrap import build_orbit
from orbit.config import Settings


@pytest.fixture
def system(tmp_path):
    settings = Settings(data_dir=tmp_path)
    sys = build_orbit(settings=settings, confirm_callback=lambda r: True, force_mock_asr=True)
    yield sys
    sys.shutdown()


@pytest.fixture
def denying_system(tmp_path):
    settings = Settings(data_dir=tmp_path / "denied")
    sys = build_orbit(settings=settings, confirm_callback=lambda r: False, force_mock_asr=True)
    yield sys
    sys.shutdown()


def test_demo_open_chrome(system):
    response = system.brain.process_text_command("Orbit, open Chrome.")
    assert response.intent.action == "open_app"
    assert response.outcomes[-1].result.success
    assert any("chrome" in w.lower() for w in system.controller.list_windows())


def test_demo_create_folder(system):
    response = system.brain.process_text_command("Orbit, create a folder called Buyer Leads.")
    assert response.intent.action == "create_folder"
    assert response.outcomes[-1].result.success
    assert (system.settings.data_dir / "Buyer Leads").is_dir()


def test_demo_pdf_summarize_plan_shape(system):
    response = system.brain.process_text_command("Orbit, open this PDF and summarize it.")
    assert response.intent.action == "summarize"
    assert response.plan.steps[0].tool == "pdf"
    # No filename was named, so this searches for (and summarizes) the most
    # recently modified PDF in the user's usual folders.
    assert response.plan.steps[0].action == "find_and_summarize"


def test_demo_create_excel_sheet(system):
    response = system.brain.process_text_command("Orbit, create an Excel sheet from this information.")
    assert response.intent.action == "create_excel"
    assert response.outcomes[-1].result.success
    assert (system.settings.data_dir / "output.xlsx").exists()


def test_demo_draft_email_then_dont_send_then_send(system):
    draft_result = system.tool_registry.run(
        "email", "draft", {"to": "buyer@example.com", "subject": "Quotation", "body": "Please find attached."}
    )
    assert draft_result.success

    dont_send = system.brain.process_text_command("Orbit, don't send it.")
    assert dont_send.intent.action == "cancel_send"
    assert dont_send.outcomes[-1].result.success

    # Nothing was sent because it was cancelled.
    assert system.email_sender.sent == []

    # Draft again, then actually send (confirmation auto-approved by fixture).
    system.tool_registry.run("email", "draft", {"to": "buyer2@example.com", "subject": "Quotation", "body": "Hi"})
    send_response = system.brain.process_text_command("Orbit, send it.")
    assert send_response.intent.action == "send"
    assert send_response.plan.steps[0].requires_approval is True
    assert send_response.outcomes[-1].result.success
    assert len(system.email_sender.sent) == 1


def test_send_without_confirmation_is_blocked(denying_system):
    denying_system.tool_registry.run(
        "email", "draft", {"to": "buyer@example.com", "subject": "Quotation", "body": "Hi"}
    )
    response = denying_system.brain.process_text_command("Orbit, send it.")
    assert response.outcomes[-1].result.success is False
    assert denying_system.email_sender.sent == []


def test_stop_command_halts_and_is_logged(system):
    response = system.brain.process_text_command("Orbit, stop.")
    assert response.stopped is True
    activity = system.memory.list_activity(limit=1)
    assert activity[0].command == "Orbit, stop."


def test_activity_history_is_recorded_for_every_command(system):
    system.brain.process_text_command("open chrome")
    system.brain.process_text_command("create a folder called Reports")
    records = system.memory.list_activity()
    assert len(records) >= 2
    assert all(r.status in ("success", "failed") for r in records)
