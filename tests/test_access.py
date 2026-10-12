"""Home network only, and wrong PINs counted one device at a time."""

from dataclasses import replace

from fastapi.testclient import TestClient

from beranda import access
from beranda.access import FIRST_WAIT, FREE_TRIES, HOUR, HOUSE_LIMIT, LONGEST_WAIT, PinAttempts
from beranda.app import create_app
from beranda.config import Config

PIN = "246810"
PHONE = ("192.168.1.20", 5000)
GUEST = ("192.168.1.66", 5000)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


# ---------------------------------------------------------------- the counter on its own ---
def test_five_wrong_pins_then_a_minute_then_twice_as_long_each_time():
    clock = Clock()
    pins = PinAttempts(clock)
    for n in range(1, FREE_TRIES):
        assert pins.failed("guest", f"000{n}") == 0  # the first 4 cost nothing
    assert pins.failed("guest", "0005") == FIRST_WAIT
    clock.now += FIRST_WAIT
    assert pins.wait_left("guest") == 0
    assert pins.failed("guest", "0006") == 2 * FIRST_WAIT
    clock.now += 2 * FIRST_WAIT
    assert pins.failed("guest", "0007") == 4 * FIRST_WAIT


def test_the_wait_never_goes_beyond_an_hour():
    clock = Clock()
    pins = PinAttempts(clock)
    for n in range(40):
        clock.now += LONGEST_WAIT
        wait = pins.failed("guest", f"{n:04}")
    assert wait == LONGEST_WAIT


def test_the_same_wrong_pin_typed_again_counts_once():
    """A tab left open with an old PIN, or the PIN changed on another phone."""
    pins = PinAttempts(Clock())
    for _ in range(20):
        pins.failed("phone", "1234")
    assert pins.wait_left("phone") == 0


def test_the_right_pin_wipes_the_slate_clean():
    pins = PinAttempts(Clock())
    for n in range(FREE_TRIES - 1):
        pins.failed("phone", f"{n:04}")
    pins.succeeded("phone")
    for n in range(FREE_TRIES - 1):
        assert pins.failed("phone", f"9{n:03}") == 0


def test_only_the_device_that_guesses_waits():
    pins = PinAttempts(Clock())
    for n in range(FREE_TRIES):
        pins.failed("guest", f"{n:04}")
    assert pins.wait_left("guest") > 0
    assert pins.wait_left("phone") == 0


def test_switching_devices_to_guess_faster_pauses_the_whole_house():
    clock = Clock()
    pins = PinAttempts(clock)
    first = clock.now
    for n in range(HOUSE_LIMIT):  # one or two guesses each from many addresses
        pins.failed(f"10.0.0.{n // 2}", f"{n:04}")
        clock.now += 30
    # everyone, even a device never seen before, waits until the first guess is an hour old
    assert pins.wait_left("phone-never-seen-before") == round(first + HOUR - clock.now)
    clock.now = first + HOUR
    assert pins.wait_left("phone-never-seen-before") == 0


def test_never_more_than_the_house_limit_in_any_hour():
    """A guesser with endless addresses, trying as soon as allowed, for a whole day."""
    clock = Clock()
    pins = PinAttempts(clock)
    start, guesses, n = clock.now, 0, 0
    while clock.now < start + 24 * HOUR:
        n += 1
        device = f"10.0.{n // 250}.{n % 250}"  # always a fresh address
        wait = pins.wait_left(device)
        if wait:
            clock.now += wait
            continue
        pins.failed(device, f"{n:06}")
        guesses += 1
    assert guesses <= HOUSE_LIMIT * 25


def test_a_device_that_stopped_guessing_a_day_ago_starts_fresh():
    clock = Clock()
    pins = PinAttempts(clock)
    for n in range(FREE_TRIES - 1):
        pins.failed("guest", f"{n:04}")
    clock.now += 25 * 3600
    for n in range(FREE_TRIES - 1):
        assert pins.failed("guest", f"9{n:03}") == 0


def test_home_addresses():
    assert access.is_home("192.168.1.20") and access.is_home("10.42.0.7") and access.is_home("127.0.0.1")
    assert access.is_home("::ffff:192.168.0.5") and access.is_home("fe80::1")
    assert not access.is_home("8.8.8.8") and not access.is_home("2a01:e0a::1")
    assert not access.is_home("") and not access.is_home(None) and not access.is_home("testclient")


# ---------------------------------------------------------------- through the server ---
def _app(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path / "cache", admin_pin=PIN, news_enabled=False, history_enabled=False)
    return create_app(cfg, config_path=tmp_path / "config.toml")


def test_after_five_wrong_pins_even_the_right_one_has_to_wait(tmp_path):
    app = _app(tmp_path)
    guest, phone = TestClient(app, client=GUEST), TestClient(app, client=PHONE)
    for n in range(FREE_TRIES - 1):
        assert guest.get("/api/admin/config", headers={"X-Beranda-Pin": f"11{n}"}).status_code == 401
    # the 5th wrong PIN already says "wait", rather than "wrong" and a surprise at the next try
    assert guest.get("/api/admin/config", headers={"X-Beranda-Pin": "999"}).status_code == 429
    refused = guest.get("/api/admin/config", headers={"X-Beranda-Pin": PIN})
    assert refused.status_code == 429  # not even looked at
    assert 0 < int(refused.headers["Retry-After"]) <= FIRST_WAIT
    assert guest.get("/api/admin/status").json()["wait"] > 0  # the page can say how long
    # the owner's phone is not locked out because the guest guessed
    assert phone.get("/api/admin/config", headers={"X-Beranda-Pin": PIN}).status_code == 200
    assert phone.get("/api/admin/status").json() == {"pin_required": True, "wait": 0}


def test_no_pin_at_all_is_not_a_guess(tmp_path):
    phone = TestClient(_app(tmp_path), client=PHONE)
    for _ in range(3 * FREE_TRIES):
        assert phone.get("/api/admin/config").status_code == 401
    assert phone.get("/api/admin/config", headers={"X-Beranda-Pin": PIN}).status_code == 200


def test_an_unusual_letter_in_the_pin_is_a_wrong_pin_not_a_crash(tmp_path):
    phone = TestClient(_app(tmp_path), client=PHONE)
    assert phone.get("/api/admin/config", headers={"X-Beranda-Pin": "café".encode("latin-1")}).status_code == 401


def test_strangers_see_nothing_at_all(tmp_path):
    stranger = TestClient(_app(tmp_path), client=("8.8.8.8", 5000))
    for path in ("/", "/api/state", "/api/photos/x.jpg", "/api/screen", "/api/setup-qr.svg"):
        answer = stranger.get(path)
        assert answer.status_code == 403 and "home network" in answer.text, path
    assert stranger.post("/api/voice", json={"text": "weather"}).status_code == 403
