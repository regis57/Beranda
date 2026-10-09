"""Plays one radio stream at a time, through `mpv`, on the Pi's own speakers or HDMI audio.

The browser never gets an `<audio src>` pointed at a random internet stream: that would
need "connect-src" opened up in the strict Content-Security-Policy (CSP), and decoding
internet radio in a browser tab is heavy for a Pi 3B. Instead the *server* starts `mpv` as
a small subprocess with no video output, and the settings page just tells it which
station to play, like a remote control.
"""

from __future__ import annotations

import shutil
import subprocess

MPV = "mpv"


class RadioPlayer:
    """One station at a time. Not thread-safe beyond FastAPI's single event loop."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._station: dict | None = None
        self._volume: int = 70

    def play(self, station: dict, volume: int | None = None) -> None:
        if not station.get("url"):
            raise ValueError("station has no stream url")
        self.stop()
        if shutil.which(MPV) is None:
            raise RuntimeError("mpv is not installed")
        if volume is not None:
            self._volume = max(0, min(100, volume))
        self._proc = subprocess.Popen(
            [MPV, "--no-video", "--really-quiet", f"--volume={self._volume}", station["url"]],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._station = station

    def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(100, volume))
        if self._station:
            self.play(self._station, self._volume)  # mpv has no live volume IPC here: restart

    def stop(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
        self._station = None

    def status(self) -> dict:
        playing = self._proc is not None and self._proc.poll() is None
        if not playing:
            self._station = None
        return {"playing": playing, "station": self._station, "volume": self._volume}
