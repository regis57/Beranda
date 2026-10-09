# Data sources & privacy

Your settings stay on the Pi. Beranda talks only to the services you use:

| Service | When | What it receives | Licence / terms |
|---|---|---|---|
| [Open-Meteo](https://open-meteo.com) | weather every 15 min, air every hour | coordinates | CC BY 4.0 (air: Copernicus CAMS) |
| Open-Meteo geocoding | when you search a town | the typed name | CC BY 4.0 |
| Your calendar provider | every 15 min | nothing but the request to your private link | yours |
| News feeds you chose | every 30 min | nothing | titles belong to their publishers |
| [GDELT](https://www.gdeltproject.org) | "news about my town" | the town name | free |
| [MeteoAlarm](https://meteoalarm.org) | warnings on, every 15 min | the country | EUMETNET |
| [nameday.abalin.net](https://nameday.abalin.net) | ephemeris on | the date and country | free |
| [Wikipedia](https://www.wikipedia.org) | "on this day", once a day | the date and language | CC BY-SA |
| [Radio Browser](https://www.radio-browser.info) | search, playing a station | the search words | free |
| Your TV guide | every 3 h | nothing | read only, never re-published |
| GitHub | *Check for updates* | nothing | |
| Browser speech service | voice, in the screen's browser | the sound (Google for Chrome) | the browser maker's |

Public holidays, sun, moon and seasons are computed on the Pi.

## What the settings page protects

- Opens from the home network only; optional PIN. **Never forward the port to the internet.**
- Calendar links and the PIN live in `config.toml` (readable by Beranda only) and never reach a log.

## The diagnostic file contains / does not contain

Contains: version, board, memory, temperature, free space, services, your settings **without secrets**,
what the display shows, recent log lines, the browser, what the screens reported.
Does not contain: passwords, calendar links, Dropbox link, feed addresses, PIN, full web addresses,
your exact position (rounded to about 10 km). You download it and decide who gets it.
