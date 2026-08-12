#!/usr/bin/env python3
"""Lists the real Chrome profiles ORBIT can see on this PC, and which one
(if any) ORBIT_CHROME_PROFILE currently resolves to.

Usage:
    python scripts\\list_chrome_profiles.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    from orbit.browser.chrome_profiles import chrome_user_data_dir, list_chrome_profiles, resolve_profile_dir
    from orbit.config import settings

    root = chrome_user_data_dir()
    if not root:
        print("Could not find a Chrome install here (this is expected off Windows, or if Chrome has never run).")
        return

    print(f"Chrome profile folder: {root}\n")
    profiles = list_chrome_profiles()
    if not profiles:
        print("No profiles found.")
        return

    print("Profiles Chrome knows about:")
    for display_name, folder in profiles.items():
        print(f"  {display_name!r:30} -> {folder}")

    print()
    if settings.chrome_profile:
        folder = resolve_profile_dir(settings.chrome_profile)
        if folder:
            print(f"ORBIT_CHROME_PROFILE={settings.chrome_profile!r} resolves to folder '{folder}'.")
            print("ORBIT will open straight into this profile -- no picker shown.")
        else:
            print(f"ORBIT_CHROME_PROFILE={settings.chrome_profile!r} does NOT match any profile above.")
            print("Check the spelling against the names listed, or unset it to use the picker instead.")
    else:
        print("ORBIT_CHROME_PROFILE is not set -- Chrome will show its profile picker each time.")
        print("Set it in .env to one of the names above to skip the picker, e.g.:")
        print('  ORBIT_CHROME_PROFILE=Vrindavan Organics')


if __name__ == "__main__":
    main()
