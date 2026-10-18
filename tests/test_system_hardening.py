"""The root-side pieces (beranda-action, the Wi-Fi job runner, the safety net, the installer),
checked without a Pi: shell scripts run in a scratch folder with stand-in commands, and every
nmcli call is faked."""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from beranda import system, wifi, wifi_setup
from beranda.wifi_setup import AP_CON_NAME, AP_SSID

ROOT = Path(__file__).resolve().parent.parent
needs_root = pytest.mark.skipif(os.geteuid() != 0, reason="the ownership checks only pass for files root owns")


# ------------------------------------------------------------------ 60: install.env ---
def _action_sandbox(tmp_path, env_text):
    prefix = tmp_path / "prefix"
    (prefix / "bin").mkdir(parents=True)
    shutil.copy(ROOT / "system" / "beranda-action", prefix / "bin" / "beranda-action")
    (tmp_path / "state" / "requests").mkdir(parents=True)
    (prefix / "install.env").write_text(env_text.replace("@T@", str(tmp_path)))
    return prefix


@needs_root
def test_beranda_action_reads_install_env_without_running_it(tmp_path):
    prefix = _action_sandbox(
        tmp_path,
        "STATEDIR=@T@/state\nBRANCH=main\ntouch @T@/PWNED_LINE\nCONFDIR=$(touch @T@/PWNED_SUBST)\n",
    )
    out = subprocess.run(["bash", str(prefix / "bin" / "beranda-action")], capture_output=True, text=True, check=False)
    assert out.returncode == 0, out.stderr
    assert not (tmp_path / "PWNED_LINE").exists() and not (tmp_path / "PWNED_SUBST").exists()


@needs_root
def test_beranda_action_refuses_an_install_env_others_can_write(tmp_path):
    prefix = _action_sandbox(tmp_path, "STATEDIR=@T@/state\n")
    (tmp_path / "state" / "requests" / "nonsense").write_text("")
    os.chmod(prefix / "install.env", 0o666)  # noqa: S103 - the very mistake the helper must refuse
    out = subprocess.run(["bash", str(prefix / "bin" / "beranda-action")], capture_output=True, text=True, check=False)
    assert out.returncode != 0
    assert (tmp_path / "state" / "requests" / "nonsense").exists()  # nothing was carried out


def test_install_info_lives_in_the_root_owned_folder_with_the_old_place_as_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("BERANDA_INSTALL_INFO", raising=False)
    new, old = tmp_path / "opt.env", tmp_path / "etc.env"
    monkeypatch.setattr(system, "INSTALL_INFO", new)
    monkeypatch.setattr(system, "LEGACY_INSTALL_INFO", old)
    old.write_text("COMMIT=old1234\n")
    assert system.install_info()["COMMIT"] == "old1234"
    new.write_text("COMMIT=new1234\n")
    assert system.install_info()["COMMIT"] == "new1234"


def test_the_installer_writes_install_env_where_only_root_can_write():
    text = (ROOT / "install.sh").read_text()
    assert 'cat > "$PREFIX/install.env"' in text and 'cat > "$CONFDIR/install.env"' not in text
    assert "BERANDA_INSTALL_INFO=@PREFIX@/install.env" in (ROOT / "system" / "beranda.service.in").read_text()
    for script in ("system/beranda-action", "uninstall.sh"):
        assert "source " not in (ROOT / script).read_text(), script


