# API reference

All JSON. `/api/admin/*` answers the home network only, needs the PIN (header `X-Beranda-Pin`) when one is
set, and refuses cross-site writes.

## Display (open on the home network)

| Route | Use |
|---|---|
| `GET /api/state` | everything the display shows, in one object (`?theme=` previews a theme) |
| `GET /api/health` | `{status, version}` |
| `GET /api/screen` | screen on/off and rotation, read by the kiosk every 30 s |
| `GET /api/photos/{name}` | one picture of the photo frame |
| `GET /api/setup-qr.svg`, `/api/setup-wifi-qr.svg` | first-start QR codes |
| `POST /api/voice` | `{text}` heard by the browser → `{reply, action}` |
| `POST /api/report` | `{event}`: a short line from the screen (microphone, page error) for the diagnostic file |

## Settings (`/api/admin`)

| Route | Use |
|---|---|
| `GET /status` | is a PIN needed |
| `GET /config`, `PUT /config` | read / save the settings (422 with a plain sentence if invalid or over the limits) |
| `GET /geocode?q=` | town search |
| `POST /test-ics`, `/test-feed`, `/test-tv`, `/test-alerts` | try a calendar, a feed, a TV guide, a warnings area |
| `GET /news-auto` | what *Choose for me* would pick |
| `GET /tv-guides?country=` | free guides that answer for a country |
| `GET /radio-search` | Radio Browser search |
| `GET /photos`, `POST /photos?name=`, `DELETE /photos/{name}`, `POST /photos-sync`, `GET /photos-count` | photo frame |
| `GET /voice-commands` | built-in phrases for a language |
| `GET /system`, `GET /system/latest` | version, board, port, https, updates |
| `POST /system/port` | `{port, confirmed}` change the port, restart |
| `POST /system/{update,restart-screen,reboot,reset}` | ask the root service; `reset` needs `{confirmed}`, erasing data also `{erase_data, confirmed_twice}` |
| `POST /diagnostics` | `{client}` → the diagnostic text file |
