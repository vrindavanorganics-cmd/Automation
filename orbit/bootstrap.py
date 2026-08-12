"""Wires up a complete ORBIT system: memory, vocabulary, permissions, tools,
windows control, skills, and the agent brain — from Settings.

This is the single place that knows how all the modules fit together, used
by main.py (the real voice loop), the desktop UI, and the test suite.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from orbit.agent.brain import OrbitBrain
from orbit.agent.planner import TaskPlanner
from orbit.asr.base import ASREngine
from orbit.asr.factory import get_asr_engine
from orbit.asr.vocabulary import VocabularyStore
from orbit.browser.chrome_profiles import chrome_user_data_dir, resolve_profile_dir
from orbit.config import Settings
from orbit.config import settings as default_settings
from orbit.email.sender import BrowserGmailSender, EmailSender, MockEmailSender
from orbit.memory.store import MemoryStore
from orbit.permissions.engine import ConfirmCallback, PermissionEngine
from orbit.skills.engine import SkillEngine
from orbit.tools.browser_tool import BrowserTool
from orbit.tools.email_tool import EmailTool
from orbit.tools.excel_tool import ExcelTool
from orbit.tools.files_tool import FilesTool
from orbit.tools.pdf_tool import PdfTool
from orbit.tools.registry import ToolRegistry
from orbit.tools.skills_tool import SkillsTool
from orbit.tools.system_tool import SystemTool
from orbit.tools.windows_apps import WindowsAppsTool
from orbit.windows.app_registry import AppRegistry
from orbit.windows.control import WindowsController, get_controller


@dataclass
class OrbitSystem:
    settings: Settings
    memory: MemoryStore
    vocabulary: VocabularyStore
    permission_engine: PermissionEngine
    tool_registry: ToolRegistry
    controller: WindowsController
    app_registry: AppRegistry
    skill_engine: SkillEngine
    asr_engine: ASREngine
    email_sender: EmailSender
    brain: OrbitBrain

    def shutdown(self) -> None:
        browser_tool = self.tool_registry.get("browser")
        if browser_tool is not None:
            browser_tool.shutdown()
        self.memory.close()


def build_orbit(
    settings: Optional[Settings] = None,
    confirm_callback: Optional[ConfirmCallback] = None,
    force_mock_asr: bool = False,
    email_sender: Optional[EmailSender] = None,
    browser_headless: Optional[bool] = None,
) -> OrbitSystem:
    settings = settings or default_settings

    memory = MemoryStore(settings.data_dir / "memory" / "orbit.db")
    vocabulary = VocabularyStore(memory)
    permission_engine = PermissionEngine(
        confirm_callback=confirm_callback, require_confirmation=settings.require_confirmation
    )

    controller = get_controller(force_simulated=settings.force_simulated_controller)
    app_registry = AppRegistry()
    app_registry.detect_installed()
    is_real_windows = controller.backend_name == "real-windows"

    # Headless by default (this workspace, tests, CI); on a real Windows
    # run, default to a visible browser so the user can log into Gmail the
    # first time -- the login then persists in browser_profile below.
    effective_headless = browser_headless if browser_headless is not None else not is_real_windows

    tool_registry = ToolRegistry()
    tool_registry.register(WindowsAppsTool(controller, app_registry))
    tool_registry.register(FilesTool(base_dir=str(settings.data_dir)))
    tool_registry.register(PdfTool())
    tool_registry.register(ExcelTool(base_dir=str(settings.data_dir)))

    # On a real Windows run, drive the user's actual, already-signed-in
    # Chrome (their real profiles -- Gmail, bookmarks, everything already
    # logged in) instead of a separate blank automation profile. If
    # ORBIT_CHROME_PROFILE names a profile, go straight into it; otherwise
    # Chrome shows its own "Who's using Chrome?" picker so the user picks.
    # Note: a profile already open in the user's regular Chrome can't also
    # be opened here -- Chrome locks each profile to one running process.
    real_chrome_root = chrome_user_data_dir() if is_real_windows else None
    if real_chrome_root:
        browser_profile_dir = str(real_chrome_root)
        browser_channel: Optional[str] = "chrome"
        chrome_args = None
        if settings.chrome_profile:
            folder = resolve_profile_dir(settings.chrome_profile)
            if folder:
                chrome_args = [f"--profile-directory={folder}"]
    else:
        browser_profile_dir = str(settings.data_dir / "browser_profile")
        browser_channel = None
        chrome_args = None

    browser_tool = BrowserTool(
        headless=effective_headless,
        profile_dir=browser_profile_dir,
        channel=browser_channel,
        chrome_args=chrome_args,
    )
    tool_registry.register(browser_tool)
    tool_registry.register(SystemTool())

    if email_sender is not None:
        sender: EmailSender = email_sender
    elif is_real_windows:
        sender = BrowserGmailSender(browser_tool)
    else:
        sender = MockEmailSender()
    tool_registry.register(EmailTool(sender=sender))

    skill_engine = SkillEngine(memory, tool_registry, permission_engine)
    tool_registry.register(SkillsTool(skill_engine))

    asr_engine = get_asr_engine(settings, force_mock=force_mock_asr)

    brain = OrbitBrain(
        asr_engine=asr_engine,
        vocabulary=vocabulary,
        tool_registry=tool_registry,
        permission_engine=permission_engine,
        memory=memory,
        planner=TaskPlanner(),
    )

    return OrbitSystem(
        settings=settings,
        memory=memory,
        vocabulary=vocabulary,
        permission_engine=permission_engine,
        tool_registry=tool_registry,
        controller=controller,
        app_registry=app_registry,
        skill_engine=skill_engine,
        asr_engine=asr_engine,
        email_sender=sender,
        brain=brain,
    )
