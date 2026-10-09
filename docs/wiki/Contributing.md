# Contributing

## Set up

```bash
git clone https://github.com/regis57/Beranda.git && cd Beranda
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
beranda --demo            # http://localhost:8080 and /admin
```

## Checks (run before every pull request)

```bash
pytest                    # about 490 tests
ruff check src tests scripts
node --check src/beranda/web/*.js
```

Screenshots: `python scripts/screenshot.py` and `python scripts/screenshot_admin.py` (Playwright).

## How we work

1. A branch per change, one pull request, a **squash merge** with a plain-words title.
2. Bump the version in `pyproject.toml` and `src/beranda/__init__.py`, add a line to [Changelog](Changelog).
   The wiki lives in the code repository, in `docs/wiki/`: edit it there, in the same pull request.
   A workflow publishes it to the GitHub wiki when the change reaches `main`.
3. Words for people come first: every message, hint and doc in plain language ("ease" is the master word).
4. Say honestly what could not be tried on real hardware.

## Common additions

| To add... | Where |
|---|---|
| a display language | one JSON file in `src/beranda/web/i18n/` (same keys as `en.json`) |
| a settings-page language | `src/beranda/web/i18n/admin/` |
| a news feed | `src/beranda/providers/news_catalog.py` (checked weekly by CI) |
| a TV guide | `src/beranda/providers/tv_guides.py` |
| a theme | `providers/seasons.py` + its season module, colours in the CSS, translations |
| a voice phrase | `providers/voice.py` (defaults per language) |

Questions and ideas: [issues](https://github.com/regis57/Beranda/issues). See also [Architecture](Architecture) and [Translations](Translations).
