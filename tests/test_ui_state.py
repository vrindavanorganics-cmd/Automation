from orbit.ui.tray import OrbitStatus, TrayState


def test_tray_state_transitions():
    state = TrayState()
    assert state.status == OrbitStatus.READY
    state.set_listening()
    assert state.status == OrbitStatus.LISTENING
    state.set_task("Opening Chrome")
    assert state.status == OrbitStatus.ACTING
    assert state.current_task == "Opening Chrome"
    state.set_ready()
    assert state.status == OrbitStatus.READY
    assert state.current_task == ""


def test_tray_state_history_preview_limit():
    state = TrayState()
    for i in range(10):
        state.push_history(f"event {i}", limit=3)
    assert len(state.history_preview) == 3
    assert state.history_preview[0] == "event 9"