# ------------------------------------------------------------------ 61: the job answers ---
def test_a_wifi_answer_never_follows_a_planted_link(tmp_path, monkeypatch):
    monkeypatch.setattr(wifi, "_run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "", ""))
    answers = tmp_path / "answers"
    answers.mkdir()
    victim = tmp_path / "victim"
    victim.write_text("precious")
    os.chmod(victim, 0o755)  # noqa: S103 - a program-like file, to see its mode is left alone
    (answers / ".aaaaaaaaaaaa.tmp").symlink_to(victim)
    monkeypatch.setenv("BERANDA_WIFI_JOBS", str(answers))
    request = tmp_path / "wifi-aaaaaaaaaaaa.json"
    request.write_text(json.dumps({"op": "radio_on"}))
    os.chmod(request, 0o600)
    wifi.job_main([str(request)])
    assert victim.read_text() == "precious" and stat.S_IMODE(victim.stat().st_mode) == 0o755
    assert json.loads((answers / "aaaaaaaaaaaa.json").read_text())["done"] is True


def test_a_wifi_request_that_is_a_link_is_refused(tmp_path, monkeypatch):
    secret = tmp_path / "secret"
    secret.write_text(json.dumps({"op": "status"}))
    request = tmp_path / "wifi-bbbbbbbbbbbb.json"
    request.symlink_to(secret)
    monkeypatch.setenv("BERANDA_WIFI_JOBS", str(tmp_path / "answers"))
    called = []
    monkeypatch.setattr(wifi, "run_job", lambda job: called.append(job) or {"ok": True})
    wifi.job_main([str(request)])
    assert {"op": "status"} not in called
    assert secret.exists()


def test_the_safety_net_status_never_follows_a_planted_link(tmp_path, monkeypatch):
    victim = tmp_path / "victim"
    victim.write_text("precious")
    link = tmp_path / "wifi-setup.json"
    link.symlink_to(victim)
    monkeypatch.setenv("BERANDA_WIFI_STATUS", str(link))
    wifi_setup.write_status(AP_SSID)
    assert victim.read_text() == "precious"
    assert not link.is_symlink() and json.loads(link.read_text())["ssid"] == AP_SSID


# ------------------------------------------------------------------ installer: 62, 63, 64 ---
def _dry(tmp_path, *args, path_prefix=None):
    env = dict(os.environ)
    if path_prefix:
        env["PATH"] = f"{path_prefix}:{env['PATH']}"
    return subprocess.run(["bash", str(ROOT / "install.sh"), "--dry-run", "--prefix", str(tmp_path / "p"), *args],
                          capture_output=True, text=True, check=True, env=env).stdout


def test_rerunning_the_installer_restarts_the_server_so_the_update_takes_effect(tmp_path):
    out = _dry(tmp_path)
    assert "systemctl restart beranda.service" in out


def test_rerunning_the_installer_over_a_copy_without_git_replaces_it(tmp_path):
    (tmp_path / "p" / "src").mkdir(parents=True)
    out = _dry(tmp_path)
    lines = out.splitlines()
    rm = next(i for i, line in enumerate(lines) if f"rm -rf {tmp_path}/p/src" in line)
    clone = next(i for i, line in enumerate(lines) if "git clone" in line)
    assert rm < clone


def test_the_image_and_the_update_button_cope_with_a_copy_without_git():
    chroot = (ROOT / "pi-gen/stage-beranda/00-install-beranda/00-run-chroot.sh").read_text()
    assert "git -C /opt/beranda/src init" in chroot
    assert "init" in (ROOT / "system" / "beranda-action").read_text()


def _fake_network_manager(tmp_path):
    fake = tmp_path / "fakebin"
    fake.mkdir()
    (fake / "systemctl").write_text("#!/bin/sh\nexit 0\n")
    (fake / "nmcli").write_text("#!/bin/sh\necho wifi\n")
    for f in fake.iterdir():
        f.chmod(0o755)
    return fake


def test_a_refused_safety_net_stays_refused_on_a_plain_rerun(tmp_path):
    fake = _fake_network_manager(tmp_path)
    assert "beranda-wifi-setup" in _dry(tmp_path, path_prefix=fake)  # NetworkManager seen: on by default
    (tmp_path / "p").mkdir(exist_ok=True)
    (tmp_path / "p" / "install.env").write_text("PREFIX=/opt/beranda\nWIFI_SETUP=0\n")
    out = _dry(tmp_path, path_prefix=fake)
    assert "network-manager" not in out and "write /etc/systemd/system/beranda-wifi-setup" not in out


def test_after_update_leaves_a_refused_safety_net_alone():
    text = (ROOT / "system" / "beranda-action").read_text()
    elif_line = next(line for line in text.splitlines() if line.strip().startswith("elif") and "wifi-setup" in line)
    assert 'WIFI_SETUP:-auto}" != 0' in elif_line


# ------------------------------------------------------------------ the safety net: 65-68 ---
class _Nmcli:
    def __init__(self, up_ok=True, active=""):
        self.calls, self.up_ok, self.active = [], up_ok, active

    def __call__(self, args):
        self.calls.append(list(args))
        if args[:3] == ["nmcli", "connection", "up"]:
            return subprocess.CompletedProcess(args, 0 if self.up_ok else 4, "", "Error: failed")
        if "--active" in args:
            return subprocess.CompletedProcess(args, 0, self.active, "")
        return subprocess.CompletedProcess(args, 0, "", "")


def test_the_hotspot_turns_the_radio_on_and_only_announces_a_network_that_opened(tmp_path, monkeypatch):
    monkeypatch.setenv("BERANDA_WIFI_STATUS", str(tmp_path / "status.json"))
    monkeypatch.setattr(wifi_setup, "DNSMASQ_DROPIN", tmp_path / "dropin.conf")
    radios = []
    monkeypatch.setattr(wifi, "radio_on", lambda country="": radios.append(country) or {"ok": True})
    monkeypatch.setattr(wifi_setup, "_country", lambda: "FR")
    monkeypatch.setattr(wifi_setup, "_run", _Nmcli(up_ok=False))
    wifi_setup.start_hotspot()
    assert radios == ["FR"]
    assert not (tmp_path / "status.json").exists()  # no QR code for a network that is not there
    monkeypatch.setattr(wifi_setup, "_run", _Nmcli(up_ok=True))
    wifi_setup.start_hotspot()
    assert json.loads((tmp_path / "status.json").read_text())["ssid"] == AP_SSID


def test_the_image_sets_a_wifi_country():
    assert "WPA_COUNTRY=" in (ROOT / "pi-gen" / "config").read_text()


def test_hotspot_only_ignores_the_loopback_profile(monkeypatch):
    monkeypatch.setattr(wifi_setup, "_run", _Nmcli(active=f"{AP_CON_NAME}\nlo\n"))
    assert wifi_setup._hotspot_only() is True
    monkeypatch.setattr(wifi_setup, "_run", _Nmcli(active=f"{AP_CON_NAME}\nlo\nMaison\n"))
    assert wifi_setup._hotspot_only() is False


def test_a_failed_connect_from_the_setup_page_brings_the_setup_network_back(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("BERANDA_WIFI_STATUS", str(tmp_path / "status.json"))
    fake = _Nmcli()

    def run(args):
        if args[:4] == ["nmcli", "device", "wifi", "connect"]:
            fake.calls.append(list(args))
            return subprocess.CompletedProcess(args, 4, "", "Error: Secrets were required")
        return fake(args)

    monkeypatch.setattr(wifi_setup, "_run", run)
    client = TestClient(wifi_setup.create_portal_app())
    r = client.post("/api/connect", json={"ssid": "Maison", "password": "wrongpass1"}).json()
    assert r["ok"] is False
    assert ["nmcli", "connection", "up", AP_CON_NAME] in fake.calls
    assert ["nmcli", "connection", "delete", "id", "Maison"] in fake.calls  # it was not saved before


def test_the_safety_net_clears_a_leftover_hotspot_when_it_starts(monkeypatch):
    class Stop(Exception):
        pass

    def stop():
        raise Stop

    monkeypatch.setattr(wifi_setup, "stop_hotspot", stop)
    monkeypatch.setattr(wifi_setup, "is_connected", lambda: (_ for _ in ()).throw(RuntimeError("too late")))
    with pytest.raises(Stop):
        wifi_setup.main()
