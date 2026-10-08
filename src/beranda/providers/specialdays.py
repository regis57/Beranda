"""Days worth marking on the calendar: public holidays of the chosen country, plus the
personal key dates (births, deaths, anniversaries...) from the config."""

from __future__ import annotations

import logging
from datetime import date

import holidays

from ..config import Config

log = logging.getLogger(__name__)


def public_holidays(country: str, subdivision: str | None, language: str, years: list[int]):
    """Return {date: name}. Unknown countries yield an empty dict rather than an error."""
    try:
        return holidays.country_holidays(
            country, subdiv=subdivision, years=years, language=language
        )
    except NotImplementedError:
        log.warning("no public holiday data for country %r", country)
        return {}
    except (KeyError, ValueError):
        # language or subdivision not supported for this country: retry with defaults
        try:
            return holidays.country_holidays(country, years=years)
        except (NotImplementedError, KeyError, ValueError):
            return {}


def _key_date_label(key, year: int) -> str:
    if key.year and year > key.year and key.kind in {"birth", "anniversary", "death"}:
        return f"{key.label} ({year - key.year})"
    return key.label


def special_days(cfg: Config, start: date, end: date) -> list[dict]:
    """All special days with start <= date <= end, sorted by date."""
    years = sorted({start.year, end.year})
    found: list[dict] = []

    for day, name in sorted(public_holidays(cfg.country, cfg.subdivision, cfg.language, years).items()):
        if start <= day <= end:
            found.append({"date": day.isoformat(), "kind": "holiday", "label": str(name)})

    for year in years:
        for key in cfg.key_dates:
            try:
                day = date(year, key.month, key.day)
            except ValueError:  # Feb 29 in a non-leap year
                continue
            if start <= day <= end:
                found.append(
                    {"date": day.isoformat(), "kind": key.kind, "label": _key_date_label(key, year)}
                )

    return sorted(found, key=lambda d: (d["date"], d["kind"] != "holiday"))
