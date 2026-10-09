# Using Beranda

Two pages, served by the Pi:

- `http://<pi-name>.local:8080/` is **the display** (the mirror or tablet shows this one);
- `http://<pi-name>.local:8080/admin` is **the settings page**, for your phone or computer on the
  same Wi-Fi. It refuses visitors from the internet.

## The settings page, box by box

![Settings page](screenshots/v0.4.0-admin.png)

The first time, a short welcome lists the three things to do. Every box has a **Need help?**
link with the details in plain words.

| Box | What it does |
|---|---|
| **1. Where are you?** | Type your town, press *Search*, click the right line: name, position and time zone fill in. Without internet, type latitude and longitude (press and hold on your home in any map app to read them). |
| **2. Country and language** | The country gives public holidays, the first day of the week and the suggested news; picking it also proposes its language. 48 languages for the screen. A region is only needed for regional holidays. |
| **3. Look** | Fifteen themes, shown live in the preview. *Auto* switches to night colours after sunset. |
| **4. Your calendar** | Paste the private link of your calendar and press *Test*. The box *Where do I find this link?* gives the steps for Google, Apple, Outlook, Nextcloud and Proton, each with a link to the official guide in your language. |
| **5. Dates that matter** | Births, remembrances, anniversaries. `2018-06-02` shows the number of years; `06-02` repeats every year. |
| **6. News headlines** | On by default with *Choose for me*. Untick it to pick media yourself (your town, your country, international, another country) and add any RSS feed; every line has a *Test* button. |
| **7. Screen** | Rotation for a screen hung upright (90° or 270°) or upside down (180°), and the hours to turn it off at night. On the Pi the screen itself switches off; on a tablet the page goes dark. |
| **8. System** | Version, *Check for updates*, *Update now*, *Restart the screen*, *Restart the Raspberry Pi*. Each button asks for a second click. They work when Beranda was installed with `install.sh`. |
| **9. Access** | Optional PIN. |

Press **Save**. The display picks the changes up within a minute, without a restart. The page
writes `~/.config/beranda/config.toml` (readable by you only, because calendar links are secrets).

## The themes

| Theme | Spirit | The season block |
|---|---|---|
| `japan` | washi paper, vermilion, ink | the 72 micro-seasons (七十二候) |
| `indonesia` | batik browns, indigo, a faint kawung motif | *pranata mangsa*, the Javanese farmers' calendar |
| `france` | almanac paper, navy, red, a tricolour rule | the Republican calendar: "16 Vendémiaire, Belle de nuit" |
| `germany` | Bauhaus: grey sheet, black, red, yellow | the ten phenological seasons of the DWD ("Vollherbst: Eicheln fallen") |
| `spain` | lime wash, terracotta, cobalt, Mudéjar star | the season and the *refrán* of the month |
| `italy` | a Renaissance page, Pompeian red | the season and the *proverbio* of the month |
| `portugal` | azulejos, cobalt on white | the season and the *provérbio* of the month |
| `brazil` | Copacabana waves, green and gold | the southern-hemisphere season and a *ditado* for every day |
| `africa` | bogolan mud cloth and a kente band | a Swahili proverb (*methali*) every day, with its meaning |
| `arab` | zellige stars, emerald and gold | the Hijri date (Umm al-Qura), ±1 day where the moon is sighted |
| `america` | 1930s national-park posters | the name of the next full moon (Hunter's Moon, Cold Moon...) |
| `india` | marigold, indigo, a rangoli lotus | the season (ṛtu, शरद) and the lunar day (tithi) |
| `china` | rice paper by day, red lacquer by night | the 24 solar terms (寒露...) and the lunar date (农历八月廿九) |
| `oceania` | tapa cloth, lagoon, coral | the Tahitian seasons of the Pleiades (Matari'i i ni'a / i raro) |
| `creole` | madras check | carême or hivernage (or the austral seasons) and a Haitian Creole proverb |

Any theme works with any language. Try combinations without saving:
`/?theme=brazil&lang=pt-BR&mode=night`.

Honest notes: micro-season, mangsa and phenological dates are averages that move from year to
year; Republican day names and proverbs come from tradition and spellings vary. Corrections
are welcome.

## On the wall

- **First start**: until the settings are saved, the screen shows the address of the settings
  page and a QR code to scan with your phone.
- **Upright screen**: choose the rotation in box 7. On a tall screen everything fits on one
  page: calendar and agenda sit side by side.
- **Night**: set "turn off at" and "turn back on at" in box 7.

## Without the settings page

Everything is in `config.toml`; see `config.example.toml`. The page is only a friendlier editor
for the same file (comments in the file are not kept when the page saves).
