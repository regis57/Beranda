# Install & Update

## What you need

- A Raspberry Pi: 3B+ or newer is comfortable; older boards run in a light mode ([limits](Settings-box-by-box#limits-per-board)).
- A microSD card: 8 GB works, **16 GB is more comfortable**.
- A screen with HDMI (or an old tablet, see below), and a phone or computer on the same Wi-Fi.

## Install, in five steps

1. **Prepare the card** with [Raspberry Pi Imager](https://www.raspberrypi.com/software/): *Raspberry Pi OS Lite (64-bit)*.
   In the customise window: a name (say `beranda`), your Wi-Fi, a user and password, SSH on.
2. **Plug in the screen and the card**, power on, wait two minutes.
3. **Open a terminal** on your computer (Windows: *PowerShell*): `ssh your-user@beranda.local`
4. **Paste**: `curl -fsSL https://raw.githubusercontent.com/regis57/Beranda/main/install.sh | sudo bash`
   (5 to 15 minutes on a Pi 3).
5. **Finish from your phone**: scan the QR code on the screen, or open `http://beranda.local:8080/admin`.

### Installer options

Put them after `bash -s --`, for example `... | sudo bash -s -- --no-screen`.

| Option | What it does |
|---|---|
| `--no-screen` | server only: show Beranda on a tablet or another device |
| `--hostname kitchen` | renames the Pi: `http://kitchen.local:8080/admin` |
| `--no-wifi-setup` | do not install the Wi-Fi safety net (on by default, see below) |
| `--with-wifi-setup` | force the safety net on, installing NetworkManager if needed |
| `--branch NAME` | install another branch |
| `--dry-run` | print what would be done, change nothing |

### What gets installed

Python, fonts for every script, Cage and Chromium (the full-screen browser), a `beranda` user (never
root), and these services:

| Service | Role |
|---|---|
| `beranda` | the web server: display page and settings page |
| `beranda-kiosk` | the full-screen browser on the HDMI screen |
| `beranda-actions` | a tiny root service that only runs the buttons of the settings page (update, restart screen, reboot, start over) |
| `beranda-wifi-setup` | the Wi-Fi safety net: with no known network for 2 minutes, opens "Beranda setup" (on by default where NetworkManager runs the Wi-Fi) |

Files: the program in `/opt/beranda`, your settings in `/etc/beranda/config.toml` (private), photos and
cache in `/var/lib/beranda`.

## Wi-Fi

Add, switch and forget networks from the settings page, box **13 · Wi-Fi**. Networks are kept by the
Pi's own system and survive restarts and updates. If one day the Pi finds no known network for two
minutes (new box, changed password), it opens its own Wi-Fi **"Beranda setup"**: join it from a phone
and pick the right network, no keyboard needed. Guide: [docs/WIFI_SETUP.md](https://github.com/regis57/Beranda/blob/main/docs/WIFI_SETUP.md).

No Wi-Fi typed into Imager? Plug a network cable in for the installation, then add the Wi-Fi from box 13.

## An old tablet as the screen

Install with `--no-screen`, then open `http://beranda.local:8080` in the tablet's browser
(**Google Chrome** recommended) and add it to the home screen. Radio and voice use the tablet's
speakers and microphone.

## Update

Settings page → **System** → *Check for updates* → *Update now*. Or run the install line again: it
updates and repairs, and keeps your settings. Every update also tidies the SD card (`beranda-tidy`):
package and pip caches, old versions, a 50 MB system log, and on cards under 32 GB the swap file.

## If the settings page does not answer

```bash
ssh your-user@beranda.local
sudo beranda doctor
```

It says what is wrong and on which address Beranda really answers.

| To... | Type |
|---|---|
| see whether it runs, and why it stopped | `sudo systemctl status beranda` then `sudo journalctl -u beranda -n 50` |
| restart it | `sudo systemctl restart beranda beranda-kiosk` |
| update or repair it (keeps your settings) | the install line above |
| read the port it uses | `sudo grep -A3 '\[server\]' /etc/beranda/config.toml` |
| free space on the SD card | `sudo apt clean && sudo apt autoremove --purge && sudo journalctl --vacuum-size=50M` |

Run these **on the Pi** (after `ssh`), not on your computer.

## Uninstall

`sudo /opt/beranda/src/uninstall.sh` (add `--purge` to delete your settings too).
