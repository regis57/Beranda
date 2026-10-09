"""The Wi-Fi setup helper: parsing `nmcli` output, building its commands, and the tiny captive
portal page - all without a real Wi-Fi radio, by stubbing subprocess.run."""

import json
import subprocess

from fastapi.testclient import TestClient

from beranda import wifi_setup
from beranda.wifi_setup import AP_SSID, Network, connect, create_portal_app, is_connected, scan


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _stub(mapping):
    """Return a fake subprocess.run that answers by matching the first words of the command."""

    def run(args, **kwargs):
        for prefix, result in mapping.items():
            if tuple(args[: len(prefix)]) == prefix:
                return result
        return _Result(returncode=1, stderr="unexpected command: " + " ".join(args))

    return run


def test_is_connected_reads_the_general_state(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _stub({("nmcli", "-t", "-f", "STATE"): _Result(stdout="connected\n")}))
    assert is_connected() is True

    monkeypatch.setattr(subprocess, "run", _stub({("nmcli", "-t", "-f", "STATE"): _Result(stdout="disconnected\n")}))
    assert is_connected() is False


def test_scan_parses_signal_strength_and_drops_duplicates_and_the_setup_network(monkeypatch):
    out = (
        "Home Wifi:70:WPA2\n"
        "Home Wifi:95:WPA2\n"  # same network seen on another channel, stronger - keep this one
        "Open Cafe:40:\n"
        "\\:tricky\\:name:10:WPA2\n"  # nmcli escapes ':' inside a field as '\:'
        f"{AP_SSID}:99:--\n"  # never offer joining our own setup network
        ":5:--\n"  # hidden network: no name to show
    )
    monkeypatch.setattr(
        subprocess, "run", _stub({("nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY"): _Result(stdout=out)})
    )
    networks = scan()
    assert networks[0] == Network(ssid="Home Wifi", signal=95, secured=True)
    assert Network(ssid="Open Cafe", signal=40, secured=False) in networks
    assert Network(ssid=":tricky:name", signal=10, secured=True) in networks
    assert all(n.ssid != AP_SSID for n in networks)
    assert len(networks) == 3  # one row per real network, strongest signal first


def test_connect_reports_success_without_ever_touching_the_password(monkeypatch):
    seen = {}

    def run(args, **kwargs):
        seen["args"] = args
        return _Result(returncode=0)

    monkeypatch.setattr(subprocess, "run", run)
    ok, message = connect("Home Wifi", "super-secret")
    assert ok is True and message == "connected"
    assert "super-secret" in seen["args"]  # the real nmcli call does need it...
    assert "super-secret" not in str((ok, message))  # ...but it never comes back out


def test_connect_reports_the_failure_reason(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        lambda args, **kw: _Result(returncode=1, stderr="Error: Secrets were required, but not provided.\n"),
    )
    ok, message = connect("Home Wifi", "wrong")
    assert ok is False and "Secrets" in message


def test_connect_with_no_network_name_fails_fast(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("should not run nmcli")))
    ok, _message = connect("", "")
    assert ok is False


def test_status_file_round_trips_through_the_environment_variable(tmp_path, monkeypatch):
    status_path = tmp_path / "wifi-setup.json"
    monkeypatch.setenv(wifi_setup.STATUS_FILE_ENV, str(status_path))
    wifi_setup.write_status(AP_SSID)
    assert json.loads(status_path.read_text()) == {"ssid": AP_SSID, "open": True}

    wifi_setup.write_status(None)
    assert not status_path.exists()


def test_portal_page_is_served_and_lists_scanned_networks(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        _stub({("nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY"): _Result(stdout="Home Wifi:80:WPA2\n")}),
    )
    client = TestClient(create_portal_app())
    page = client.get("/")
    assert page.status_code == 200 and "Connect Beranda" in page.text

    networks = client.get("/api/networks").json()["networks"]
    assert networks == [{"ssid": "Home Wifi", "signal": 80, "secured": True}]


def test_portal_connect_endpoint_calls_nmcli_and_reports_back(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _Result(returncode=0))
    client = TestClient(create_portal_app())
    result = client.post("/api/connect", json={"ssid": "Home Wifi", "password": "x"}).json()
    assert result == {"ok": True, "message": "connected"}


def test_captive_portal_probe_urls_redirect_to_the_setup_page():
    client = TestClient(create_portal_app())
    for path in ("/generate_204", "/gen_204", "/hotspot-detect.html", "/connecttest.txt", "/ncsi.txt", "/anything"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code in (302, 307) and response.headers["location"] == "/"
