"""Who may talk to Beranda, and how many wrong PINs a device may type.

Two simple rules:

1. **Home network only.** Beranda answers devices on its own home network (addresses such as
   192.168.x.x or 10.x.x.x, and the Pi itself) and nobody else - the screen, the photos and the
   settings page alike. Even if someone opens the port on the router by mistake, a stranger on
   the internet gets "refused" and sees nothing.

2. **Wrong PINs are counted, one device at a time.** A phone or a computer may get the PIN
   wrong 5 times. After that it has to wait 1 minute, and every further wrong PIN doubles the
   wait (2, 4, 8... up to 1 hour). The right PIN wipes the slate clean. Only the device that
   keeps guessing has to wait: the owner's phone is not locked out because a guest's laptop
   guessed. And so that switching devices does not help a guesser either, the whole house
   gets at most 20 wrong PINs in any hour: past that, every device waits until the hour is
   over. People who simply mistype never get anywhere near it.

Typing the same wrong PIN again (a page left open in another tab, a PIN changed on another
phone) counts once, not every time. The counters live in memory: restarting Beranda clears
them, which needs the PIN, or a hand on the Pi.
"""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

FREE_TRIES = 5  # wrong PINs a device may type before it has to wait
FIRST_WAIT = 60  # seconds, after the 5th wrong PIN; then twice as long each time
LONGEST_WAIT = 60 * 60
FORGET_AFTER = 24 * 60 * 60  # a device that stopped guessing a day ago starts fresh
HOUSE_LIMIT = 20  # wrong PINs in any one hour, all devices together; past that, everyone waits
HOUR = 60 * 60
_REMEMBERED_GUESSES = 20  # enough to spot the same wrong PIN typed again


def is_home(host: str | None) -> bool:
    """True for an address on a home network, or the Pi itself."""
    try:
        ip = ipaddress.ip_address(host or "")
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_private or ip.is_loopback or ip.is_link_local


# Endings home routers and the Pi itself give to names on the home network.
_HOME_SUFFIXES = (".local", ".lan", ".home", ".home.arpa", ".internal", ".localdomain", ".fritz.box")


def is_home_name(host_header: str | None) -> bool:
    """True when the page was opened under a home-network name or address (the Host header).

    A web page from another site can have its own name re-pointed at the Pi's address ("DNS
    rebinding"). The browser then sends that site's name as Host and as Origin, so comparing the
    two proves nothing, and the visitor's address is a home one. Only the name gives it away.
    """
    host = (host_header or "").strip().lower()
    if not host:
        return False  # every browser sends one
    if host.startswith("["):  # an IPv6 address, written [fe80::1]:8080
        inside, _, _ = host[1:].partition("]")
        try:
            ipaddress.ip_address(inside)
        except ValueError:
            return False
        return True
    name = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
    name = name.rstrip(".")
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        pass
    if not name:
        return False
    return name == "localhost" or "." not in name or name.endswith(_HOME_SUFFIXES)


@dataclass
class _Device:
    wrong: int = 0
    seen: deque = field(default_factory=lambda: deque(maxlen=_REMEMBERED_GUESSES))
    until: float = 0.0
    last: float = 0.0


class PinAttempts:
    """Counts wrong PINs per device and says how long a device must wait."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._devices: dict[str, _Device] = {}
        self._house: deque[float] = deque()  # when each recent wrong PIN was typed
        self._house_until = 0.0

    def wait_left(self, device: str) -> int:
        """Seconds this device must still wait before a PIN is even looked at (0: go ahead)."""
        now = self._clock()
        entry = self._devices.get(device)
        mine = entry.until - now if entry else 0
        return max(0, round(max(mine, self._house_until - now)))

    def failed(self, device: str, guess: str) -> int:
        """Note a wrong PIN; returns how many seconds this device must now wait."""
        now = self._clock()
        self._forget_old(now)
        entry = self._devices.setdefault(device, _Device())
        # Only a fingerprint of the guess is kept, never the guess itself.
        fingerprint = hashlib.sha256(guess.encode()).hexdigest()
        if fingerprint in entry.seen:
            return self.wait_left(device)  # the same wrong PIN again: it does not count twice
        entry.seen.append(fingerprint)
        entry.wrong += 1
        entry.last = now
        if entry.wrong >= FREE_TRIES:
            wait = min(FIRST_WAIT * 2 ** (entry.wrong - FREE_TRIES), LONGEST_WAIT)
            entry.until = now + wait
            log.warning("%d wrong PINs from %s: that device waits %d min", entry.wrong, device, round(wait / 60))
        self._house.append(now)
        while self._house and self._house[0] <= now - HOUR:
            self._house.popleft()
        if len(self._house) >= HOUSE_LIMIT:
            # Everyone waits until the oldest of these wrong PINs is an hour old. Never more
            # than HOUSE_LIMIT wrong PINs in any hour, however many devices are used.
            until = self._house[0] + HOUR
            if self._house_until <= now:
                log.warning("%d wrong PINs within an hour on the home network: the settings page "
                            "waits %d min for every device", len(self._house), round((until - now) / 60))
            self._house_until = max(self._house_until, until)
        return self.wait_left(device)

    def succeeded(self, device: str) -> None:
        """The right PIN: this device starts from zero again."""
        self._devices.pop(device, None)

    def _forget_old(self, now: float) -> None:
        for device in [d for d, e in self._devices.items() if now - e.last > FORGET_AFTER and e.until <= now]:
            del self._devices[device]
