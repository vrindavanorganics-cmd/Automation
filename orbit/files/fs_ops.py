"""Real file-system operations (not GUI automation) — cross-platform and
fully testable in the browser workspace.
"""
from __future__ import annotations

import fnmatch
import hashlib
import shutil
from pathlib import Path
from typing import Optional


def create_folder(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_file(path: str | Path, content: str = "") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def rename(path: str | Path, new_name: str) -> Path:
    p = Path(path)
    target = p.parent / new_name
    p.rename(target)
    return target


def move(path: str | Path, destination: str | Path) -> Path:
    src = Path(path)
    dst = Path(destination)
    dst.mkdir(parents=True, exist_ok=True) if dst.suffix == "" else dst.parent.mkdir(parents=True, exist_ok=True)
    final = dst / src.name if dst.is_dir() or dst.suffix == "" else dst
    shutil.move(str(src), str(final))
    return final


def copy(path: str | Path, destination: str | Path) -> Path:
    src = Path(path)
    dst = Path(destination)
    if dst.is_dir() or dst.suffix == "":
        dst.mkdir(parents=True, exist_ok=True)
        final = dst / src.name
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        final = dst
    if src.is_dir():
        shutil.copytree(src, final, dirs_exist_ok=True)
    else:
        shutil.copy2(src, final)
    return final


def search(directory: str | Path, pattern: str = "*", recursive: bool = True) -> list[Path]:
    d = Path(directory)
    if not d.exists():
        return []
    iterator = d.rglob(pattern) if recursive else d.glob(pattern)
    return sorted(iterator)


def find_by_keyword(directory: str | Path, keyword: str) -> list[Path]:
    """Case-insensitive filename keyword search."""
    d = Path(directory)
    if not d.exists():
        return []
    keyword = keyword.lower()
    return sorted(p for p in d.rglob("*") if p.is_file() and keyword in p.name.lower())


def default_search_dirs() -> dict[str, Path]:
    home = Path.home()
    return {
        "downloads": home / "Downloads",
        "desktop": home / "Desktop",
        "documents": home / "Documents",
    }


def find_file_in_common_locations(
    hint: str,
    folder_hint: Optional[str] = None,
    extensions: tuple[str, ...] = (),
) -> Optional[Path]:
    """Finds a file by a loose name hint (e.g. "camscanner") across the
    user's usual folders (Downloads/Desktop/Documents), so a voice command
    like "summarize the camscanner pdf in downloads" doesn't require an
    exact path. Picks the most recently modified match when there's more
    than one. An empty hint matches every file with a matching extension --
    i.e. "the most recently modified one" -- covering "summarize this PDF"
    with no name given (usually means "the one I just got"). Returns None
    if nothing matches.
    """
    dirs = default_search_dirs()
    search_dirs = [dirs[folder_hint]] if folder_hint and folder_hint in dirs else list(dirs.values())
    hint_lower = hint.strip().lower()

    candidates: list[Path] = []
    for d in search_dirs:
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if not p.is_file():
                continue
            if extensions and p.suffix.lower() not in extensions:
                continue
            if hint_lower in p.name.lower():
                candidates.append(p)

    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


# Default extension -> category mapping used by organize_by_type.
EXTENSION_CATEGORIES = {
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf"},
    "Spreadsheets": {".xlsx", ".xls", ".csv", ".tsv"},
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"},
    "Presentations": {".ppt", ".pptx"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
}


def organize_by_type(directory: str | Path) -> dict[str, list[str]]:
    """Moves loose files in `directory` into category subfolders by
    extension. Returns {category: [moved file names]}. Non-matching
    extensions are left untouched (grouped under "Other" only if desired
    by the caller — kept conservative here).
    """
    d = Path(directory)
    moved: dict[str, list[str]] = {}
    if not d.exists():
        return moved

    ext_to_category = {ext: cat for cat, exts in EXTENSION_CATEGORIES.items() for ext in exts}

    for item in list(d.iterdir()):
        if item.is_dir():
            continue
        category = ext_to_category.get(item.suffix.lower())
        if not category:
            continue
        target_dir = d / category
        target_dir.mkdir(exist_ok=True)
        target = target_dir / item.name
        shutil.move(str(item), str(target))
        moved.setdefault(category, []).append(item.name)

    return moved


def file_hash(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def matches_glob(name: str, pattern: str) -> bool:
    return fnmatch.fnmatch(name.lower(), pattern.lower())
