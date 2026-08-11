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
from orbit.config import Settings
from orbit.config import settings as default_settings
from orbit.email.sender import EmailSender, MockEmailSender
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
    browser_headless: bool = True,
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

    tool_registry = ToolRegistry()
    tool_registry.register(WindowsAppsTool(controller, app_registry))
    tool_registry.register(FilesTool(base_dir=str(settings.data_dir)))
    tool_registry.register(PdfTool())
    tool_registry.register(ExcelTool(base_dir=str(settings.data_dir)))
    tool_registry.register(BrowserTool(headless=browser_headless))
    tool_registry.register(SystemTool())

    sender = email_sender or MockEmailSender()
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
