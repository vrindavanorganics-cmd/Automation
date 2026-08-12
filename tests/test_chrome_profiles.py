import json

from orbit.browser import chrome_profiles


def _write_local_state(user_data_dir, profiles: dict) -> None:
    user_data_dir.mkdir(parents=True, exist_ok=True)
    local_state = {"profile": {"info_cache": profiles}}
    (user_data_dir / "Local State").write_text(json.dumps(local_state))


def test_list_chrome_profiles_maps_display_name_to_folder(tmp_path, monkeypatch):
    user_data_dir = tmp_path / "User Data"
    _write_local_state(
        user_data_dir,
        {
            "Default": {"name": "Rahul Soni"},
            "Profile 1": {"name": "Vrindavan Organics"},
            "Profile 2": {"name": "Ekagya Exports"},
        },
    )
    monkeypatch.setattr(chrome_profiles, "chrome_user_data_dir", lambda: user_data_dir)

    profiles = chrome_profiles.list_chrome_profiles()

    assert profiles == {
        "Rahul Soni": "Default",
        "Vrindavan Organics": "Profile 1",
        "Ekagya Exports": "Profile 2",
    }


def test_list_chrome_profiles_missing_local_state_returns_empty(tmp_path, monkeypatch):
    user_data_dir = tmp_path / "User Data"
    user_data_dir.mkdir()
    monkeypatch.setattr(chrome_profiles, "chrome_user_data_dir", lambda: user_data_dir)

    assert chrome_profiles.list_chrome_profiles() == {}


def test_list_chrome_profiles_no_chrome_returns_empty(monkeypatch):
    monkeypatch.setattr(chrome_profiles, "chrome_user_data_dir", lambda: None)
    assert chrome_profiles.list_chrome_profiles() == {}


def test_resolve_profile_dir_case_insensitive_exact_match(tmp_path, monkeypatch):
    user_data_dir = tmp_path / "User Data"
    _write_local_state(user_data_dir, {"Profile 1": {"name": "Vrindavan Organics"}})
    monkeypatch.setattr(chrome_profiles, "chrome_user_data_dir", lambda: user_data_dir)

    assert chrome_profiles.resolve_profile_dir("vrindavan organics") == "Profile 1"
    assert chrome_profiles.resolve_profile_dir("VRINDAVAN ORGANICS") == "Profile 1"


def test_resolve_profile_dir_partial_match(tmp_path, monkeypatch):
    user_data_dir = tmp_path / "User Data"
    _write_local_state(user_data_dir, {"Profile 1": {"name": "Vrindavan Organics"}})
    monkeypatch.setattr(chrome_profiles, "chrome_user_data_dir", lambda: user_data_dir)

    assert chrome_profiles.resolve_profile_dir("vrindavan") == "Profile 1"


def test_resolve_profile_dir_by_folder_name(tmp_path, monkeypatch):
    user_data_dir = tmp_path / "User Data"
    _write_local_state(user_data_dir, {"Profile 1": {"name": "Vrindavan Organics"}})
    monkeypatch.setattr(chrome_profiles, "chrome_user_data_dir", lambda: user_data_dir)

    assert chrome_profiles.resolve_profile_dir("Profile 1") == "Profile 1"


def test_resolve_profile_dir_no_match_returns_none(tmp_path, monkeypatch):
    user_data_dir = tmp_path / "User Data"
    _write_local_state(user_data_dir, {"Profile 1": {"name": "Vrindavan Organics"}})
    monkeypatch.setattr(chrome_profiles, "chrome_user_data_dir", lambda: user_data_dir)

    assert chrome_profiles.resolve_profile_dir("nonexistent") is None
    assert chrome_profiles.resolve_profile_dir("") is None
