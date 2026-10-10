"""Wi-Fi from the settings page (wifi.py), with a fake nmcli: no radio is needed."""

import json
import os
import subprocess
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from beranda import wifi
from beranda.app import create_app
from beranda.config import Config
from beranda.wifi_setup import AP_CON_NAME, Network


class FakeNmcli:
    """Answers nmcli like a Pi on "Maison" (signal 72), knowing "Maison" and "Bureau"."""

    def __init__(self, ethernet=False, up_ok=True):
        self.calls: list[list[str]] = []
        self.ethernet = ethernet
        self.up_ok = up_ok
        self.profiles = {"Maison": "Maison", "Bureau": "Bureau"}

    def __call__(self, args, timeout=30):
        self.calls.append(args)
        out, code = "", 0
        if args[:5] == ["nmcli", "-t", "-f", "NAME,TYPE", "connection"]:
            out = "\n".join([f"{n}:802-11-wireless" for n in self.profiles] + ["Wired:802-3-ethernet", f"{AP_CON_NAME}:802-11-wireless"])
        elif args[:3] == ["nmcli", "-g", "802-11-wireless.ssid"]:
            out = self.profiles.get(args[-1], "")
        elif args[:4] == ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION"]:
            out = "wlan0:wifi:connected:Maison\n" + ("eth0:ethernet:connected:Wired\n" if self.ethernet else "eth0:ethernet:unavailable:\n")
        elif args[:4] == ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL"]:
            out = "no:Voisin:40\nyes:Maison:72\n"
        elif args[:4] == ["nmcli", "-t", "-f", "IP4.ADDRESS"]:
            out = "IP4.ADDRESS[1]:192.168.1.223/24\n"
        elif args[:2] == ["systemctl", "is-enabled"]:
            out = "enabled\n"
        elif "up" in args and "connection" in args:
            code = 0 if (self.up_ok or args[-1] == "Maison") else 4
        return subprocess.CompletedProcess(args, code, out, "")


@pytest.fixture
def fake(monkeypatch):
    nm = FakeNmcli()
    monkeypatch.setattr(wifi, "_run", nm)
    return nm


def test_names_and_passwords_are_checked():
    assert wifi.check_ssid("Maison") == "Maison"
    for bad in ("", "x" * 33, "a\nb", None, 5):
        with pytest.raises(wifi.WifiError, match="bad_name"):
            wifi.check_ssid(bad)
    assert wifi.check_password("") == "" and wifi.check_password("12345678") == "12345678"
    assert wifi.check_password("a" * 64) == "a" * 64  # 64 hex digits is a raw key
    for bad in ("short", "x" * 64, "pass\nword", 12345678):
        with pytest.raises(wifi.WifiError, match="bad_password"):
            wifi.check_password(bad)


def test_status_tells_the_network_its_strength_the_address_and_the_safety_net(fake):
    s = wifi.status()
    assert s["connection"] == "Maison" and s["ssid"] == "Maison" and s["signal"] == 72
    assert s["address"] == "192.168.1.223" and s["ethernet"] is False and s["safety_net"] is True
    assert [n["name"] for n in s["saved"]] == ["Maison", "Bureau"]  # never the setup network


def test_adding_a_network_never_disconnects_and_remembers_it_for_good(fake):
    assert wifi.add("Grand-mère", "motdepasse1") == {"ok": True, "name": "Grand-mère", "updated": False}
    command = fake.calls[-1]
    assert command[:4] == ["nmcli", "connection", "add", "type"] and "connection.autoconnect" in command
    assert "up" not in command  # only remembered, nothing switches
    assert wifi.add("Bureau", "nouveaumotdepasse")["updated"] is True  # a known one gets its new password
    assert fake.calls[-1][:3] == ["nmcli", "connection", "modify"]
    with pytest.raises(wifi.WifiError):
        wifi.add("Beranda setup", "")


def test_the_network_in_use_cannot_be_forgotten_without_a_cable(fake, monkeypatch):
    with pytest.raises(wifi.WifiError, match="in_use"):
        wifi.forget("Maison")
    assert wifi.forget("Bureau")["ok"]
    cabled = FakeNmcli(ethernet=True)
    monkeypatch.setattr(wifi, "_run", cabled)
    assert wifi.forget("Maison")["ok"]
    with pytest.raises(wifi.WifiError, match="unknown_network"):
        wifi.forget("Inconnu")


def test_switching_goes_back_by_itself_when_the_new_network_fails(monkeypatch):
    failing = FakeNmcli(up_ok=False)
    monkeypatch.setattr(wifi, "_run", failing)
    r = wifi.switch("Bureau")
    assert r == {"ok": False, "name": "Bureau", "error": "switch_failed", "back_to": "Maison"}
    assert failing.calls[-1][-1] == "Maison"  # the last thing done: back to the network that worked
    working = FakeNmcli()
    monkeypatch.setattr(wifi, "_run", working)
    assert wifi.switch("Bureau") == {"ok": True, "name": "Bureau"}


