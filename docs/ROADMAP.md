# Roadmap

Master word: **ease of installation**. Each step ships as its own PR with a screenshot.

1. **v0.1** – display page, weather, moon, calendar, holidays, ICS (done)
2. Settings web page, Indonesian and French themes (v0.2, done)
2b. Config menu on the Pi itself (raspi-config style)
3. One-line install script, systemd service, kiosk mode (WPE `cog`)
4. Wi-Fi captive portal and ready-to-flash image (pi-gen)
5. Photo carousel from a local folder (sync with rclone/Syncthing)
6. World radio (Radio Browser)
7. TV prime-time from XMLTV files
8. Blink camera thumbnails
9. Voice control (local: openWakeWord + Vosk + Piper; Alexa skill / Matter with limits)
10. Country-specific historical events (Wikidata)

## What we won't do, and why

- **Google Assistant / "OK Google"**: being retired, SDK restricted.
- **Google Photos**: Library API closed to this use; use rclone to a local folder instead.
- **Spotify / Deezer playback**: need a Premium account; optional plugins only.
- **Blink live view**: unofficial API gives thumbnails/clips, not a live stream.
- **Alexa**: custom skill needs a cloud endpoint; limited commands.
- **TV listings**: only reading XMLTV you provide, because of data licensing.
