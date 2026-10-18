"""World radio: Radio Browser (radio-browser.info), a free, keyless directory of ~50,000
stations maintained by volunteers. No account, no clicks counted against the user.

Radio Browser runs on several independent, mirrored servers so that no single one is a
point of failure; a client is expected to try more than one. We keep a short, fixed list
of well-known mirrors and move to the next one if a request fails.
"""

from __future__ import annotations

import httpx

USER_AGENT = "Beranda/0.5 (+https://github.com/regis57/Beranda)"
MIRRORS = (
    "https://de1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info",
    "https://at1.api.radio-browser.info",
)
MAX_RESULTS = 30


# Radio Browser stores a station's language as English names ("french,other") and its search
# matches the given text anywhere inside them, so sending Beranda's short code ("de", "es")
# finds the wrong stations or none. Keyed by the base code, so "pt-BR" and "zh-TW" work too.
LANGUAGE_NAMES = {
    "af": "afrikaans", "am": "amharic", "ar": "arabic", "bg": "bulgarian", "bn": "bengali",
    "ca": "catalan", "cs": "czech", "da": "danish", "de": "german", "el": "greek",
    "en": "english", "es": "spanish", "et": "estonian", "fa": "persian", "fi": "finnish",
    "fr": "french", "ha": "hausa", "he": "hebrew", "hi": "hindi", "hr": "croatian",
    "ht": "haitian", "hu": "hungarian", "id": "indonesian", "it": "italian", "ja": "japanese",
    "ko": "korean", "lt": "lithuanian", "lv": "latvian", "mg": "malagasy", "ms": "malay",
    "nb": "norwegian", "nl": "dutch", "pl": "polish", "pt": "portuguese", "qu": "quechua",
    "ro": "romanian", "ru": "russian", "sk": "slovak", "sl": "slovenian", "so": "somali",
    "sr": "serbian", "sv": "swedish", "sw": "swahili", "ta": "tamil", "th": "thai",
    "tl": "tagalog", "tr": "turkish", "ty": "tahitian", "uk": "ukrainian", "ur": "urdu",
    "vi": "vietnamese", "wo": "wolof", "yo": "yoruba", "zh": "chinese", "zu": "zulu",
}  # fmt: skip


def _language_name(code: str) -> str:
    """Radio Browser's name for a display code; a full name typed by hand passes through."""
    base = code.strip().lower().split("-")[0]
    if base in LANGUAGE_NAMES:
        return LANGUAGE_NAMES[base]
    # An unknown two- or three-letter code would only match other languages' names by accident.
    return base if len(base) > 3 else ""


def _stream_url(raw: dict) -> str:
    """The station's address, preferring https.

    A screen opened with https:// (needed for the microphone) cannot play an http:// stream:
    the browser upgrades it to https and gives up when the station does not answer there.
    Radio Browser keeps two addresses, and when only one of them is https we take that one.
    """
    resolved, given = raw.get("url_resolved") or "", raw.get("url") or ""
    for candidate in (resolved, given):
        if candidate.startswith("https://"):
            return candidate
    return resolved or given


def _station(raw: dict) -> dict:
    url = _stream_url(raw)
    return {
        "uuid": raw.get("stationuuid", ""),
        "name": raw.get("name", "").strip() or "?",
        "url": url,
        # Lets the settings page warn that an http-only station stays silent on an https screen.
        "https": url.startswith("https://"),
        "favicon": raw.get("favicon", ""),
        "country": raw.get("countrycode", ""),
        "language": (raw.get("language", "") or "").split(",")[0].strip(),
        "tags": [t for t in (raw.get("tags", "") or "").split(",") if t][:3],
    }


async def search(
    *, country: str = "", language: str = "", name: str = "", tag: str = "", limit: int = MAX_RESULTS
) -> list[dict]:
    """Stations matching any of the given filters, most popular first."""
    params = {
        "limit": min(limit, MAX_RESULTS),
        "hidebroken": "true",
        "order": "clickcount",
        "reverse": "true",
    }
    if country:
        params["countrycode"] = country.upper()
    if language and (language_name := _language_name(language)):
        params["language"] = language_name
    if name:
        params["name"] = name
    if tag:
        params["tag"] = tag

    last_error: Exception | None = None
    for mirror in MIRRORS:
        try:
            async with httpx.AsyncClient(timeout=8, headers={"User-Agent": USER_AGENT}) as client:
                r = await client.get(f"{mirror}/json/stations/search", params=params)
                r.raise_for_status()
                return [_station(s) for s in r.json()]
        except httpx.HTTPError as exc:
            last_error = exc
            continue
    raise last_error or RuntimeError("no radio mirror reachable")
