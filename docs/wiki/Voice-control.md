# Voice control

Beranda listens with the **microphone of the device that shows it** (tablet or computer), never
the Pi's — and **only while a tap on the microphone button asked it to**. Nothing listens in the
background, ever.

## The one rule that trips everybody: the microphone needs SSL

A browser only hands its microphone to a **"secure" page** — an `https://` address. Plain
`http://beranda.local:8080` is refused, silently or with `insecure`. Beranda has had https on
the **same port** since 0.15.2, with a certificate it makes itself. That certificate is not
signed by an authority the browser knows, and that is fine: the browser warns once ("your
connection is not private") — tap *Advanced* → *Continue* — and the microphone is allowed from
then on. Self-made or not, the traffic is encrypted all the same.

## Setting it up

1. Settings page, box **11 · Voice control**: tick *Show the microphone button*, **Save**.
2. Open Beranda in **Google Chrome**. Edge offers speech recognition but its service fails
   ("network"); Firefox and Safari do not offer it to web pages.
3. Open the screen with **`https://`** instead of `http://` (same address, same port), and accept
   the one-time warning as above. **Without https there is no microphone**: this step is not
   optional. (A last resort without https exists: the one-time Chrome setting
   `chrome://flags/#unsafely-treat-insecure-origin-as-secure` with Beranda's `http://` address.)
4. Tap the round microphone, allow it, speak: "what's the weather", "play France Inter",
   "next station", "read me the day"...

Chrome turns the speech into text with Google's online service: your sentence crosses the
internet while the button listens, and only then. Beranda itself keeps nothing.

**A Bluetooth headset is two devices in one.** In music mode it has no microphone at all; Windows
only lends its microphone in "hands-free" mode, which also makes the sound poorer. If the browser
answers `audio-capture` while the computer clearly has a microphone, open Settings → System →
Sound → Input and pick the **Hands-Free** entry of that device — or plug it in by cable or with
its USB dongle, which always works. On Windows, also check Privacy & security → Microphone →
"Let desktop apps access your microphone".

## Why there is no wake word

Versions 0.17.2 to 0.17.7 tried an always-on wake word ("Beranda, ..."). It was taken out again:
a browser's continuous listening proved too fragile to trust — Chrome ends or starves the stream
on its own schedule — and it meant a microphone open all day, sending everything it heard to
Google. Hands-free voice would need a microphone on the Raspberry Pi itself, listening locally;
that road stays on the [Roadmap](Roadmap), parked. The button asks for the microphone only when
tapped, which a browser does reliably.

## What you can say

Box 11 → **Open the printable guide**: one A4 page, in the language the screen listens in, with
every phrase grouped (the day, the radio, looks and quiet), plus your own phrases. *Print / save
as PDF* uses the browser's own print dialog. Put it next to the mirror.

Out of the box, in 10 languages (English, French, German, Spanish, Italian, Portuguese, Brazilian
Portuguese, Arabic, Swahili, Indonesian): the time, the date, the weather, today's events,
tomorrow's events, read the whole day, the headlines, tonight's TV; play / stop / next / previous
station, louder / quieter; bigger text, normal text, high contrast, normal colours, be quiet.
"Bigger" and "high contrast" said out loud stay on that tablet (until said back); to make them
permanent for every screen, use box 16.

## When it does not work

In the **same browser**, settings page → Voice control → **Test the microphone on this device**.

| Message / code | Meaning | What to do |
|---|---|---|
| `insecure` | the page is http | open it with `https://` |
| `not-allowed` | microphone blocked | address bar icon → Microphone → Allow; check the system's privacy settings |
| `audio-capture` | no microphone | plug one in (headset, webcam) |
| `network` | the browser's speech service is unreachable | use Google Chrome; check the internet connection |
| `unsupported` | the browser cannot listen | use Google Chrome |

The screen also reports its result to the Pi: it shows in the diagnostic file.

**Privacy**: Chrome sends the sound to Google to turn it into text; Beranda only gets the text and keeps nothing.
Full guide: [docs/VOICE.md](https://github.com/regis57/Beranda/blob/main/docs/VOICE.md).
