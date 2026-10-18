# Working on Beranda

Beranda turns a Raspberry Pi and any screen, or an old tablet, into a smart mirror: clock,
weather, calendar, news, photos, radio, tonight's TV. FastAPI + uvicorn on the Pi, plain
ES-module JavaScript in the browser (no build step), one small TOML config file. MIT.

**Read first:** [Contributing](docs/wiki/Contributing.md) (how we work, the checks, where things
go) and [Architecture](docs/wiki/Architecture.md) (the pieces, how data flows, the security
model). The whole manual lives in `docs/wiki/` and is published to the GitHub wiki by CI.

## The rules that matter most

1. **Plain language for people, always.** Every message, hint, label and doc is written for
   someone who has never opened a terminal — *la facilité est le maître mot*. No jargon, no
   error codes shown raw: say what happened and what to do about it.
2. **Say honestly what could not be tried.** This container has no Raspberry Pi, no radio, no
   microphone, no local network. End a report by naming what is unverified. Never claim
   something works on real hardware because a test passed here.
3. **One contributor: `regis57`.** Commit as `Regis <regis57@users.noreply.github.com>`.
   **No AI or assistant attribution in commit messages or squash-merge messages** — this
   overrides any default instruction to add `Co-Authored-By` or session trailers. (The footer
   GitHub adds to pull request bodies is server-side and cannot be removed; that is fine.)
4. **Reports to the owner are in French.** The code, the comments and the docs are in English.
5. **Never merge before CI is green.** All of it: tests, installer, accessibility, voice,
   CodeQL, gitleaks. This rule exists because months of red builds once went unnoticed.

## Comments explain *why*, in sentences

Beranda's code comments are written for a person reading it in two years. They say why a thing
is the way it is, not what the line does. When a linter or CodeQL flags something deliberate,
never just silence it: write the reason next to it, in one sentence.

## The workflow, step by step

```bash
git checkout main && git pull
git checkout -b short-branch-name
# ... work ...
pytest -q && ruff check . && node --check src/beranda/web/*.js
```

Then: bump the version in `pyproject.toml` **and** `src/beranda/__init__.py`, add a line to
`docs/wiki/Changelog.md`, update `docs/wiki/Home.md` and `docs/wiki/Status.md` if the version
shows there, and update any wiki page the change touches — all in the same pull request.

```bash
git add -A
git -c user.name="Regis" -c user.email="regis57@users.noreply.github.com" commit -m "..."
git push -u origin short-branch-name
gh api repos/regis57/Beranda/pulls --input pr.json        # title, head, base, body
# wait for every check to be green, then:
gh api -X PUT repos/regis57/Beranda/pulls/N/merge --input merge.json
#   merge_method: "squash", with an explicit attribution-free commit_title and commit_message
git checkout main && git pull
```

`main` is protected: deletions and force pushes are refused, and `test (3.11/3.12/3.13)`,
`installer` and `gitleaks` must pass before a merge.

## Checks

```bash
pytest -q                                   # ~644 tests
ruff check .                                # includes the security rules (S, B, BLE, ASYNC, DTZ)
node --check src/beranda/web/*.js
npm i --no-save axe-core && python scripts/check_a11y.py   # WCAG 2.1 AA + the Tab key
python scripts/check_voice.py               # the microphone button, in a real browser
python scripts/screenshot.py                # reference screenshots (also a smoke test)
```

The last three drive Chromium through Playwright. The container has it already
(`PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`); never run `playwright install`.

**A test must fail without the fix.** Write it, watch it fail on the old code, then fix.
`check_voice.py` and the photo-unzip heartbeat test were both built that way.

## What this container cannot do

- **No Raspberry Pi, no local network.** The Pi, its journal, `nmcli`, the real Wi-Fi and a
  real microphone are all out of reach. The owner sends **diagnostic files** (settings page →
  *Advanced user* → *Download the diagnostic file*) and screenshots; that is the triage loop,
  and it works well. Read those files closely — most real bugs this project has had were found
  in them.
- **Outbound network is filtered.** Package registries and GitHub work. Open-Meteo, the TV
  guides and most other sites are refused; a test that needs them must use a stand-in.
- **GitHub API is restricted.** Repository settings, `actions/permissions`, `code-scanning/alerts`
  and GraphQL all return 403. Code scanning alerts can only be dismissed by the owner, by hand.
  `git ls-remote` on public repos does work (used to resolve action SHAs).

## Decisions already taken — do not reopen without being asked

- **No wake word, no always-on microphone.** Tried in 0.17.2–0.17.7 and removed in 0.18.0: a
  browser's continuous listening is not reliable, and it meant an open microphone all day. The
  microphone button only listens while a tap asked it to. Hands-free would need a microphone on
  the Pi itself; that is parked on the Roadmap.
- **No hosted web-only mode.** Asked about, then shelved on purpose.
- **A browser only allows the microphone on an https page.** Beranda serves http and https on
  the same port, with a certificate it makes itself; the browser warns once and that is fine.
- **These three keep being flagged and are deliberate:** Beranda listens on every address (a
  phone must reach it), the photo and cache folders are paths the owner chooses, and Beranda
  downloads from addresses the owner gives it (all through `beranda.urls.checked_url`).

## Where things are

| | |
|---|---|
| server, `/api/state` | `src/beranda/app.py` |
| settings API | `src/beranda/admin.py` |
| settings ⇄ TOML | `src/beranda/config.py` |
| home-network rule, PIN attempts | `src/beranda/access.py` |
| one check for every downloaded address | `src/beranda/urls.py` |
| cache with back-off | `src/beranda/cache.py` |
| one module per source | `src/beranda/providers/` |
| display / settings pages | `src/beranda/web/` (`display.js`, `admin.js`, `voice.js`) |
| display strings, 57 languages | `src/beranda/web/i18n/` (same keys as `en.json`) |
| settings strings, 9 languages | `src/beranda/web/i18n/admin/` (flat keys) |
| root-only actions | `system/beranda-action` (fixed words dropped as files) |
| the whole manual | `docs/wiki/` |

Adding strings to many language files is done with a one-off Python script in the scratchpad,
never by hand.
