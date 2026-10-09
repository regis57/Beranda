"""A secure (https) address on the SAME port, so a browser allows the microphone.

Browsers only give the microphone to "secure" pages: https://, or localhost. So Beranda answers
both ways on its one port: http://rp4.local:8080 as always, and https://rp4.local:8080 (same
address, with an "s"). It looks at the first byte each visitor sends: a secure connection
always starts with byte 0x16, plain http never does.

The certificate is made by Beranda itself (with the openssl tool). No official authority signed
it, so the browser warns once ("your connection is not private"): choose "Advanced", then
"Continue". Nothing leaves the home network.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import shutil
import socket
import subprocess
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



def ssl_context(folder: Path):
    """The TLS settings for the secure address, or None when no certificate can be made."""
    import ssl

    try:
        cert, key = ensure_certificate(folder)
    except TlsError as exc:
        log.warning("secure address unavailable (%s): http only", exc)
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(cert), str(key))
    return ctx


_available = False


def available() -> bool:
    """True when this server also answers https on its port."""
    return _available


class _Listener:
    """Accepts visitors on the port and gives each one plain http or https, by its first byte."""

    def __init__(self, sock: socket.socket, make_protocol, ctx) -> None:
        self.sock = sock
        self.make_protocol = make_protocol
        self.ctx = ctx
        self.loop = asyncio.get_running_loop()
        self.task = self.loop.create_task(self._accept())

    async def _accept(self) -> None:
        while True:
            try:
                conn, _addr = await self.loop.sock_accept(self.sock)
            except asyncio.CancelledError:
                raise
            except OSError:
                await asyncio.sleep(0.05)
                continue
            self.loop.create_task(self._serve(conn))

    async def _first_byte(self, conn: socket.socket) -> bytes:
        ready = self.loop.create_future()
        self.loop.add_reader(conn.fileno(), lambda: ready.done() or ready.set_result(None))
        try:
            await asyncio.wait_for(ready, timeout=30)  # browsers open spare connections and wait
        finally:
            self.loop.remove_reader(conn.fileno())
        return conn.recv(1, socket.MSG_PEEK)

    async def _serve(self, conn: socket.socket) -> None:
        conn.setblocking(False)
        try:
            first = await self._first_byte(conn)
            if not first:
                conn.close()
                return
            secure = first == b"\x16" and self.ctx is not None
            await self.loop.connect_accepted_socket(self.make_protocol, conn, ssl=self.ctx if secure else None)
        except (TimeoutError, OSError, ConnectionError):
            conn.close()
        except Exception:
            log.debug("connection dropped", exc_info=True)
            conn.close()

    def close(self) -> None:
        self.task.cancel()
        self.sock.close()

    async def wait_closed(self) -> None:
        return None


def make_server(config, cert_folder: Path):
    """A uvicorn server that answers http AND https on the same port (see the top of this file).
    If anything about it fails, it quietly behaves like a plain uvicorn server (http only)."""
    import sys

    import uvicorn

    class DualServer(uvicorn.Server):
        async def startup(self, sockets=None) -> None:
            global _available
            try:
                make = self.config.http_protocol_class  # uvicorn's own protocol, as in its startup()
            except AttributeError:
                return await super().startup(sockets)
            ctx = await asyncio.to_thread(ssl_context, cert_folder)
            if ctx is None:
                return await super().startup(sockets)
            await self.lifespan.startup()
            if self.lifespan.should_exit:
                sys.exit(3)
            config = self.config

            def protocol():
                return make(config=config, server_state=self.server_state, app_state=self.lifespan.state)

            try:
                sock = socket.create_server((config.host, config.port), backlog=config.backlog)
            except OSError as exc:
                log.error("cannot listen on port %s: %s", config.port, exc)
                await self.lifespan.shutdown()
                sys.exit(3)
            sock.setblocking(False)
            self.servers = [_Listener(sock, protocol, ctx)]
            _available = True
            log.info("Beranda answers on port %s, with http:// and https://", config.port)
            self.started = True

    return DualServer(config)
