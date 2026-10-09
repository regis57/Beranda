# Status

**Beranda 0.15.10 - alpha.** Used every day by the author on a Raspberry Pi 4 (2 GB).
"Alpha" means: it works and is used, but only a few boards and browsers have been tried for real.

## What works, and how we know

| Area | State | How it was checked |
|---|---|---|
| Display: clock, weather, 24 h graph, agenda, news, photos, radio, TV, "on this day" | ✅ works | real Pi 4, daily use |
| 15 themes, 57 display languages (incl. right to left) | ✅ works | automated screenshots of every theme |
| Settings page (15 boxes, 9 languages) | ✅ works | real Pi 4 + automated browser tests |
| One-line installer, update button, `beranda doctor` | ✅ works | real Pi 4 + a fresh Ubuntu machine in CI |
| Port change, https on the same port | ✅ works | real Pi 4 (October 2026) |
| Diagnostic file | ✅ works | real Pi 4 |
| Voice control | ✅ Google Chrome · ❌ Microsoft Edge | real PC: Edge's speech service answers "network" |
| Air quality, UV, pollen | ✅ works | real Pi 4 (pollen: Europe, in season only) |
| Weather warnings (MeteoAlarm) | ⚠️ works, area names differ by country | France only; the settings page now spots an area that does not match the town |
| Limits per board (Pi 2 to Pi 5) | ⚠️ estimates | only the Pi 4 2 GB was measured |
| Raspberry Pi 3B+, Pi 5, Pi 2, Zero 2 W | ❓ untested | help welcome |
| Wi-Fi setup with no keyboard, ready-to-flash image | ❓ built, never tried on a real Pi | |

## Known issues

- **Voice on Microsoft Edge** does not work (the browser's own speech service fails). Use Google Chrome.
- **Weather warnings**: the area must be written as MeteoAlarm writes it in your country; use the *Test* button.
- **8 GB SD cards** are tight: since 0.15.9 every update keeps them tidy, 16 GB is more comfortable.
- **Self-made certificate**: the first visit to `https://` shows a "not private" warning, once per browser.

Found something else? [Open an issue](https://github.com/regis57/Beranda/issues) and attach the diagnostic
file (settings page → *Advanced user*).

## Quality

489 automated tests and a linter run on every change; the installer is tested on a fresh Ubuntu
machine in GitHub Actions, and every news feed of the catalogue is checked weekly. Every change goes through a pull request.
