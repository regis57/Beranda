# Configuration reference

The settings page writes `config.toml` for you (`/etc/beranda/config.toml` on an installed Pi). Every
key is optional. Example: [config.example.toml](https://github.com/regis57/Beranda/blob/main/config.example.toml).

| Key | Default | Box | Meaning |
|---|---|---|---|
| `country` | `"FR"` | 2 | ISO code: holidays, week start, units, news |
| `subdivision` | none | 2 | region for regional holidays |
| `language` | `"fr"` | 2 | screen language (57) |
| `units` | metric | 2 | `metric` or `imperial` |
| `theme` | `"japan"` | 3 | one of 15 themes |
| `mode` | `"auto"` | 3 | `auto` (follows the sun), `light`, `night` |
| `[location]` `name`, `latitude`, `longitude`, `timezone` | Metz | 1 | your town |
| `[calendar]` `ics_urls` | `[]` | 5 | private calendar links |
| `key_dates` (a list of tables): `date`, `label`, `kind` | none | 6 | `MM-DD` or `YYYY-MM-DD`; `birth`, `death`, `anniversary`, `other` |
| `[news]` `enabled`, `sources`, `feeds` | on, automatic | 7 | catalogue ids and your own RSS links |
| `[history]` `enabled` | `true` | 7 | "on this day" |
| `[photos]` `folder`, `interval`, `dropbox_url` | own folder, 20 s | 8 | |
| `[radio]` `stations`, `volume` | `[]`, 70 | 9 | favourites |
| `[tv]` `url`, `channels`, `names` | none | 10 | XMLTV guide, ticked channel ids and their names |
| `[voice]` `enabled`, `commands` | off | 11 | your own phrases |
| `[screen]` `rotate`, `off`, `on` | 0, never | 12 | rotation in degrees, night hours `"23:00"` |
| `[admin]` `pin` | none | 14 | |
| `[server]` `host`, `port` | `0.0.0.0`, 8080 | 15 | the port also answers https |
| `[widgets]` `chart`, `air`, `alerts`, `alerts_area`, `ephemeris`, `second_clock` | on, on, off, -, on, - | 4 | extras of the main screen |
| `[limits]` `profile` | `auto` | - | `lite`, `standard`, `comfort`, `plus`, `max` |

Environment: `BERANDA_CONFIG` (settings file), `BERANDA_PROFILE` (limits), `BERANDA_PHOTOS`,
`BERANDA_REQUESTS`, `BERANDA_INSTALL_INFO` (set by the installer).
Command line: `beranda [serve|doctor] [--config PATH] [--demo] [--host H] [--port P]`.
