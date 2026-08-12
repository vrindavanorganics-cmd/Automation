"""Tool: launch/close/focus Windows applications, using the AppRegistry to
resolve names/aliases and a WindowsController (simulated or real) to act.
"""
from __future__ import annotations

from orbit.tools.base import Tool, ToolResult
from orbit.windows.app_registry import AppRegistry
from orbit.windows.control import WindowsController


class WindowsAppsTool(Tool):
    name = "windows_apps"

    def __init__(self, controller: WindowsController, registry: AppRegistry):
        self.controller = controller
        self.registry = registry

    def do_open_app(self, app: str) -> ToolResult:
        if not app or not app.strip():
            return ToolResult.fail("No application specified to open")
        entry = self.registry.resolve(app)
        display_name = entry.name if entry else app
        # Prefer the full resolved path found by AppRegistry.detect_installed()
        # (via shutil.which()/common install locations) over the bare
        # executable name -- Windows only searches a handful of fixed
        # locations plus PATH for bare names, and most installers don't add
        # themselves to PATH, so a bare "chrome.exe" often silently fails
        # to actually launch anything even when Popen() itself succeeds.
        target = (entry.resolved_path if entry and entry.resolved_path else None) or (
            entry.executable if entry else app
        )
        launched = self.controller.launch_app(target)
        if not launched:
            if entry and entry.installed is False:
                return ToolResult.fail(
                    f"{display_name} does not appear to be installed on this PC", app=display_name
                )
            return ToolResult.fail(f"Failed to launch {display_name}", app=display_name)
        return ToolResult.ok(
            f"Launched {display_name}",
            app=display_name,
            backend=self.controller.backend_name,
            windows=self.controller.list_windows(),
        )

    def do_close_app(self, app: str) -> ToolResult:
        entry = self.registry.resolve(app)
        display_name = entry.name if entry else app
        closed = self.controller.close_app(display_name)
        if not closed:
            return ToolResult.fail(f"No open window found for {display_name}", app=display_name)
        return ToolResult.ok(f"Closed {display_name}", app=display_name)

    def do_list_windows(self) -> ToolResult:
        windows = self.controller.list_windows()
        return ToolResult.ok(f"{len(windows)} window(s) open", windows=windows)

    def do_focus_app(self, app: str) -> ToolResult:
        entry = self.registry.resolve(app)
        display_name = entry.name if entry else app
        focused = self.controller.focus_window(display_name)
        if not focused:
            return ToolResult.fail(f"Could not focus {display_name}", app=display_name)
        return ToolResult.ok(f"Focused {display_name}", app=display_name)
