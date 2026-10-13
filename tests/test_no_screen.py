"""A Pi with no screen plugged in is not told off for its full-screen display being off."""

from beranda import diagnostics, doctor, system


def _drm(tmp_path, *states):
    for i, state in enumerate(states):
        folder = tmp_path / f"card1-HDMI-A-{i + 1}"
        folder.mkdir()
        (folder / "status").write_text(state + "\n")
    return str(tmp_path)


def test_screen_detection(tmp_path):
    assert system.screen_plugged_in(_drm(tmp_path, "disconnected", "disconnected")) is False
    other = tmp_path / "b"
    other.mkdir()
    assert system.screen_plugged_in(_drm(other, "disconnected", "connected")) is True
    empty = tmp_path / "c"
    empty.mkdir()
    assert system.screen_plugged_in(str(empty)) is None  # cannot say: keep showing everything


def _fake_states(monkeypatch, kiosk):
    monkeypatch.setattr(diagnostics.shutil, "which", lambda name: "/bin/systemctl")
    monkeypatch.setattr(diagnostics, "_service_state", lambda n: kiosk if n == "beranda-kiosk" else "active")


def test_diagnostic_leaves_the_kiosk_out_without_a_screen(monkeypatch):
    _fake_states(monkeypatch, "deactivating")
    monkeypatch.setattr(system, "screen_plugged_in", lambda: False)
    text = "\n".join(diagnostics.device_lines())
    assert "beranda-kiosk=" not in text and "none plugged in" in text and "beranda=active" in text


def test_diagnostic_keeps_the_kiosk_with_a_screen_or_when_unsure(monkeypatch):
    _fake_states(monkeypatch, "inactive")
    for plugged in (True, None):
        monkeypatch.setattr(system, "screen_plugged_in", lambda p=plugged: p)
        assert "beranda-kiosk=inactive" in "\n".join(diagnostics.device_lines())


def test_diagnostic_shows_the_kiosk_if_it_runs_anyway(monkeypatch):
    _fake_states(monkeypatch, "active")
    monkeypatch.setattr(system, "screen_plugged_in", lambda: False)
    assert "beranda-kiosk=active" in "\n".join(diagnostics.device_lines())


def test_doctor_is_calm_without_a_screen(monkeypatch):
    class Done:
        stdout = "inactive\n"
    monkeypatch.setattr(doctor.shutil, "which", lambda n: "/bin/systemctl")
    monkeypatch.setattr(doctor.subprocess, "run", lambda *a, **k: Done())
    monkeypatch.setattr(system, "screen_plugged_in", lambda: False)
    text = "\n".join(doctor._services())
    assert "no screen plugged in" in text and "not running" not in text
