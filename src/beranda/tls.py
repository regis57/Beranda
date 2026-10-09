"""An optional secure (HTTPS) address, so a computer's browser allows the microphone.

Browsers only give the microphone to "secure" pages: https://, or localhost. Beranda's usual
address, http://beranda.local:8080, is neither. When this is switched on in the settings page
("Advanced user"), Beranda also answers on https://beranda.local:8443 with a certificate it made
itself. Because no official authority signed it, the browser warns once ("your connection is
not private"): the person clicks "Advanced" then "Continue". Nothing leaves the home network.

The usual http address keeps working exactly as before (the screen on the Pi uses it).
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

log = logging.getLogger(__name__)

VALID_DAYS = 825  # the longest lifetime browsers are happy with
RENEW_AFTER_DAYS = 700  # made again a little before it runs out


class TlsError(Exception):
    """The certificate could not be made; the message is a short code for the settings page."""


def openssl_available() -> bool:
    return shutil.which("openssl") is not None


def lan_ip() -> str | None:
    """The address of this device on the home network (no packet is sent to find it out)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))
            ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None


def certificate_names() -> tuple[list[str], list[str]]:
    """The names and numeric addresses the certificate must be valid for."""
    host = socket.gethostname().strip()
    dns = ["localhost"]
    if host and host != "localhost":
        dns += [host, f"{host}.local"]
    dns.append("beranda.local")
    ips = ["127.0.0.1"]
    ip = lan_ip()
    if ip:
        ips.append(ip)
    return list(dict.fromkeys(dns)), list(dict.fromkeys(ips))


def ensure_certificate(folder: Path) -> tuple[Path, Path]:
    """The (certificate, key) files in `folder`, made now if missing, out of date, or if the
    name or address of this device changed since. Raises TlsError("no_openssl" | "failed")."""
    cert, key, stamp = folder / "cert.pem", folder / "key.pem", folder / "names.txt"
    dns, ips = certificate_names()
    wanted = "\n".join([*dns, *ips])
    try:
        fresh = (
            cert.is_file() and key.is_file() and stamp.read_text() == wanted
            and time.time() - cert.stat().st_mtime < RENEW_AFTER_DAYS * 86400
        )
    except OSError:
        fresh = False
    if fresh:
        return cert, key
    if not openssl_available():
        raise TlsError("no_openssl")
    san = ",".join([*(f"DNS:{d}" for d in dns), *(f"IP:{i}" for i in ips)])
    try:
        folder.mkdir(parents=True, exist_ok=True)
        os.chmod(folder, 0o700)
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256",
             "-days", str(VALID_DAYS), "-subj", "/CN=Beranda", "-addext", f"subjectAltName={san}",
             "-keyout", str(key), "-out", str(cert)],
            check=True, capture_output=True, timeout=120,
        )
        os.chmod(key, 0o600)
        stamp.write_text(wanted)
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("could not make the HTTPS certificate (%s)", type(exc).__name__)
        raise TlsError("failed") from exc
    return cert, key


def valid_ip(text: str) -> bool:
    try:
        ipaddress.ip_address(text)
    except ValueError:
        return False
    return True


_server = None  # the second server, while it runs
_thread: threading.Thread | None = None


def is_running() -> bool:
    return bool(_server is not None and getattr(_server, "started", False))


def start(app, host: str, port: int, folder: Path) -> bool:
    """Start answering on the secure port in a background thread (same app, same rules).
    Returns False, and Beranda carries on with plain http only, if that cannot be done."""
    global _server, _thread
    import uvicorn

    try:
        cert, key = ensure_certificate(folder)
    except TlsError as exc:
        log.error("HTTPS is switched on but unavailable (%s); carrying on with http only", exc)
        return False
    config = uvicorn.Config(
        app, host=host, port=port, ssl_certfile=str(cert), ssl_keyfile=str(key),
        lifespan="off",  # the first server already runs the app's start-up work
        log_level="warning",
    )
    _server = uvicorn.Server(config)
    _thread = threading.Thread(target=lambda: asyncio.run(_server.serve()), name="beranda-https", daemon=True)
    _thread.start()
    return True


def stop() -> None:
    if _server is not None:
        _server.should_exit = True
    if _thread is not None:
        _thread.join(3)
