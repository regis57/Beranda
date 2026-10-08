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
    ],
)
def test_invalid_values_are_rejected(bad):
    with pytest.raises((ValueError, KeyError)):
        config.from_dict(bad)


def test_load_reads_toml(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text('country = "JP"\nlanguage = "ja"\n[location]\nname = "Kyoto"\nlatitude = 35.01\nlongitude = 135.77\ntimezone = "Asia/Tokyo"\n')
    cfg = config.load(path)
    assert cfg.location.name == "Kyoto" and cfg.week_start == 6
