from orbit.windows.hardware import HardwareInfo, detect_hardware, recommend_asr_model


def test_detect_hardware_returns_plausible_values():
    hw = detect_hardware()
    assert hw.cpu_cores >= 1
    assert hw.ram_gb > 0


def test_recommend_asr_model_low_ram():
    hw = HardwareInfo(os_name="Windows", os_version="10", cpu="x", cpu_cores=2, ram_gb=2.5, gpu=None, vram_gb=None)
    assert recommend_asr_model(hw) == "tiny"


def test_recommend_asr_model_high_ram():
    hw = HardwareInfo(os_name="Windows", os_version="11", cpu="x", cpu_cores=16, ram_gb=32, gpu=None, vram_gb=None)
    assert recommend_asr_model(hw) == "large-v3"


def test_recommend_asr_model_never_exceeds_ram():
    hw = HardwareInfo(os_name="Windows", os_version="11", cpu="x", cpu_cores=4, ram_gb=5.5, gpu=None, vram_gb=None)
    assert recommend_asr_model(hw) == "small"
