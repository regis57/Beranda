"""The country table, and that every display language it points to actually has a
translation file with the same shape as English (so the screen never shows a half-translated
page)."""

import json
from pathlib import Path

import pytest

from beranda.providers import countries

I18N_DIR = Path(__file__).resolve().parent.parent / "src" / "beranda" / "web" / "i18n"


def _keyset(d: dict, prefix: str = "") -> set[str]:
    out: set[str] = set()
    for k, v in d.items():
        full = f"{prefix}{k}"
        out |= _keyset(v, f"{full}.") if isinstance(v, dict) else {full}
    return out


@pytest.mark.parametrize("code", countries.LANGUAGES)
def test_every_display_language_has_a_translation_file(code):
    assert (I18N_DIR / f"{code}.json").is_file()


@pytest.mark.parametrize("code", [c for c in countries.LANGUAGES if c != "en"])
def test_every_translation_file_is_valid_json_with_known_keys(code):
    # A language need not translate every string yet (missing ones fall back to English),
    # but it must not have a stray key the app would never look for, or broken JSON.
    english = _keyset(json.loads((I18N_DIR / "en.json").read_text(encoding="utf-8")))
    this = _keyset(json.loads((I18N_DIR / f"{code}.json").read_text(encoding="utf-8")))
    assert this <= english


@pytest.mark.parametrize("code", ["ha", "yo", "zu", "so", "mg", "wo", "ta", "ty", "qu"])
def test_the_nine_new_translations_are_complete(code):
    english = _keyset(json.loads((I18N_DIR / "en.json").read_text(encoding="utf-8")))
    this = _keyset(json.loads((I18N_DIR / f"{code}.json").read_text(encoding="utf-8")))
    assert this == english


@pytest.mark.parametrize(
    ("country", "expected_first"),
    [
        ("NG", "en"), ("NE", "fr"), ("MG", "mg"), ("SN", "fr"), ("SO", "so"), ("ZA", "en"),
        ("IN", "hi"), ("LK", "en"), ("PF", "fr"), ("PE", "es"), ("BO", "es"), ("EC", "es"),
    ],
)
def test_the_new_languages_are_offered_without_changing_the_suggested_one(country, expected_first):
    assert countries.suggested_language(country) == expected_first


def test_every_country_still_resolves_to_at_least_one_known_language():
    for code, langs in countries.COUNTRY_LANGUAGES.items():
        assert langs, code
        for lang in langs:
            assert lang in countries.LANGUAGES, (code, lang)


def test_the_nine_new_languages_are_in_the_table():
    added = {"ha", "yo", "zu", "so", "mg", "wo", "ta", "ty", "qu"}
    assert added <= set(countries.LANGUAGES)
