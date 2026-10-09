# Roadmap

Master word: **ease of installation**. Each step ships as its own PR with a screenshot.

Done:

- **v0.1**: display page, weather, rain, moon, calendar, holidays, ICS calendars
- **v0.2**: settings web page, Indonesian and French themes
- **v0.3**: 13 languages (incl. Arabic right to left), 8 themes, news headlines, step-by-step help
- **v0.4**: one-line installer (start at boot, full screen, update and reboot from the settings
  page, screen rotation and night hours, first-start QR code, `beranda doctor`); 48 languages,
  243 countries, 140 news feeds; 15 themes
- **v0.5**: photo carousel from a local folder, filled with rclone or Syncthing — never a cloud
  photo account of its own
- **v0.6**: world radio (Radio Browser, ~50,000 free stations, played through `mpv` on the Pi
  itself)
- **v0.7**: TV prime time from the user's own XMLTV guide (read-only, never scraped or hosted
  by Beranda)

Next:

1. Wi-Fi setup without a keyboard (captive portal) and a ready-to-flash image (pi-gen), so
   that installing needs no terminal at all
2. Test on real Raspberry Pi 3B+, 4 and 5 hardware, and tune Chromium for the Pi 3
3. Settings menu on the Pi itself (raspi-config style)
4. Blink camera thumbnails
5. Voice control (local: openWakeWord + Vosk + Piper; Alexa skill / Matter with limits)
6. Country-specific historical events (Wikidata)
7. More languages: Hausa, Yoruba, Zulu, Somali, Malagasy, Wolof, Tamil, Tahitian, Quechua...

## What we won't do, and why

- **Google Assistant / "OK Google"**: being retired, SDK restricted.
- **Google Photos**: Library API closed to this use; use rclone to a local folder instead.
- **Spotify / Deezer playback**: need a Premium account; optional plugins only.
- **Blink live view**: unofficial API gives thumbnails/clips, not a live stream.
- **Alexa**: custom skill needs a cloud endpoint; limited commands.
- **TV listings**: only reading XMLTV you provide, because of data licensing.
