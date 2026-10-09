# Settings, box by box

Open `http://beranda.local:8080/admin` from a phone or computer on the same Wi-Fi. A ☰ menu jumps
to any box; each box has a **Need help?** link. Press **Save**: the screen follows within a minute.

| Box | What it does | Worth knowing |
|---|---|---|
| **1. Where are you?** | Town, position, time zone | Picking a town also resets the region and the warnings area |
| **2. Country and language** | Public holidays, first day of the week, news suggestions, screen language | A region only matters for regional holidays |
| **3. Look** | 15 themes, live preview; *Auto* follows the sun | Each theme tells the season its own way |
| **4. Extras of the main screen** | 24 h graph, air/UV/pollen, weather warnings, ephemeris, second clock | Each can be switched off; the page warns if the warnings area belongs to another town |
| **5. Your calendar** | Private iCal/ICS links (Google, Apple, Outlook, Nextcloud, Proton), *Test* | Read only; keep the link secret |
| **6. Dates that matter** | Births, anniversaries; `2018-06-02` shows the years, `06-02` repeats | |
| **7. News headlines** | *Choose for me*, 140 free feeds, your own RSS | Titles only, no tracking |
| **8. Photo frame** | *Add photos*, or follow a shared Dropbox folder | Limited by the board, see below |
| **9. World radio** | Search 50,000 stations, keep favourites | Plays on the screen's speakers |
| **10. TV tonight** | Pick a free guide for your country, tick channels | Channel names are kept with the settings |
| **11. Voice control** | Microphone button, your own phrases, *Test the microphone* | Google Chrome only, see [Voice control](Voice-control) |
| **12. Screen** | Rotation, night hours | On a Pi the HDMI turns off; on a tablet the page goes dark |
| **13. System** | Version, board, updates, restart screen, reboot | Buttons ask for a second click |
| **14. Access** | Optional PIN | The page already opens from the home network only |
| **15. Advanced user** | Port, secure address, diagnostic file, start over | Every consequence is spelled out before you confirm |

## Advanced user

- **Port**: change `8080` only if another program uses it. Beranda checks the number is free, restarts,
  the Pi screen follows, and it falls back to 8080 by itself if the port cannot be used.
- **Secure address**: the same address with `https://` (same port). Needed for the microphone on a computer.
- **Diagnostic file**: a text file to attach to a bug report, with no secret inside.
- **Start over**: *settings only* (photos kept), or *everything* (settings, photos, downloaded data;
  asks twice). Both bring the port back to 8080.

## Limits per board

Beranda recognises the board and its memory and caps each list, so a small Pi never slows down.
Force a profile with `[limits] profile = "plus"` in `config.toml`.

| Board | Memory | Profile | Calendars | News sources | TV channels | Radio | Dates | Photos | Voice phrases |
|---|---|---|---|---|---|---|---|---|---|
| Pi 2, Zero 2 W | 0.5-1 GB | light | 3 | 8 | 15 | 15 | 100 | 200 | 20 |
| Pi 3 / 3B+, Pi 4 | 1 GB | standard | 10 | 20 | 40 | 30 | 200 | 500 | 50 |
| Pi 4, Pi 5 | 2 GB | comfortable | 15 | 30 | 60 | 50 | 400 | 800 | 80 |
| Pi 4, Pi 5, Pi 400 | 4 GB | comfortable + | 25 | 50 | 100 | 80 | 800 | 1,500 | 120 |
| Pi 4, Pi 5 | 8 GB + | maximum | 40 | 80 | 150 | 120 | 1,500 | 3,000 | 200 |

These are estimates; only the Pi 4 2 GB has been measured.
