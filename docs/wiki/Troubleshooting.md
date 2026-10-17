# Troubleshooting

First step, always: **`sudo beranda doctor`** on the Pi, and the **diagnostic file** (settings page →
*Advanced user* → *Download the diagnostic file*). The file holds no password, calendar link, Dropbox
link, feed address or PIN; web addresses are cut to the site name, the place is rounded to about 10 km.

| Symptom | Likely cause | Fix |
|---|---|---|
| A box of the settings page stays empty, odd behaviour in Edge | Edge kept an older version of the page | use Google Chrome; in Edge press Ctrl+F5 |
| "The Pi is busy" | an update or a Wi-Fi change is running (about 1.5 min for an update) | wait a minute, reload |
| "The Pi's helper service is stuck" | the root helper failed several times | on the Pi: `sudo systemctl reset-failed beranda-actions.service beranda-actions.path && sudo systemctl restart beranda-actions.path` |
| The settings page does not answer | Beranda restarting, or another port | wait a minute; `sudo beranda doctor` tells the real address |
| Lost after changing the port | the address changed | open the new one; *Start over* brings back 8080 |
| `ERR_SSL_PROTOCOL_ERROR` | `https://` on a version before 0.15.2 | update, then use `https://` on the usual port |
| "Not private" warning on `https://` | self-made certificate | normal: *Advanced* → *Continue*, once per browser |
| Microphone: `network` | Microsoft Edge | use Google Chrome |
| Microphone: `not-allowed` | permission refused | address bar icon → Microphone → Allow |
| "No weather warning", always | area of another town, or misspelt | box 4: use the suggested area, press *Test* |
| TV channels show numbers | guide saved before 0.15.0 | open the TV box once, then *Save* |
| SD card full | caches, logs, swap file | update (it tidies), or the free-space line in [Install & Update](Install-and-Update) |
| New box / Wi-Fi password changed | the Pi knows no network in range | wait 2 minutes, join the "Beranda setup" Wi-Fi from a phone, pick the new network |
| "Use now" on a network did not work | wrong password, out of range | the Pi went back to the previous network by itself; fix the password with *Save this network* |
| "offline" badge while everything looks current | before 0.16.4: one news source failing (often "news about my town") | update; the diagnostic file names it in its log lines |
| "Too many wrong PINs" | 5 wrong PINs from this phone or computer | wait the minutes shown (other devices are not affected); restarting Beranda on the Pi also clears it |
| Forgot the PIN | | on the Pi: `sudo sed -i '/^pin = /d' /etc/beranda/config.toml && sudo systemctl restart beranda`, then set a new one in box 15 |
| "Beranda only answers devices on its own home network" | the phone is on mobile data, a guest network or a VPN | join the same Wi-Fi as the mirror, turn the VPN off |
| The microphone button does nothing, and nothing is ever heard | **v0.17.2 only**: the wake word kept the microphone for itself | update to 0.17.3; as a stopgap, empty the wake word box |
| Beranda answers on screen but says nothing out loud | the browser keeps a page nobody has touched quiet | touch the screen once (Beranda now says so); it lasts until the page is reloaded |
| "microphone in use" stays on, battery drains | the wake word is on: the microphone is open all the time | that is how it works; empty the wake word box to use the button only |
| The wake word stops working after a while | the browser's speech service kept failing, so Beranda gave up | the screen says so; reload the screen, and check the internet connection |
| `audio-capture`, and the computer does have a microphone | a **Bluetooth** headset or speakerphone: Windows only lends its microphone in "hands-free" mode, and a Bluetooth device in music mode has none | Settings → System → Sound → Input, pick the "Hands-Free" entry of that device; or plug it in by cable or its USB dongle, which always works. Also check Windows → Privacy & security → Microphone → "Let desktop apps access your microphone" |
| The wake word stops after about 15 s, every time (`audio-capture`) | something else on the computer took the microphone: another window using speech, Windows voice activation ("Hey Cortana", "Hey Copilot"), or an app holding the microphone | close the other window; Windows → Settings → Privacy → Speech, turn voice activation off; check that apps may use the microphone. Beranda now waits and tries again instead of giving up |
| Microphone test: "works, but heard nothing", with the wake word on | **0.17.2 to 0.17.6**: the preview on the settings page was a second screen holding the microphone | update to 0.17.7 |
| Several Beranda screens, and only one hears the wake word | on purpose: a browser has one microphone, the first screen keeps it | the others take over at once if it is closed |
| Voice works with one address and not the other | `rp4.local` and `192.168.1.x` are two sites for the browser: they cannot share the microphone | open Beranda with one address only |
| Black screen on the Pi | the screen service stopped | `sudo systemctl restart beranda-kiosk` |
| Nothing shows a calendar | link expired or wrong | box 5: paste it again, *Test* |

Still stuck? [Open an issue](https://github.com/regis57/Beranda/issues) with the diagnostic file.
