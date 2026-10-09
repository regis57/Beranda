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
- **v0.8**: offline voice control (openWakeWord + Vosk + Piper), a separate opt-in service
  (`install.sh --with-voice`) for the weather, the time, a favourite station and the screen
- **v0.9**: country-specific historical events ("on this day", free lookup on Wikidata),
  woven into the news ticker
- **v0.10**: 9 more languages (Hausa, Yoruba, Zulu, Somali, Malagasy, Wolof, Tamil, Tahitian,
  Quechua), 57 in all
- **v0.11**: Wi-Fi setup with no keyboard (`install.sh --with-wifi-setup`: an open "Beranda
  setup" network and a one-page picker if the Pi boots with no network at all) and a pi-gen
  build definition + CI workflow for a ready-to-flash image with it already built in
- **v0.12**: what the first real test showed was confusing, fixed. Radio and voice now work in
  the page of the tablet that shows Beranda (sound and microphone are the tablet's, not the
  Pi's; `mpv` and the Pi voice service are gone); photos have their own folder, "Add photos"
  and Dropbox; TV prime time is fixed at 20:00 + 3 h and a guide is suggested for the country;
  "On this day" comes from Wikipedia in the user's language; the month grid is gone and the
  agenda looks further ahead

Next:

1. Test on real Raspberry Pi 3B+, 4 and 5 hardware, and tune Chromium for the Pi 3 - also the
   only way to really try v0.11's Wi-Fi setup and build and flash its image
2. Settings menu on the Pi itself (raspi-config style)
3. Blink camera thumbnails

## What we won't do, and why

- **Google Assistant / "OK Google"**: being retired, SDK restricted.
- **Google Photos / Google Drive / iCloud, directly**: no API lets a small home app read them;
  "Add photos" (the phone's picker lists those apps), Dropbox links or rclone to a folder instead.
- **Spotify / Deezer playback**: need a Premium account; optional plugins only.
- **Blink live view**: unofficial API gives thumbnails/clips, not a live stream.
- **Alexa**: custom skill needs a cloud endpoint; limited commands.
- **TV listings**: only reading XMLTV you provide, because of data licensing.
