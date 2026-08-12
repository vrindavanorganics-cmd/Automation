"""Browser control via Playwright — real, testable browser automation.

Runs headless by default (required in this browser workspace / on a
headless server); on the user's local Windows PC it can run headed so they
can see ORBIT working.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class PageInfo:
    url: str
    title: str
    text: str


def _default_chromium_executable() -> Optional[str]:
    """Locates the pre-installed Chromium binary when the pip `playwright`
    package version doesn't exactly match the pre-downloaded browser build
    (common in this sandboxed workspace). Returns None to let Playwright use
    its own resolution (e.g. on a normal local Windows install).
    """
    override = os.environ.get("ORBIT_CHROMIUM_PATH")
    if override:
        return override
    browsers_dir = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not browsers_dir or not os.path.isdir(browsers_dir):
        return None
    for entry in sorted(os.listdir(browsers_dir), reverse=True):
        if entry.startswith("chromium-"):
            candidate = os.path.join(browsers_dir, entry, "chrome-linux", "chrome")
            if os.path.exists(candidate):
                return candidate
    return None


class BrowserController:
    """Thin synchronous wrapper around Playwright's sync API.

    With `profile_dir` set, uses a persistent browser profile (cookies,
    local storage, logins) stored on disk under that path -- so logging
    into Gmail once in ORBIT stays logged in across future runs, the same
    way a normal browser profile would. Without it, each session starts
    from a clean slate (used for headless search/summarize/scrape tasks
    that don't need any login state).
    """

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        executable_path: Optional[str] = None,
        profile_dir: Optional[str] = None,
    ):
        self.headless = headless
        self.browser_type = browser_type
        self.executable_path = executable_path
        self.profile_dir = profile_dir
        self._playwright = None
        self._browser = None
        self._context = None
        self._pages: list = []
        self._active_index = 0

    def start(self) -> None:
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        launcher = getattr(self._playwright, self.browser_type)
        exe = self.executable_path or (
            _default_chromium_executable() if self.browser_type == "chromium" else None
        )

        if self.profile_dir:
            os.makedirs(self.profile_dir, exist_ok=True)
            launch_kwargs = {"headless": self.headless, "user_data_dir": self.profile_dir}
            if exe:
                launch_kwargs["executable_path"] = exe
            self._context = launcher.launch_persistent_context(**launch_kwargs)
            self._browser = None
            page = self._context.pages[0] if self._context.pages else self._context.new_page()
        else:
            launch_kwargs = {"headless": self.headless}
            if exe:
                launch_kwargs["executable_path"] = exe
            self._browser = launcher.launch(**launch_kwargs)
            self._context = self._browser.new_context()
            page = self._context.new_page()

        self._pages = [page]
        self._active_index = 0

    def stop(self) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._pages = []

    def __enter__(self) -> "BrowserController":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    @property
    def page(self):
        return self._pages[self._active_index]

    def goto(self, url: str) -> PageInfo:
        self.page.goto(url, wait_until="domcontentloaded")
        return self.current_page_info()

    def current_page_info(self) -> PageInfo:
        return PageInfo(url=self.page.url, title=self.page.title(), text=self.page.inner_text("body"))

    def click(self, selector: str) -> bool:
        self.page.click(selector)
        return True

    def type_text(self, selector: str, text: str) -> bool:
        self.page.fill(selector, text)
        return True

    def extract_text(self, selector: str = "body") -> str:
        return self.page.inner_text(selector)

    def search(self, query: str, engine_url: str = "https://duckduckgo.com/html/?q={query}") -> PageInfo:
        self.goto(engine_url.format(query=query.replace(" ", "+")))
        return self.current_page_info()

    def new_tab(self, url: Optional[str] = None) -> int:
        page = self._context.new_page()
        self._pages.append(page)
        self._active_index = len(self._pages) - 1
        if url:
            self.goto(url)
        return self._active_index

    def switch_tab(self, index: int) -> bool:
        if 0 <= index < len(self._pages):
            self._active_index = index
            return True
        return False

    def list_tabs(self) -> list[str]:
        return [p.url for p in self._pages]

    def screenshot(self, path: str) -> str:
        self.page.screenshot(path=path)
        return path

    def download(self, trigger_selector: str, save_path: str) -> str:
        with self.page.expect_download() as dl_info:
            self.page.click(trigger_selector)
        download = dl_info.value
        download.save_as(save_path)
        return save_path
