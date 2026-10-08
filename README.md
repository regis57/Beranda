# Beranda

*Beranda* means "veranda" in Indonesian: a calm place to see the day at a glance.

A dashboard for a smart mirror or an old tablet, made for a **Raspberry Pi 3B+ or newer**:
clock, local weather and rain, moon, your calendar, holidays and dates that matter, and a line
of news headlines. Light by day, dark at night. Free: no account, no subscription, no paid API.

> **Status: alpha (v0.3).** Everything below works in a browser. It has not been tested on a
> real Raspberry Pi yet, and the one-line installer is the next step (see the roadmap).
> 🇫🇷 [Lire en français](README.fr.md)

| | |
|---|---|
| ![Japan](docs/screenshots/v0.3.0-japan-light.png) | ![Brazil](docs/screenshots/v0.3.0-brazil-light.png) |
| ![Germany, night](docs/screenshots/v0.3.0-germany-night.png) | ![Arabic, right to left](docs/screenshots/v0.3.0-arabic-light.png) |

*Screenshots use demo data: weather, agenda and headlines are invented; moon, sun, seasons and
public holidays are real.* [All screenshots](docs/screenshots/)

## What you get

- **Clock and date** in your language.
- **Weather**: now, rain in the next two hours, seven-day forecast (Open-Meteo, free).
- **Moon and sun**: moon phase, sunrise and sunset, all calculated on the Pi.
- **Calendar**: your Google, Apple, Outlook, Nextcloud or Proton calendar (read-only), the
  public holidays of your country, and your own dates (births, remembrances, anniversaries).
- **News**: one line of headlines at the bottom. News about your town, your country's media,
  an international medium in your language, or any RSS feed you like.
- **Eight themes**, each with its own way of telling the season: Japan (72 micro-seasons),
  Indonesia (Javanese mangsa), France (Republican calendar), Germany (seasons of nature),
  Spain, Italy and Portugal (proverb of the month), Brazil (saying of the day, southern seasons).
- **13 languages**: English, French, German, Spanish, Italian, Portuguese, Brazilian Portuguese,
  Japanese, Indonesian, Arabic (right to left), Swahili, Amharic, Afrikaans.
  [Coverage for Latin America and Africa](docs/COUNTRIES.md).
- **A settings page** for your phone, in plain words, with step-by-step help.

## Try it on your computer (2 minutes)

You need Python 3.11 or newer.

```bash
git clone https://github.com/regis57/Beranda.git
cd Beranda
python3 -m venv .venv && . .venv/bin/activate
pip install .
beranda --demo
```

Open <http://localhost:8080> for the display and <http://localhost:8080/admin> for the settings.
Stop it with Ctrl+C. Without `--demo` you get real weather and your own calendar.

## Install on a Raspberry Pi (manual, for now)

1. **Prepare the card.** With [Raspberry Pi Imager](https://www.raspberrypi.com/software/),
   choose *Raspberry Pi OS Lite (64-bit)*. In the Imager settings, give the Pi a name
   (for example `beranda`), your Wi-Fi, and a user name and password.
   [Official guide](https://www.raspberrypi.com/documentation/computers/getting-started.html).
2. **Connect to it** from your computer: `ssh your-user@beranda.local`.
   [Official guide](https://www.raspberrypi.com/documentation/computers/remote-access.html).
3. **Install Beranda**:
   ```bash
   sudo apt update && sudo apt install -y git python3-venv fonts-noto-core fonts-noto-cjk
   git clone https://github.com/regis57/Beranda.git && cd Beranda
   python3 -m venv .venv && . .venv/bin/activate && pip install .
   beranda
   ```
4. **Set it up from your phone**: open `http://beranda.local:8080/admin` (same Wi-Fi as the Pi)
   and follow the three steps at the top of the page.

Starting by itself at boot and showing full screen (kiosk) come with the installer (v0.4).

## Connect your calendar

Beranda reads your calendar through a private **link** (an "iCal" or "ICS" address). It only
reads: it never changes anything, and it never asks for your password. Paste the link in
*Settings → 4. Your calendar* and press **Test**.

| Calendar | Where to find the link | Official guide |
|---|---|---|
| **Google Calendar** | On a computer: ⚙ → Settings → click your calendar on the left → *Integrate calendar* → copy *Secret address in iCal format*. | [Google help](https://support.google.com/calendar/answer/37648) |
| **Apple iCloud** | On icloud.com/calendar: ⓘ next to the calendar → turn on *Public Calendar* → *Copy*. | [Apple help](https://support.apple.com/guide/icloud/share-a-calendar-mm6b1a9479/icloud) |
| **Outlook / Microsoft 365** | Outlook on the web: ⚙ Settings → Calendar → Shared calendars → *Publish a calendar* → choose it → *Publish* → copy the **ICS** link. | [Microsoft help](https://support.microsoft.com/en-us/outlook/share-your-calendar-in-outlook-com) |
| **Nextcloud** | Calendar app: calendar menu → *Share link* → copy. Beranda turns the share link into the feed by itself. | [Nextcloud manual](https://docs.nextcloud.com/server/stable/user_manual/en/groupware/calendar.html#publishing-a-calendar) |
| **Proton Calendar** | Paid plans: Settings → Calendars → your calendar → *Share with anyone* → *Create link* → *Copy link*. | [Proton help](https://proton.me/support/share-calendar-via-link) |

**Keep the link private**: anyone who has it can see your events. Beranda stores it only on the
Pi, in a file only you can read. If it leaks, make a new one from the same page (the old one
stops working). Links starting with `webcal://` work too.

## News headlines

One line at the bottom shows the latest headlines, one at a time, with the name of the medium.
Titles only: no pictures, no ads, no tracking, no account.

- **"Choose for me"** (default): news mentioning your town (found by [GDELT](https://www.gdeltproject.org/),
  a free open index of the world's press), two media of your country, and an international
  medium in your language.
- **Choose yourself** among about 70 free feeds: public broadcasters and major newspapers of
  Europe, the Americas, Africa and Asia, and international services (BBC, DW, France 24, RFI,
  UN News, Al Jazeera...).
- **Add any feed**: most news sites publish an RSS link (look for the orange RSS logo, or try the
  site address followed by `/rss` or `/feed`). Paste it and press **Test**.

Every feed of the catalog is checked automatically every week.

## Privacy and security

- The settings page only opens from your home network, and can ask for a PIN.
- Your settings stay on the Pi. The Pi talks only to the services you use: Open-Meteo (weather),
  your calendar, the news feeds you chose, and GDELT if "news about my town" is on (it then
  sends the name of your town).
- Do not open the Pi's port 8080 to the internet on your router.

## For contributors

`pip install -e ".[dev]"`, then `pytest` and `ruff check src tests scripts`.
Screenshots: `python scripts/screenshot.py` and `python scripts/screenshot_admin.py`.
A new language is one JSON file in `src/beranda/web/i18n/` (and optionally `i18n/admin/`).
See [docs/ROADMAP.md](docs/ROADMAP.md).

## Credits

Weather data by [Open-Meteo](https://open-meteo.com/) (CC BY 4.0). Town news by
[GDELT](https://www.gdeltproject.org/). Public holidays by the
[holidays](https://github.com/vacanza/holidays) library. Headlines belong to their publishers.

## Licence

MIT.
