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
- **v0.13**: TV gets its own "Tonight on TV" box on the screen (one main programme per ticked
  channel, with a plain message when it is empty) and big guides are no longer cut off; the
  radio box gets a "previous station" button; long lists in the settings page can be folded
  away (radio results, TV channels with a search box); voice control gets more built-in phrases
  (next/previous station, volume, tonight's TV), your own phrases from the settings page, and a
  step-by-step guide ([docs/VOICE.md](VOICE.md))
- **v0.13.1**: TV fixes from the second real test: ticking more channels now shows them all (the
  cache ignored the ticked channels), big guides are unpacked as a stream and parsed off the
  main thread, the too-heavy xmltvfr.fr "complete" file is replaced by its TNT and France files,
  the TV box pages through more channels; news shows 3 headlines at once; clock and weather
  are a little smaller; photo and radio share their row 65/35
- **v0.14**: the empty middle of the screen is used: your photo and a 24-hour graph (temperature,
  rain, wind, nights) side by side, with air quality / UV / pollen below; clock and weather sit side by
  side on top. New optional extras (each one can be switched off in the settings page): official
  weather warnings for your area (MeteoAlarm), an ephemeris (name day, length of the day, local
  calendar of the country) and a small second clock. The settings page gets a ☰ menu to jump to a
  section, and "start again from zero" now needs the word yes (oui, ja, sí...) typed in the
  language of the page
- **v0.14.1**: fix - choosing a town in the settings page filled in coordinates the form then
  refused (too many decimals), so the page could not be saved
- **v0.14.2**: fix - choosing a new town in the settings page now also replaces the weather
  warnings area (it kept the old town's) and says that the region was reset
- **v0.14.3**: limits that fit the board. Beranda recognises the Raspberry Pi model and its memory
  (Pi 2, 3, 4, 5; 1 to 16 GB) and caps each list accordingly (calendars, news sources, TV channels,
  radio stations, key dates, photos, voice phrases): the settings page stops you with a plain
  sentence instead of slowing the Pi down, and a hand-edited file is trimmed to fit. The five
  profiles (light, standard, comfortable, comfortable +, maximum) are tabulated in the README and
  can be forced with `[limits] profile` or `BERANDA_PROFILE`. README rewritten around the reader
- **v0.14.4**: a new "Advanced user" box in the settings page: change the port 8080 (checked to
  be free, with every consequence spelled out, the screen on the Pi follows by itself, and Beranda
  falls back to 8080 if the new port cannot be used), and "start over from scratch" moves there.
  A "Buy me a coffee" button sits in the header and the menu. The usage guide lists all 15 boxes

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