def test_a_scan_marks_the_networks_already_known(fake, monkeypatch):
    monkeypatch.setattr(wifi, "scan", lambda: [Network("Maison", 72, True), Network("Café", 30, False)])
    nets = wifi.networks_around()["networks"]
    assert nets[0]["saved"] is True and nets[1] == {"ssid": "Café", "signal": 30, "secured": False, "saved": False}


def test_a_job_file_is_deleted_at_once_and_the_answer_never_holds_the_password(fake, tmp_path, monkeypatch):
    monkeypatch.setenv("BERANDA_WIFI_JOBS", str(tmp_path / "answers"))
    request = tmp_path / "wifi-0123456789ab.json"
    request.write_text(json.dumps({"op": "add", "ssid": "Grand-mère", "password": "secretpass"}))
    assert wifi.job_main([str(request)]) == 0
    assert not request.exists()
    answer = (tmp_path / "answers" / "0123456789ab.json").read_text()
    assert json.loads(answer)["ok"] and json.loads(answer)["done"] and "secretpass" not in answer
    bad = tmp_path / "wifi-0123456789ac.json"
    bad.write_text(json.dumps({"op": "rm -rf /"}))
    wifi.job_main([str(bad)])
    assert json.loads((tmp_path / "answers" / "0123456789ac.json").read_text())["error"] == "unknown_op"


def _client(tmp_path, monkeypatch, installed=True):
    if installed:
        (tmp_path / "requests").mkdir()
        monkeypatch.setenv("BERANDA_REQUESTS", str(tmp_path / "requests"))
    else:
        monkeypatch.delenv("BERANDA_REQUESTS", raising=False)
    monkeypatch.setenv("BERANDA_WIFI_JOBS", str(tmp_path / "answers"))
    cfg = replace(Config(), cache_dir=tmp_path / "c", news_enabled=False, history_enabled=False)
    return TestClient(create_app(cfg, config_path=tmp_path / "config.toml"), client=("192.168.1.20", 5000))


def test_the_settings_page_drops_a_private_job_and_reads_the_answer(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    r = client.post("/api/admin/wifi/add", json={"ssid": "Grand-mère", "password": "secretpass"})
    job = r.json()["job"]
    path = tmp_path / "requests" / f"wifi-{job}.json"
    assert json.loads(path.read_text()) == {"op": "add", "ssid": "Grand-mère", "password": "secretpass", "hidden": False}
    assert oct(os.stat(path).st_mode)[-3:] == "600"
    assert client.get(f"/api/admin/wifi-job/{job}").json() == {"done": False}
    (tmp_path / "answers").mkdir()
    (tmp_path / "answers" / f"{job}.json").write_text('{"done": true, "ok": true}')
    assert client.get(f"/api/admin/wifi-job/{job}").json()["ok"] is True


def test_the_settings_page_checks_before_asking_root(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    assert client.post("/api/admin/wifi/add", json={"ssid": "x", "password": "short"}).json()["detail"] == "wifi_bad_password"
    assert client.post("/api/admin/wifi/switch", json={"name": "Bureau"}).status_code == 400  # must be confirmed
    assert client.post("/api/admin/wifi/reboot", json={}).status_code == 404
    assert client.get("/api/admin/wifi-job/../../etc").status_code == 404
    assert not list((tmp_path / "requests").iterdir())


def test_without_the_installer_the_page_says_so(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, installed=False)
    r = client.post("/api/admin/wifi/status", json={})
    assert r.status_code == 409 and r.json()["detail"] == "wifi_not_installed"


def test_the_safety_net_waits_longer_once_a_wifi_is_known(monkeypatch):
    from beranda import wifi_setup

    known = "Maison:802-11-wireless\nWired:802-3-ethernet\n"
    monkeypatch.setattr(wifi_setup, "_run", lambda args: subprocess.CompletedProcess(args, 0, known, ""))
    assert wifi_setup.knows_a_wifi() and wifi_setup.grace_seconds() == 120 and wifi_setup.open_seconds() == 300
    first = f"{AP_CON_NAME}:802-11-wireless\n"
    monkeypatch.setattr(wifi_setup, "_run", lambda args: subprocess.CompletedProcess(args, 0, first, ""))
    assert not wifi_setup.knows_a_wifi() and wifi_setup.grace_seconds() == 45 and wifi_setup.open_seconds() == 900
    assert wifi_setup._hotspot_only() is False  # (the fake lists the setup network with its type)
    monkeypatch.setattr(wifi_setup, "_run", lambda args: subprocess.CompletedProcess(args, 0, f"{AP_CON_NAME}\n", ""))
    assert wifi_setup._hotspot_only() is True  # "connected" only to itself: not a real connection


def test_the_installer_accepts_saying_no_to_the_safety_net():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    out = subprocess.run(["bash", str(root / "install.sh"), "--dry-run", "--no-wifi-setup"],
                         capture_output=True, text=True, check=True).stdout
    assert "beranda-wifi-setup" not in out
