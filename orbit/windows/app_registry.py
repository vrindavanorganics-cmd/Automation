"""Registry of known Windows applications: name, executable, path, aliases,
launch method. Detection of actually-installed apps only works on Windows;
elsewhere the registry is still usable (data-driven, testable) but
`installed` stays unknown (None).
"""
from __future__ import annotations

import platform
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AppEntry:
    name: str
    executable: str
    common_paths: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    launch_method: str = "executable"  # "executable" | "uwp" | "protocol"
    installed: Optional[bool] = None
    resolved_path: Optional[str] = None


DEFAULT_APPS: list[AppEntry] = [
    AppEntry(
        name="Google Chrome",
        executable="chrome.exe",
        common_paths=[
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        aliases=["chrome", "google chrome", "browser"],
    ),
    AppEntry(
        name="Microsoft Excel",
        executable="EXCEL.EXE",
        common_paths=[r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"],
        aliases=["excel", "spreadsheet"],
    ),
    AppEntry(
        name="Microsoft Word",
        executable="WINWORD.EXE",
        common_paths=[r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"],
        aliases=["word", "ms word"],
    ),
    AppEntry(
        name="Notion",
        executable="Notion.exe",
        common_paths=[r"%LOCALAPPDATA%\Programs\Notion\Notion.exe"],
        aliases=["notion"],
    ),
    AppEntry(
        name="Visual Studio Code",
        executable="Code.exe",
        common_paths=[r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"],
        aliases=["vs code", "vscode", "code"],
    ),
    AppEntry(
        name="WhatsApp",
        executable="WhatsApp.exe",
        common_paths=[r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"],
        aliases=["whatsapp"],
        launch_method="uwp",
    ),
    AppEntry(
        name="File Explorer",
        executable="explorer.exe",
        common_paths=[r"C:\Windows\explorer.exe"],
        aliases=["file explorer", "explorer", "files"],
    ),
]


class AppRegistry:
    def __init__(self, apps: Optional[list[AppEntry]] = None):
        self.apps: dict[str, AppEntry] = {a.name: a for a in (apps or [e for e in DEFAULT_APPS])}

    def register(self, app: AppEntry) -> None:
        self.apps[app.name] = app

    def resolve(self, name_or_alias: str) -> Optional[AppEntry]:
        needle = name_or_alias.strip().lower()
        for app in self.apps.values():
            if app.name.lower() == needle:
                return app
        for app in self.apps.values():
            if needle in [a.lower() for a in app.aliases]:
                return app
        # fuzzy-ish substring fallback
        for app in self.apps.values():
            if needle in app.name.lower():
                return app
        return None

    def list_apps(self) -> list[AppEntry]:
        return list(self.apps.values())

    def detect_installed(self) -> None:
        """Best-effort installed-app detection. Only meaningful on Windows;
        on other platforms every app stays `installed=None` (unknown).
        """
        if platform.system() != "Windows":
            return
        import os

        for app in self.apps.values():
            found = shutil.which(app.executable)
            if not found:
                for raw_path in app.common_paths:
                    expanded = os.path.expandvars(raw_path)
                    if Path(expanded).exists():
                        found = expanded
                        break
            app.installed = bool(found)
            app.resolved_path = found
