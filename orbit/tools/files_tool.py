"""Tool: file/folder create, read, rename, move, copy, organize, search."""
from __future__ import annotations

from orbit.files import fs_ops
from orbit.tools.base import Tool, ToolResult


class FilesTool(Tool):
    name = "files"
    sensitive_actions = {"delete_file", "delete_folder"}

    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir

    def do_create_folder(self, name: str, parent: str | None = None) -> ToolResult:
        path = f"{parent or self.base_dir}/{name}"
        created = fs_ops.create_folder(path)
        return ToolResult.ok(f"Created folder '{created}'", path=str(created))

    def do_create_file(self, name: str = "new_file.txt", content: str = "", parent: str | None = None) -> ToolResult:
        path = f"{parent or self.base_dir}/{name}"
        created = fs_ops.create_file(path, content)
        return ToolResult.ok(f"Created file '{created}'", path=str(created))

    def do_read_file(self, path: str) -> ToolResult:
        text = fs_ops.read_text(path)
        return ToolResult.ok(f"Read {len(text)} chars from {path}", path=path, content=text)

    def do_rename(self, path: str, new_name: str) -> ToolResult:
        target = fs_ops.rename(path, new_name)
        return ToolResult.ok(f"Renamed to '{target}'", path=str(target))

    def do_move(self, path: str, destination: str) -> ToolResult:
        target = fs_ops.move(path, destination)
        return ToolResult.ok(f"Moved to '{target}'", path=str(target))

    def do_copy(self, path: str, destination: str) -> ToolResult:
        target = fs_ops.copy(path, destination)
        return ToolResult.ok(f"Copied to '{target}'", path=str(target))

    def do_organize(self, directory: str | None = None) -> ToolResult:
        moved = fs_ops.organize_by_type(directory or self.base_dir)
        total = sum(len(v) for v in moved.values())
        return ToolResult.ok(f"Organized {total} file(s) into {len(moved)} categories", moved=moved)

    def do_find_file(self, query: str, directory: str | None = None) -> ToolResult:
        matches = fs_ops.find_by_keyword(directory or self.base_dir, query)
        return ToolResult.ok(f"Found {len(matches)} match(es) for '{query}'", matches=[str(m) for m in matches])

    def do_search(self, pattern: str = "*", directory: str | None = None) -> ToolResult:
        matches = fs_ops.search(directory or self.base_dir, pattern)
        return ToolResult.ok(f"Found {len(matches)} match(es)", matches=[str(m) for m in matches])
