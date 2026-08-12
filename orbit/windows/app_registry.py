"""Registry of known Windows applications: name, executable, path, aliases,
launch method. Detection of actually-installed apps only works on Windows;
elsewhere the registry is still usable (data-driven, testable) but
`installed` stays unknown (None).

Locating an installed app's real path (`find_executable`) tries, in order:
  1. The Windows "App Paths" registry -- the same mechanism the Start Menu
     and Win+R "Run" dialog use to resolve a bare name like "chrome" to its
     real install location. This is authoritative and works regardless of
     which folder an app happens to be installed in.
  2. PATH (shutil.which).
  3. A short list of common install locations, if the caller supplied any.
  4. A bounded search of the usual install roots (Program Files, per-user
     Programs, etc.) for a file with that exact name -- a last resort for
     apps that don't register themselves properly, capped in depth so it
     can't turn into a full-disk crawl.
"""
from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Roots searched by the bounded filesystem fallback, and consulted for
# %ENV%-style expansion when building common_paths entries.
_SEARCH_ROOTS = [
    r"%ProgramFiles%",
    r"%ProgramFiles(x86)%",
    r"%LOCALAPPDATA%\Programs",
    r"%LOCALAPPDATA%",
    r"%APPDATA%",
]
_MAX_SEARCH_DEPTH = 4


def _query_app_paths_registry(executable: str) -> Optional[str]:
    """Looks up HKCU/HKLM ...\\App Paths\\<executable> -- the registry key
    Windows itself uses to resolve a bare executable name. Returns the
    real path on a hit, or None (including on any non-Windows platform,
    or if the `winreg` lookup fails for any reason).
    """
    try:
        import winreg  # type: ignore
    except ImportError:
        return None

    subkey = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{executable}"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, subkey) as key:
                value, _ = winreg.QueryValueEx(key, "")
                if value and Path(value).exists():
                    return value
        except (FileNotFoundError, OSError):
            continue
    return None


def _search_common_roots(executable: str) -> Optional[str]:
    """Bounded search of the usual install directories for a file with this
    exact name. Depth-limited so it stays fast -- this is a last resort,
    not a substitute for the registry lookup above.
    """
    target = executable.lower()
    for raw_root in _SEARCH_ROOTS:
        root = Path(os.path.expandvars(raw_root))
        if not root.is_dir():
            continue
        root_depth = len(root.parts)
        for dirpath, dirnames, filenames in os.walk(root):
            depth = len(Path(dirpath).parts) - root_depth
            if depth >= _MAX_SEARCH_DEPTH:
                dirnames[:] = []
                continue
            for filename in filenames:
                if filename.lower() == target:
                    return str(Path(dirpath) / filename)
    return None


def find_executable(executable: str, common_paths: Optional[list[str]] = None) -> Optional[str]:
    """Locates a Windows executable by name. Returns None on any
    non-Windows platform, or if every lookup strategy comes up empty.
    """
    if platform.system() != "Windows":
        return None

    found = _query_app_paths_registry(executable)
    if found:
        return found

    found = shutil.which(executable)
    if found:
        return found

    for raw_path in common_paths or []:
        expanded = os.path.expandvars(raw_path)
        if Path(expanded).exists():
            return expanded

    return _search_common_roots(executable)


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
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        aliases=["chrome", "google chrome", "browser"],
    ),
    AppEntry(
        name="Microsoft Edge",
        executable="msedge.exe",
        common_paths=[
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        aliases=["edge", "microsoft edge", "msedge"],
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
        if not needle:
            # An empty needle is a substring of every app name below, which
            # would otherwise silently resolve to whichever app happens to
            # be registered first. No name means no match.
            return None
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
        for app in self.apps.values():
            app.resolved_path = find_executable(app.executable, app.common_paths)
            app.installed = bool(app.resolved_path)

    def resolve_or_guess(self, name_or_alias: str) -> tuple[Optional[AppEntry], Optional[str]]:
        """Like resolve(), but for a name that isn't in the curated
        registry at all (e.g. "spotify"), also tries to locate it live on
        this Windows PC by guessing an executable name. Returns
        (matched AppEntry or None, resolved full path or None).
        """
        entry = self.resolve(name_or_alias)
        if entry:
            return entry, entry.resolved_path
        guess = name_or_alias.strip().lower().replace(" ", "")
        if not guess:
            return None, None
        if not guess.endswith(".exe"):
            guess += ".exe"
        return None, find_executable(guess)
