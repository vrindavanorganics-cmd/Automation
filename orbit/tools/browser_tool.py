"""Tool: browser automation (Playwright) — open, navigate, search, click,
type, read, extract, tabs, screenshots.

Lazily starts a BrowserController on first use and keeps it alive for the
rest of the session (closing/reopening a browser per command would be slow
and would lose tab/login state).
"""
from __future__ import annotations

from typing import Optional

from orbit.browser.playwright_controller import BrowserController
from orbit.tools.base import Tool, ToolResult


class BrowserTool(Tool):
    name = "browser"

    def __init__(
        self,
        headless: bool = True,
        profile_dir: Optional[str] = None,
        channel: Optional[str] = None,
        chrome_args: Optional[list[str]] = None,
    ):
        self.headless = headless
        self.profile_dir = profile_dir
        self.channel = channel
        self.chrome_args = chrome_args
        self._controller: Optional[BrowserController] = None

    def _ensure_started(self) -> BrowserController:
        if self._controller is None:
            self._controller = BrowserController(
                headless=self.headless,
                profile_dir=self.profile_dir,
                channel=self.channel,
                chrome_args=self.chrome_args,
            )
            self._controller.start()
        return self._controller

    def get_controller(self) -> BrowserController:
        """Public accessor so other tools (e.g. the email tool's Gmail
        sender) can share this same browser session -- one login, reused
        across commands -- instead of opening a second, separate browser.
        """
        return self._ensure_started()

    def shutdown(self) -> None:
        if self._controller:
            self._controller.stop()
            self._controller = None

    def do_open(self, url: str = "about:blank") -> ToolResult:
        bc = self._ensure_started()
        info = bc.goto(url)
        return ToolResult.ok(f"Opened {info.url}", url=info.url, title=info.title)

    def do_goto(self, url: str) -> ToolResult:
        return self.do_open(url)

    def do_search(self, query: str) -> ToolResult:
        bc = self._ensure_started()
        info = bc.search(query)
        return ToolResult.ok(f"Searched for '{query}'", url=info.url, title=info.title, text=info.text[:2000])

    def do_click(self, selector: str) -> ToolResult:
        bc = self._ensure_started()
        bc.click(selector)
        return ToolResult.ok(f"Clicked '{selector}'", selector=selector)

    def do_type(self, selector: str, text: str) -> ToolResult:
        bc = self._ensure_started()
        bc.type_text(selector, text)
        return ToolResult.ok(f"Typed into '{selector}'", selector=selector)

    def do_extract_text(self, selector: str = "body") -> ToolResult:
        bc = self._ensure_started()
        text = bc.extract_text(selector)
        return ToolResult.ok(f"Extracted {len(text)} chars", selector=selector, text=text)

    def do_screenshot(self, path: str) -> ToolResult:
        bc = self._ensure_started()
        bc.screenshot(path)
        return ToolResult.ok(f"Saved screenshot to {path}", path=path)

    def do_list_tabs(self) -> ToolResult:
        bc = self._ensure_started()
        return ToolResult.ok("Listed tabs", tabs=bc.list_tabs())

    def do_new_tab(self, url: Optional[str] = None) -> ToolResult:
        bc = self._ensure_started()
        index = bc.new_tab(url)
        return ToolResult.ok(f"Opened new tab (index {index})", index=index)

    def do_find_contacts(self, companies: list[str]) -> ToolResult:
        # Placeholder for a real contact-lookup workflow (e.g. company
        # website contact page or CRM search). Requires a defined data
        # source; returns unresolved contacts so the caller/skill can
        # supply them explicitly or teach ORBIT this step via Teach Mode.
        return ToolResult.ok(
            "Contact lookup requires a configured data source (CRM/website) — none configured yet",
            companies=companies,
            contacts={},
        )
