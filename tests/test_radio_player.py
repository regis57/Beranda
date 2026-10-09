from beranda.providers.radio_player import RadioPlayer

STATION = {"uuid": "abc", "name": "Test FM", "url": "http://stream.example/live"}


class FakeProcess:
    """Stands in for subprocess.Popen without spawning a real mpv."""

    def __init__(self, argv, **kw):
        self.argv = argv
        self.alive = True

    def poll(self):
        return None if self.alive else 0

    def terminate(self):
        self.alive = False

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.alive = False


def test_nothing_playing_by_default():
    player = RadioPlayer()
    assert player.status() == {"playing": False, "station": None, "volume": 70}


def test_play_requires_mpv_to_be_installed(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    player = RadioPlayer()
    try:
        player.play(STATION)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "mpv" in str(exc)


def test_play_rejects_a_station_with_no_url():
    player = RadioPlayer()
    try:
        player.play({"name": "Nothing"})
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_play_stop_and_status(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/mpv")
    monkeypatch.setattr("subprocess.Popen", FakeProcess)
    player = RadioPlayer()

    player.play(STATION, volume=55)
    assert player.status() == {"playing": True, "station": STATION, "volume": 55}

    player.stop()
    assert player.status() == {"playing": False, "station": None, "volume": 55}


def test_playing_a_new_station_stops_the_previous_one(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/mpv")
    monkeypatch.setattr("subprocess.Popen", FakeProcess)
    player = RadioPlayer()
    player.play(STATION)
    first = player._proc
    player.play({"uuid": "xyz", "name": "Other", "url": "http://stream.example/other"})
    assert first.alive is False
    assert player.status()["station"]["uuid"] == "xyz"


def test_set_volume_restarts_playback_at_the_new_volume(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/mpv")
    monkeypatch.setattr("subprocess.Popen", FakeProcess)
    player = RadioPlayer()
    player.play(STATION, volume=40)
    player.set_volume(90)
    assert player.status()["volume"] == 90
    assert player.status()["playing"] is True
