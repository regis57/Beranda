# Roadmap

Master word: **ease of installation**. Each step ships as its own PR with a screenshot.

Done:

- **v0.1**: display page, weather, rain, moon, calendar, holidays, ICS calendars
- **v0.2**: settings web page, Indonesian and French themes
- **v0.3**: 13 languages (incl. Arabic right to left), 8 themes, news headlines, step-by-step help

Next:

1. **v0.4**: one-line install script, start at boot (systemd), full screen kiosk (WPE `cog`)
2. Wi-Fi setup without a keyboard (captive portal) and a ready-to-flash image (pi-gen)
3. Settings menu on the Pi itself (raspi-config style)
4. Photo carousel from a local folder (synced with rclone or Syncthing)
5. World radio (Radio Browser)
6. TV prime time from XMLTV files
7. Blink camera thumbnails
8. Voice control (local: openWakeWord + Vosk + Piper; Alexa skill / Matter with limits)
9. Country-specific historical events (Wikidata)
10. More languages: Hausa, Yoruba, Zulu, Somali, Malagasy, Wolof, Haitian Creole, Quechua...

## What we won't do, and why

- **Google Assistant / "OK Google"**: being retired, SDK restricted.
- **Google Photos**: Library API closed to this use; use rclone to a local folder instead.
- **Spotify / Deezer playback**: need a Premium account; optional plugins only.
- **Blink live view**: unofficial API gives thumbnails/clips, not a live stream.
- **Alexa**: custom skill needs a cloud endpoint; limited commands.
- **TV listings**: only reading XMLTV you provide, because of data licensing.
