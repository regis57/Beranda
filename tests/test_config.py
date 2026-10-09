import pytest

from beranda import config


def test_defaults_work_without_any_file():
    cfg = config.Config()
    assert cfg.country == "FR" and cfg.units == "metric" and cfg.week_start == 0


def test_from_dict_full():
    cfg = config.from_dict(
        {
            "country": "us",
            "language": "EN",
            "location": {"name": "Austin", "latitude": 30.27, "longitude": -97.74, "timezone": "America/Chicago"},
            "calendar": {"ics_urls": ["webcal://example.org/a.ics"]},
            "key_dates": [
                {"date": "03-14", "label": "Pi day", "kind": "other"},
                {"date": "2018-06-02", "label": "Léa", "kind": "birth"},
            ],
        }
    )
    assert cfg.country == "US" and cfg.language == "en"
    assert cfg.units == "imperial"  # inferred from the country
    assert cfg.week_start == 6  # Sunday first in the US
    assert cfg.key_dates[0].year is None and cfg.key_dates[1].year == 2018
    assert cfg.ics_urls == ("webcal://example.org/a.ics",)


@pytest.mark.parametrize(
    "bad",
    [
        {"location": {"latitude": 123, "longitude": 0}},
        {"units": "furlongs"},
        {"mode": "dusk"},
        {"key_dates": [{"date": "13-40", "label": "x"}]},
        {"key_dates": [{"date": "banana", "label": "x"}]},
        {"key_dates": [{"date": "03-14", "label": "x", "kind": "party"}]},
        {"radio": {"stations": [{"uuid": "u1", "name": "x", "url": "not-a-url"}]}},
        {"tv": {"url": "not-a-url"}},
        {"photos": {"dropbox_url": "ftp://x"}},
    ],
)
def test_invalid_values_are_rejected(bad):
    with pytest.raises((ValueError, KeyError)):
        config.from_dict(bad)


def test_radio_defaults_and_round_trip():
    cfg = config.Config()
    assert cfg.radio_stations == () and cfg.radio_volume == 70

    cfg = config.from_dict(
        {
            "radio": {
                "stations": [{"uuid": "u1", "name": " France Musique ", "url": "https://stream/live"}],
                "volume": 150,  # clamped
            }
        }
    )
    assert cfg.radio_stations[0].name == "France Musique"
    assert cfg.radio_volume == 100
    assert config.to_dict(cfg)["radio"]["stations"][0]["uuid"] == "u1"


def test_tv_defaults_and_round_trip():
    cfg = config.Config()
    assert cfg.tv_xmltv_url == "" and cfg.tv_channels == ()

    # Old files still carry prime_start/prime_end: prime time is now fixed (20:00 + 3 h), so they are ignored.
    cfg = config.from_dict(
        {"tv": {"url": "https://example.org/guide.xml", "channels": ["c1", "c2"], "prime_start": "19:30"}}
    )
    assert cfg.tv_xmltv_url == "https://example.org/guide.xml"
    assert cfg.tv_channels == ("c1", "c2")
    assert config.to_dict(cfg)["tv"] == {"url": "https://example.org/guide.xml", "channels": ["c1", "c2"]}


def test_voice_defaults_and_round_trip():
    assert config.Config().voice_enabled is False
    cfg = config.from_dict({"voice": {"enabled": True, "wake_word": "alexa"}})  # old key: ignored
    assert cfg.voice_enabled is True
    assert config.to_dict(cfg)["voice"] == {"enabled": True}


def test_photos_round_trip_with_a_dropbox_link():
    cfg = config.from_dict({"photos": {"dropbox_url": "https://www.dropbox.com/scl/fo/a/b?rlkey=c"}})
    assert cfg.photos_folder == "" and cfg.photos_dropbox_url.startswith("https://www.dropbox.com/")
    assert config.to_dict(cfg)["photos"]["dropbox_url"] == cfg.photos_dropbox_url


def test_history_defaults_and_round_trip():
    cfg = config.Config()
    assert cfg.history_enabled is True

    cfg = config.from_dict({"history": {"enabled": False}})
    assert cfg.history_enabled is False
    assert config.to_dict(cfg)["history"] == {"enabled": False}


def test_load_reads_toml(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text('country = "JP"\nlanguage = "ja"\n[location]\nname = "Kyoto"\nlatitude = 35.01\nlongitude = 135.77\ntimezone = "Asia/Tokyo"\n')
    cfg = config.load(path)
    assert cfg.location.name == "Kyoto" and cfg.week_start == 6


def test_a_config_path_that_does_not_exist_yet_gives_the_defaults(tmp_path, monkeypatch):
    from beranda import config as cfgmod

    monkeypatch.setenv("BERANDA_CONFIG", str(tmp_path / "not-yet.toml"))
    assert cfgmod.load().location.name == "Metz"
