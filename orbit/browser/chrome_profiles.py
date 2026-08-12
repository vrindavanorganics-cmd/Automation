"""Reads Chrome's own profile list (Local State) so ORBIT can drive a real,
already-signed-in Chrome profile (e.g. "Vrindavan Organics") instead of a
blank, separate automation profile.

Chrome names profiles internally by folder ("Default", "Profile 1", "Profile
2", ...) but shows the human-chosen display name ("Vrindavan Organics") in
its UI. That mapping lives in Chrome's `Local State` JSON file, which this
module reads (read-only -- never writes Chrome's own files).
"""
from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Optional


def chrome_user_data_dir() -> Optional[Path]:
    """The root folder holding all of a user's Chrome profiles. Only
    resolvable on Windows -- returns None elsewhere.
    """
    if platform.system() != "Windows":
        return None
    path = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"))
    return path if path.is_dir() else None


def list_chrome_profiles() -> dict[str, str]:
    """Returns {display_name: folder_name}, e.g.
    {"Vrindavan Organics": "Profile 1", "Personal": "Default"}.
    Empty dict if Chrome/its profile list can't be found (including on any
    non-Windows platform, or before Chrome has ever been run).
    """
    user_data_dir = chrome_user_data_dir()
    if not user_data_dir:
        return {}
    local_state_path = user_data_dir / "Local State"
    if not local_state_path.exists():
        return {}
    try:
        data = json.loads(local_state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    info_cache = data.get("profile", {}).get("info_cache", {})
    return {info.get("name", folder): folder for folder, info in info_cache.items()}


def resolve_profile_dir(name_or_folder: str) -> Optional[str]:
    """Matches a spoken/typed profile name (case-insensitive, partial) or an
    exact folder name (e.g. "Profile 1") to Chrome's real folder name.
    """
    profiles = list_chrome_profiles()
    needle = name_or_folder.strip().lower()
    if not needle:
        return None

    for display_name, folder in profiles.items():
        if display_name.lower() == needle or folder.lower() == needle:
            return folder
    for display_name, folder in profiles.items():
        if needle in display_name.lower():
            return folder
    return None
