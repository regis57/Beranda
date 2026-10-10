# Architecture

Beranda is one small Python web server and two web pages. No build step, no database, no cloud.

```
            phone / computer                      HDMI screen or tablet
        ┌────────────────────┐               ┌──────────────────────────┐
        │  /admin (settings) │               │  /  (display page)       │
        │  admin.js          │               │  display.js, radio, voice│
        └─────────┬──────────┘               └────────────┬─────────────┘
                  │ /api/admin/*                          │ /api/state every 60 s
                  ▼                                       ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  beranda (FastAPI + uvicorn, user "beranda", never root)     │
        │  one port: http:// and https:// (first byte decides)         │
        │  config.toml ─ Config ─ build_state ─ Cache (memory + disk)  │
        │  providers/: weather, air, alerts, calendar, news, tv, ...   │
        └───────┬───────────────────────────────────────┬──────────────┘
                │ drops a file in requests/             │ HTTPS to public services
                ▼                                       ▼
        beranda-actions (root, fixed words only)  Open-Meteo, MeteoAlarm, feeds, ...
        update · restart-screen · reboot · reset
        + wifi-<id>.json jobs → beranda-wifi-job (checked, deleted at once)

        beranda-wifi-setup (root): the safety net, opens "Beranda setup" when no network
```

## Pieces

| Piece | Where | Role |
|---|---|---|
| Server | `src/beranda/app.py` | routes, `build_state` (everything the display needs, in one JSON) |
| Settings API | `src/beranda/admin.py` | `/api/admin/*`, guarded |
| Settings | `src/beranda/config.py` | `config.toml` ⇄ frozen `Config`; validated, trimmed to the limits |
| Cache | `src/beranda/cache.py` | each provider call: fresh data, or the last good copy marked stale |
| Providers | `src/beranda/providers/` | one module per source or calendar (weather, ICS, news, TV, seasons...) |
| Limits | `src/beranda/limits.py` | board + memory → profile → maximum per list |
| Secure address | `src/beranda/tls.py` | self-made certificate (openssl), http and https on one port |
| Diagnostics | `src/beranda/diagnostics.py` | the diagnostic file, recent log lines, screen reports |
| Wi-Fi | `src/beranda/wifi.py`, `wifi_setup.py` | Wi-Fi jobs run by the root helper (nmcli); the always-on safety net and its setup page |
| System | `src/beranda/system.py`, `system/` | screen hours, requests to the root service, installer units, kiosk script, `beranda-tidy` |
| Pages | `src/beranda/web/` | plain ES modules, CSS, translations in `i18n/` |

## How data flows

- The display page asks `/api/state` every 60 seconds. The server builds it from the settings and the
  providers, each behind the cache: weather and calendars 15 min, news 30 min, air 1 h, TV 3 h,
  "on this day" 20 h. With no network, the last good copy is shown and flagged stale.
- The settings page reads `/api/admin/config`, writes it back with `PUT`; the display follows on its next poll.
- Radio and voice run in the display page itself (the tablet's speakers and microphone).

## Security model

- The settings API answers the **home network only**, can ask a **PIN**, and refuses cross-site writes.
- The server never runs as root. Root actions are fixed words dropped as files for `beranda-actions`;
  Wi-Fi jobs are small JSON files (mode 0600) that the root runner checks strictly and deletes at once
  (they may hold a password); answers never contain a password.
- A strict Content-Security-Policy: the pages load only their own files.
- Secrets (calendar links, PIN) stay in `config.toml` (mode 0600) and never reach a log or the diagnostic file.
