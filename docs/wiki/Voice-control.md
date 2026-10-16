# Voice control

Beranda listens with the **microphone of the device that shows it** (tablet or computer), never the Pi's.

1. Settings page, box **11 · Voice control**: tick *Show the microphone button*, **Save**.
2. Open Beranda in **Google Chrome**. Edge offers speech recognition but its service fails
   ("network"); Firefox and Safari do not offer it to web pages.
3. Use the **secure address**: `https://` instead of `http://`, same address and port. The first
   time, accept the "not private" warning (*Advanced* → *Continue*): the certificate is made by Beranda.
4. Tap the round microphone, allow it, speak: "what's the weather", "play France Inter", "next station", "read me the day"...

The other way round step 3: a one-time Chrome setting,
`chrome://flags/#unsafely-treat-insecure-origin-as-secure` with Beranda's `http://` address.

## Without touching the screen: the wake word

Box 11 → *Speak without touching the screen* → type a word, say **Beranda**, and Save. Reload the
screen on the tablet once. From then on the tablet listens all the time (with its own microphone,
through the browser's speech service): say the word, then your sentence, in one breath
("Beranda, what's the weather") or in two (say "Beranda", wait for *Listening…*, then speak).
A word of two syllables or more works best; a very short one wakes it up by mistake. Leave the
box empty to keep the microphone button only. While it is on, the microphone button on the screen
wears a ring, so an always-listening microphone is never invisible.

**Know what it costs, before you switch it on.** The tablet holds its microphone open all the
time, and Chrome sends **everything it hears** to Google to turn it into text, not only your
commands. Chrome shows "microphone in use" for as long as it lasts, the battery drains faster,
and a television nearby can wake it up. Beranda itself keeps nothing, and the Raspberry Pi hears
nothing. If any of that bothers you, empty the box: the microphone button alone only listens
while you hold it.

**It is the browser's own listening**, and it is not reliable: Chrome stops a long listen by
itself and Beranda starts it again; when its service keeps failing, Beranda waits longer and
longer and finally gives up with a message rather than asking every second.

**A Bluetooth headset is two devices in one.** In music mode it has no microphone at all; Windows
only lends its microphone in "hands-free" mode, which also makes the sound poorer. If the browser
answers `audio-capture` while the computer clearly has a microphone, open Settings → System →
Sound → Input and pick the **Hands-Free** entry of that device — or plug it in by cable or with
its USB dongle, which always works. On Windows, also check Privacy & security → Microphone →
"Let desktop apps access your microphone".

**A browser has one microphone.** Chrome lets a single page listen at a time; a second one is
cut off, and "the microphone works but heard nothing" is what that looks like. So all the
Beranda pages in a browser agree among themselves: the **first** screen with a wake word keeps
the microphone, other screens wait (and take over at once if it is closed), and the microphone
button or the settings page's *Test* borrows it for a moment and gives it back. The little
preview of the screen on the settings page never listens at all. One thing they cannot agree
across: two different addresses for the same Pi (`rp4.local` and `192.168.1.x`) are, for the
browser, two different sites: open Beranda with one address only.

If the wake word stops after a few seconds with `audio-capture`, something outside the browser
took the microphone. On Windows the usual causes are **voice activation** (Settings → Privacy &
security → Speech, and the "wake word" settings of Cortana or Copilot), or an app holding it.

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
