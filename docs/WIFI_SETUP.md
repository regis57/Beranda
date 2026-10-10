# Wi-Fi: set it up, keep it, never get locked out

Giving a Raspberry Pi its Wi-Fi is usually the hard part: a keyboard and a screen, or the right
box ticked in Raspberry Pi Imager before flashing. Beranda makes it a page on your phone, and
keeps it working for good.

## Every day: the Wi-Fi box of the settings page (box 13)

- **See** the network in use, its strength, the Pi's address, and whether a cable is plugged in.
- **Add a network**: *Search networks*, tap yours, type its password, *Save this network*. Adding
  never cuts the current connection: the Pi only remembers it, and joins it whenever it is in range.
- **Keep several** (home, holiday house, a phone used as a hotspot...): the Pi joins the best one in range.
- **Use now**: switches straight away. If the new network does not work within 45 seconds, the Pi
  goes back to the one that worked, by itself.
- **Forget** a network. The one in use cannot be forgotten unless a cable keeps the Pi reachable.

Networks are saved by the Pi's own system (NetworkManager, standard on Raspberry Pi OS), so they
survive restarts, updates, and even uninstalling Beranda. Passwords stay there too: never in
Beranda's settings, never in a log or the diagnostic file.

## The safety net: "Beranda setup"

On by default wherever NetworkManager runs the Wi-Fi (Raspberry Pi OS since Bookworm).

1. A small service watches the connection all the time.
2. With **no network at all for 2 minutes** (45 seconds on a Pi that knows no Wi-Fi yet), the Pi
   turns its radio into an open access point called **"Beranda setup"**. The screen shows a QR code.
3. Join it from a phone: a page opens by itself and lists the networks the Pi can see. Pick yours,
   type the password, *Connect*.
4. The Pi joins it, "Beranda setup" disappears, and Beranda is back at its usual address.
5. Nobody came? After 5 minutes (15 on a first start) the Pi closes "Beranda setup" and tries its
   known networks again, so it comes back by itself when the usual Wi-Fi returns (a box that was
   restarting, for instance). Then it keeps watching.

This is what makes the Wi-Fi durable: a new box, a changed password or a move never needs a
keyboard or a terminal.

### Why "Beranda setup" has no password

So a phone joins it with one tap. It only exists while the Pi has no real network anyway, for a
few minutes at a time. The real Wi-Fi password you type in its page goes once, over that local
network, straight to the Pi; it is never sent anywhere else.

## Turning the safety net off, or on by force

```bash
# off (it stays off through updates):
curl -fsSL https://raw.githubusercontent.com/regis57/Beranda/main/install.sh | sudo bash -s -- --no-wifi-setup
# on even where NetworkManager is not running the network yet (it gets installed):
curl -fsSL https://raw.githubusercontent.com/regis57/Beranda/main/install.sh | sudo bash -s -- --with-wifi-setup
```

Already installed before 0.16? The *Update* button turns the safety net on by itself.

## First Wi-Fi on a brand-new card

Easiest: set the Wi-Fi in Raspberry Pi Imager. No Wi-Fi to type there? Plug in a network cable for
the installation; afterwards, add the Wi-Fi from box 13 and unplug the cable. Or use the
[ready-to-flash image](../pi-gen/README.md), which opens "Beranda setup" on its first start.

> Honest note: this was designed and tested with a simulated Wi-Fi; the first real tries are
> listed on the [Status](https://github.com/regis57/Beranda/wiki/Status) page. For your first
> change of network, keep a cable or a screen and keyboard at hand.
