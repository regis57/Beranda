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
- **v0.16.0**: a Wi-Fi box in the settings page: see the network, keep several, add one (never cuts
  the current one), use one now (goes back by itself if it fails), forget one. The "Beranda setup"
  safety net is on by default and watches all the time: with no known network for 2 minutes the Pi
  opens its own Wi-Fi so a phone can pick the right one; it closes again and retries the known
  networks by itself. Existing installs get it with the Update button
- **v0.16.1**: Wi-Fi fixes from the first real test: a failure now says why (wrong password, not in
  range, radio off, too slow) with the system's own message; a switched-off Wi-Fi radio can be turned
  on from the page (setting the Wi-Fi country from Beranda's country when none is set); browsers no
  longer keep last version's scripts after an update (an empty Wi-Fi box in Edge); the end of an
  update is run by the new version of the root helper, so new steps work at once
- **v0.16.2**: first real Wi-Fi change made from the settings page (Pi 4, cable to Wi-Fi). A request with no
  answer now says whether the Pi is busy (an update) or its helper is stuck, with the command to unblock
  it; Edge users see a gentle tip to use Google Chrome, now the recommended browser everywhere
- **v0.16.3**: the name day is back. The name-day service answers in a shape Beranda did not read, so the
  "Name day" line had never appeared on a real Pi: fixed, against the real answer. With the France theme it
  now shows in big at the top right (where the theme leaves room), in the countries that celebrate name
  days and with their own names; a new option in "Extras of the main screen" turns it off. The languages of
  those countries get their own word for it (Imieniny, Namnsdag, Svátek, Névnap...)
- **v0.16.4**: calmer with a failing source (found with a diagnostic file): "news about my town" (GDELT)
  was asked again every minute, twice, and kept refusing. Now a source that fails is left alone for a
  while (2 to 15 minutes) while its last good copy stays on screen, and two screens asking at once share
  one request. The "offline" badge only shows when the Pi cannot be reached or the weather or calendar
  are old copies; the log names the failing news source
- **v0.16.5**: security housekeeping. The linter's security rules are switched on (they were not),
  and where something looks risky but is deliberate - listening on the home network, naming a command
  rather than writing out its path - the reason is now written next to it. CodeQL reads the Python and
  the JavaScript on every pull request and once a week, Dependabot watches the libraries and the CI
  actions, the CI token can only read, and the root services set their own PATH. A SECURITY.md says how
  to report a problem privately. One real bug found on the way: unpacking a Dropbox folder of photos
  froze the screen and the settings page for as long as it took; it now runs out of the way
- **v0.16.6**: gitleaks joins the checks: it reads every commit ever made, looking for anything shaped
  like a password, a key or a token. GitHub's own scanner only knows the shapes of known providers and
  only looks at new commits. The whole history came back clean
- **v0.16.7**: every action used by CI is now named by the exact commit it is, instead of by a tag
  that its owner could move onto other code. Dependabot keeps them current
- **v0.16.8**: went through everything the new code scanner flagged. One shared check now
  decides whether an address Beranda is given is safe to download from (http or https only,
  a real site name, no hidden password), and calendar links go through it too - they were the
  one kind that was never checked. The Wi-Fi setup page now refuses a network name or a
  password that cannot be right instead of asking the radio to try it. Smaller ones: answer
  files are readable by their owner alone, nothing but the type of a problem is ever written
  to a log, and the few places that really do use a path or an address chosen by the owner now
  say in a sentence why that is safe.
- **v0.16.9**: Beranda now answers the home network only for everything - the screen, its data and the
  photos as much as the settings page - so a port opened on the router by mistake shows strangers
  nothing. Wrong PINs are counted, one phone or computer at a time: after 5, that device waits 1 minute,
  then twice as long each time (up to 1 hour), and the page says how long; the whole house gets at most
  20 wrong PINs in any hour. A PIN with an unusual letter no longer makes the page fail
- **v0.16.10**: on a Raspberry Pi with no screen plugged in (used over SSH only), the diagnostic file and
  `beranda doctor` no longer show the full-screen display service as a fault: it has nothing to do
  there. If the Pi cannot tell, or the service runs anyway, nothing changes
- **v0.17.0**: a first pass for people who see badly or use no mouse. The faint grey texts of the
  screen (air, moon, next events, the town...) are darker in all 15 themes, light and night, so they
  pass the reading-contrast rule; every box and list of the settings page has a name a screen reader
  can say, in the page's language, and so has every part of the screen (57 languages); what changes
  on the screen (weather, agenda, warnings, news) is announced; a clear ring shows where the keyboard
  is; the settings page stops moving for people who asked their system for less motion. Both pages
  are now checked against the accessibility rules (WCAG 2.1 AA) on every change
- **v0.17.1**: a box **Accessibility** on the settings page (16 since 0.17.5): *large text* (everything about 1.4
  times bigger; the 24 h graph and the air row step aside), *high contrast* (black on white by day,
  white on black at night, on top of any style) and *read the day out loud* (a speaker button on the
  screen, and the voice command "read me the day", in the 10 voice languages: the date, the time,
  the weather, today's events and the warnings)
- **v0.17.2**: speak without touching the screen: a **wake word** ("Beranda") in box 11, heard by
  the tablet's own microphone. **Nine more phrases** in the 10 voice languages: the date, today's and
  tomorrow's events, the headlines, bigger / normal text, high contrast / normal colours, be quiet.
  A **printable one-page guide** of everything you can say, in the screen's language, with your own
  phrases (box 11 → *Open the printable guide*; print or save as PDF). And **arrows** to put radio
  favourites and TV channels in the order you want: prime time follows it
- **v0.17.3**: fixes what 0.17.2 broke. A browser allows **one listening at a time**: the wake word
  held the microphone, so the microphone button stopped answering and no phrase worked at all. The
  button now borrows the microphone and gives it back. A failing speech service is left alone
  (the wait doubles, then Beranda says it gave up) instead of being asked again every few seconds.
  When the browser keeps a page nobody has touched silent, the screen now says "touch the screen
  once" instead of saying nothing. The microphone button wears a ring while the wake word is on,
  the settings page says plainly what an always-open microphone costs, and a new check
  (`scripts/check_voice.py`, in CI) makes sure the two listenings never fight again
- **v0.17.4**: three things learnt from a real diagnostic file, where the wake word stopped after
  15 seconds every time with "audio-capture". A microphone taken away *after* it worked is now
  waited for and tried again (it is usually another window, or the system's own voice assistant);
  only right at the start does Beranda conclude there is none. Several Beranda screens in one
  browser no longer fight over the microphone: the newest listens, the others wait and take over
  by themselves. And a browser that answers nothing at all to the microphone button no longer
  keeps the microphone for ever: after 12 seconds it goes back to the wake word. The screen says
  in words when the wake word stops, instead of a code
- **v0.17.5**: the settings page numbered its boxes 15, 17, 16: *Accessibility* is now **16** and
  *Advanced user* **17**, last as it should be. The settings page also says "no microphone found on
  this device" before anybody switches voice control on, instead of a green tick and a failure
  afterwards (a browser lists its microphones without asking permission). And the screen says what
  a microphone problem means - no microphone, blocked, speech service unreachable - rather than the
  browser's own code
- **v0.17.6**: "no microphone was found" was the wrong thing to say to a computer that clearly has
  one. When the browser refuses the microphone but the device lists one, the settings page now
  names the three real reasons - a Bluetooth headset not in "hands-free" mode, Windows refusing
  microphones to desktop programs, another program holding it - and the screen says "the browser
  cannot use the microphone" rather than claiming there is none

- **v0.17.7**: the real reason voice control failed from 0.17.2 on: the little **preview of the
  screen on the settings page** is a full copy of the screen, and it started its own wake word.
  A browser has one microphone, so that hidden copy held it, the real screen fought it, and the
  settings page's microphone test "worked but heard nothing". The preview never listens or speaks
  now. The way pages share the one microphone is rewritten: the first screen keeps it (they no
  longer take it from each other every few seconds), the button or the settings test borrows it
  from any tab and gives it back to the screen that had it, a closed screen lets go at once, and
  a microphone that never started is no longer mistaken for one that "worked first". A check in
  CI now simulates Chrome's single microphone across tabs; it fails on 0.17.6 with exactly the
  message the owner saw
- **v0.18.0**: the always-on **wake word is gone**, on its owner's call after three evenings of
  fighting it: a browser's continuous listening proved too fragile to trust (Chrome ends or
  starves the stream on its own schedule), and it meant a microphone open all day. The microphone
  button does everything: it only listens while a tap asked it to, all the 0.17 phrases still
  work, and the printable guide stays. A wake word saved by an older version is simply ignored.
  Kept from the attempt, because they are good: the 12-second guard on a browser that answers
  nothing, "touch the screen once so Beranda may speak", the plain-words microphone messages, and
  the no-microphone warnings on the settings page. The docs now say in one clear place that **a
  browser only allows the microphone on an https (SSL) page**, and that Beranda's own self-made
  certificate is enough
- **v0.18.1**: the small grey labels of the default theme (the AIR, UV, POLLEN tiles) were a hair too
  light by day - 4.49 to 1 against the 4.5 the accessibility rules ask - and CI only saw it in daytime
  runs, because it checked the screen in whichever mode the clock gave it. The screen is now checked
  by day and by night every time, and a new test reads the three text colours of all 15 themes in both
  modes: two more were just under the line (Oceania by day, America by night). Each of the three is
  one step darker or brighter, invisible to the eye. Also in the wiki: the microphone button
  confirmed on a real Pi 4 with Chrome on Windows, and the Roadmap brought up to date
- **v0.19.0**: a full review of the code against what the README and this wiki promise, 65 problems
  fixed, each with a test that failed before. **Safety**: the root helper no longer runs a file the web
  server's user could change, Wi-Fi answers can no longer be steered through a link, full download
  addresses (calendar links, coordinates) no longer reach the system journal, the settings refuse a page
  from another site pretending to be at Beranda's address, and a PIN Beranda could not check later is
  refused at once. **The screen holds up**: a photo folder Beranda may not open hides the photos instead
  of blanking everything, a mistyped time zone is refused, the agenda keeps its last copy offline on the
  1st of the month, an expired weather warning disappears even when MeteoAlarm cannot be reached, and a
  restart without network keeps the https certificate already accepted. **Right answers**: warnings for
  "Rhône" no longer show "Bouches-du-Rhône"'s, cancelled events are hidden, `webcals://` links work,
  multi-day events stay until they end, rain stays right in imperial units, the Korean clock, TV paging,
  white-night sunrise above 60°, the Indian lunar day, holidays when a region is unknown, standard XMLTV
  guides, radio search by language, Dropbox pictures with the same name. **Voice**: "play the radio"
  with no station, curly apostrophes, a regional language (fr-FR), words inside words, the printable guide
  behind a PIN, and a screen opened with `?lang=` understood in that language. **Settings**: a forced
  `[limits]` profile and a hand-set cache folder survive a save, the voice-phrase limit follows the board.
  **Install**: re-running the install line restarts Beranda, image installs can update, `--no-wifi-setup`
  is respected, and the safety net turns the Wi-Fi radio on and survives a wrong password
