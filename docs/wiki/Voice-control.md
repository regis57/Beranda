# Voice control

Beranda listens with the **microphone of the device that shows it** (tablet or computer), never the Pi's.

1. Settings page, box **11 · Voice control**: tick *Show the microphone button*, **Save**.
2. Open Beranda in **Google Chrome**. Edge offers speech recognition but its service fails
   ("network"); Firefox and Safari do not offer it to web pages.
3. Use the **secure address**: `https://` instead of `http://`, same address and port. The first
   time, accept the "not private" warning (*Advanced* → *Continue*): the certificate is made by Beranda.
4. Tap the round microphone, allow it, speak: "what's the weather", "play France Inter", "next station"...

The other way round step 3: a one-time Chrome setting,
`chrome://flags/#unsafely-treat-insecure-origin-as-secure` with Beranda's `http://` address.

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
