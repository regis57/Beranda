# Wi-Fi setup with no keyboard

Normally, giving a Raspberry Pi its first Wi-Fi network means either plugging in a keyboard
and screen, or customising the SD card in Raspberry Pi Imager before flashing it. Beranda can
skip all of that: installed with `install.sh --with-wifi-setup` (or already baked into the
[ready-to-flash image](../pi-gen/README.md)), it can offer its *own* Wi-Fi network the moment
it boots with none configured, and let you pick a real one from your phone.

## What actually happens

1. At every boot, a small service checks whether the Pi already has a working connection
   (Wi-Fi saved from before, or a network cable plugged in). If it does, nothing else happens.
2. If not, after about 45 seconds the Pi turns its own Wi-Fi radio into an access point called
   **"Beranda setup"**. The screen (if one is plugged in) shows a QR code: scanning it with a
   phone's camera joins that network directly, the way scanning a restaurant's Wi-Fi code does.
3. Joining it opens a small page on its own (most phones and computers do this automatically
   for a new Wi-Fi network with no internet - it is what Beranda's setup network is counting
   on). It lists the Wi-Fi networks the Pi can see; pick yours, type its password, and press
   Connect.
4. The Pi joins that network, "Beranda setup" disappears, and the usual dashboard and settings
   page ( `http://beranda.local:8080/admin` ) take over - exactly as if Wi-Fi had been set up
   before the first boot.
5. If nobody finishes this within about 15 minutes, the Pi gives up, turns the access point off,
   and quietly tries again later - it does not broadcast an open network forever unattended.

## Why the setup network has no password

"Beranda setup" is deliberately open (no password) so a phone can join it with one tap, with
nothing to type until the real Wi-Fi password. It only exists for the few minutes it takes to
set up a new Pi, and only when there is no real network anyway - there being nothing else on
it to protect. The *real* Wi-Fi password you type into the page that opens is sent once, over
that temporary local network, straight to the Pi itself; it is never sent anywhere else, and
the page (like the rest of Beranda) never leaves the Pi's own Wi-Fi.

## Turning it on

```bash
curl -fsSL https://raw.githubusercontent.com/regis57/Beranda/main/install.sh | sudo bash -s -- --with-wifi-setup
```

Already installed? Run the command above again (installing again only repairs or adds to what
is there) - or see [`pi-gen/README.md`](../pi-gen/README.md) for an image with this, and
everything else Beranda needs, already built in.
