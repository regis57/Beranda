# Changelog

One line per version, newest last. Each one was a pull request on
[GitHub](https://github.com/regis57/Beranda/pulls?q=is%3Apr+is%3Amerged).

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
  step-by-step guide ([docs/VOICE.md](https://github.com/regis57/Beranda/blob/main/docs/VOICE.md))
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
- **v0.14.5**: "Start over and erase photos and data" next to "Start over from scratch": it also
  deletes the photos of Beranda's own photo frame and everything downloaded, and asks twice (the typed
  word, then a last reminder listing what will go)
- **v0.15.0**: three fixes and two tools. The warnings area is emptied when the town is changed by hand
  (name, coordinates or country); ticked TV channels keep their usual names instead of showing guide
  numbers; and in "Advanced user": an optional secure address (HTTPS, a certificate made by Beranda) so
  a computer's browser allows the microphone, and a diagnostic file to download for bug reports (no secret inside)
- **v0.15.1**: the two "start over" buttons say plainly what they erase; after starting over with a
  changed port, the settings page follows Beranda back to 8080 by itself; `beranda doctor` says when
  it needs sudo to read the settings and finds the server on another port; the installer shows the real port
- **v0.15.2**: the secure address is now simply the usual one with an "s": the same port answers
  http:// and https:// (no switch, no second port). The README gets a "settings page does not answer"
  rescue section with the few commands that always work
- **v0.15.3**: "Test the microphone on this device" in the Voice control box says in plain words what
  blocks it (blocked permission, no microphone, speech service unreachable...); the screen's message
  adds a short reason code
- **v0.15.4**: a warnings area saved for another town is spotted when the settings page opens
  ("does not match your town"), with a one-tap fix (found thanks to the diagnostic file)
- **v0.15.5**: the screen reports what goes wrong on its side (microphone result, page errors) and the
  diagnostic file shows it, with the browser of that screen
- **v0.15.6**: Google Chrome recommended for voice; the settings page warns Edge users that its speech
  service often fails ("network")
- **v0.15.7**: tidier on small SD cards: the installer and each update drop the downloaded packages,
  the pip cache and the old versions' files, and keep the system log under 50 MB; `beranda doctor`
  shows the free space
- **v0.15.8**: `beranda-tidy`, run by the installer and every update: package and pip caches, old
  versions, a 50 MB system log, and on cards under 32 GB with rpi-swap, swap in compressed memory
  only (the swap file as big as the memory goes away at the next reboot; a hand-made choice is kept)
- **v0.15.9**: the wiki (roadmap, status, changelog, user guide, developer documentation) lives in
  `docs/wiki/` and is published automatically; the automatic checks pass again (a newer linter and
  a shell-script warning had turned them red since 0.14.0); fix - a first install on a new card
  stopped with an error at its very last step since 0.15.1 (updates were not affected)
- **v0.15.10**: wiki links fixed (they broke inside tables); the READMEs link to the wiki pages
