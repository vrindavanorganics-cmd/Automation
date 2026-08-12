from orbit.models.manager import ModelManager
from orbit.windows.hardware import HardwareInfo


def test_model_manager_lists_catalog_with_fit_flags(tmp_path):
    manager = ModelManager(tmp_path)
    hw = HardwareInfo(os_name="Windows", os_version="11", cpu="x", cpu_cores=8, ram_gb=8, gpu=None, vram_gb=None)
    models = manager.list_models(hw)
    names = {m["name"] for m in models}
    assert {"tiny", "base", "small", "medium", "large-v3"} <= names
    small = next(m for m in models if m["name"] == "small")
    assert small["fits_hardware"] is True
    large = next(m for m in models if m["name"] == "large-v3")
    assert large["fits_hardware"] is False


def test_model_manager_install_and_active(tmp_path):
    manager = ModelManager(tmp_path)
    assert manager.is_installed("small") is False
    manager.mark_installed("small")
    assert manager.is_installed("small") is True
    manager.set_active("small")
    assert manager.get_active() == "small"
