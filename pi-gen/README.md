# Building a ready-to-flash Beranda image

This folder is a [pi-gen](https://github.com/RPi-Distro/pi-gen) "custom stage": the same
mechanism Raspberry Pi OS itself is built with. Added to a pi-gen checkout, it produces a
`.img.xz` that already has Beranda installed, enabled, and set up to offer its own Wi-Fi
network ("Beranda setup") if the Pi boots with none configured - see
[`docs/WIFI_SETUP.md`](../docs/WIFI_SETUP.md). Flash it with Raspberry Pi Imager and the whole
of [roadmap item 1](../docs/ROADMAP.md) - installing without ever opening a terminal - is done.

**This has not been built or flashed from the cloud development session that wrote it.**
A pi-gen build needs a privileged container (to create loop devices and `chroot`), tens of
gigabytes of disk and well over an hour, none of which fit a quick cloud session - and, like
testing on real Raspberry Pi hardware (see roadmap item 2), actually flashing and booting the
result needs a real SD card and a real Pi. What is here is the build *definition* - the same
kind of file Raspberry Pi OS itself is built from - plus a GitHub Actions workflow that can run
the real build for you. Please build and flash it once, and report back anything that needs
fixing; this is exactly the kind of thing that is hard to get perfectly right without trying it.

## Building it yourself

```bash
git clone https://github.com/RPi-Distro/pi-gen.git
git clone https://github.com/regis57/Beranda.git
cp -r Beranda/pi-gen/stage-beranda pi-gen/stage-beranda
cp Beranda/pi-gen/config pi-gen/config
cd pi-gen
BERANDA_SRC="$(pwd)/../Beranda" ./build-docker.sh
```

`build-docker.sh` runs the whole build inside Docker (it needs `--privileged`, which it asks
for itself) so nothing else needs installing first. The finished image lands in
`pi-gen/deploy/*.img.xz`. See pi-gen's own README for options (a 64-bit build, a different
Raspberry Pi OS release to build from, etc.) - nothing in `stage-beranda` depends on those.

## Building it with GitHub Actions instead

[`.github/workflows/build-image.yml`](../.github/workflows/build-image.yml) does the same
build in CI. Run it from the Actions tab ("Run workflow") - it takes a while (pi-gen itself
warns to expect over an hour) - and download the `.img.xz` from the finished run's artifacts.

## What the image does on first boot

- With a monitor plugged in: shows the dashboard (demo data at first) and, if no Wi-Fi was
  set up when the SD card was flashed (Raspberry Pi Imager can do this for you, with no image
  customisation needed), a QR code for a temporary open Wi-Fi network called "Beranda setup".
- Join it from a phone, a page opens by itself, and from there you pick your real home Wi-Fi -
  no keyboard, no terminal, no typing an IP address.
- Once connected, open the settings page shown on screen (or `http://beranda.local:8080/admin`)
  to pick your city, language, and the rest.
