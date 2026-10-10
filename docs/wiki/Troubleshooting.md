# Troubleshooting

First step, always: **`sudo beranda doctor`** on the Pi, and the **diagnostic file** (settings page →
*Advanced user* → *Download the diagnostic file*). The file holds no password, calendar link, Dropbox
link, feed address or PIN; web addresses are cut to the site name, the place is rounded to about 10 km.

| Symptom | Likely cause | Fix |
|---|---|---|
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
| Black screen on the Pi | the screen service stopped | `sudo systemctl restart beranda-kiosk` |
| Nothing shows a calendar | link expired or wrong | box 5: paste it again, *Test* |

Still stuck? [Open an issue](https://github.com/regis57/Beranda/issues) with the diagnostic file.
