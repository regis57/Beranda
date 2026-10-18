# Roadmap

Master word: **ease**. Every step ships as its own small release; what is learned on a real Pi
comes first. Order agreed in October 2026.

## Now

1. **Test on other boards**: Raspberry Pi 3B+ and Pi 5, and tune Chromium for the Pi 3.
2. **First real try of the Wi-Fi safety net** (opening "Beranda setup" with no network at all) and
   of the **ready-to-flash image**. The Wi-Fi box itself was tried on a real Pi 4 in October 2026.
3. Turn the per-board limits from estimates into measurements.

## Next

- **Accessibility, third pass**: a try with a real screen reader. Hands-free voice was tried in
  the browser (a wake word, 0.17.2-0.17.7) and taken out again: a browser's always-on listening
  proved too fragile. If it ever comes back, it will be a microphone on the Pi itself, listening
  locally (openWakeWord + Vosk) - parked for now.

- **Offline voice on the Pi** (Vosk): the page sends the sound to the Pi, which recognises it.
  Works in any browser (Edge, Firefox, Safari), no Google or Microsoft, the voice never leaves home.
  Cost: about 50 MB per language on the SD card, a bit less accurate, one or two seconds on a Pi 4.
- **A settings menu on the Pi itself** (raspi-config style), for when no phone is at hand.
- **Releases page**: versioned downloads and release notes on GitHub.

## Later, ideas

- Blink camera thumbnails.
- A web-only hosted mode (no Raspberry Pi): parked on purpose for now.

## What we won't do, and why

- **Google Assistant / "OK Google"**: being retired, SDK restricted.
- **Google Photos / Google Drive / iCloud, directly**: no API lets a small home app read them;
  "Add photos" (the phone's picker lists those apps), Dropbox links or rclone to a folder instead.
- **Spotify / Deezer playback**: need a Premium account; optional plugins only.
- **Blink live view**: unofficial API gives thumbnails/clips, not a live stream.
- **Alexa**: custom skill needs a cloud endpoint; limited commands.
- **TV listings**: only reading XMLTV you provide, because of data licensing.

## Done

The short story: **0.1-0.4** foundations and the one-line installer · **0.5-0.9** photos, radio, TV,
voice, history · **0.10-0.11** 57 languages, Wi-Fi setup · **0.12-0.13** lessons from the first real
tests · **0.14** the new main screen and limits per board · **0.15** advanced settings, diagnostics,
https, small SD cards · **0.16** Wi-Fi from the settings page, the safety net, home network only ·
**0.17-0.18** voice: a wake word tried and taken out, the microphone button kept. Every version, one line each: [Changelog](Changelog).
