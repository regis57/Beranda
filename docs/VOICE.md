# Voice control

Beranda can listen to you and answer out loud. **It uses the microphone and the speakers of the
tablet that shows Beranda** — never the Raspberry Pi's.

## How to use it, step by step

1. Open the settings page, box **10 · Voice control**, tick **Show the microphone button** and
   press **Save**.
2. On the tablet, open Beranda in **Chrome or Edge**. (Firefox and Safari do not offer speech
   recognition to web pages in the same way.)
3. Browsers only allow a microphone on "secure" pages, and an address such as
   `http://192.168.1.20:8080` is not one. One-time fix on the tablet: open
   `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, type Beranda's address (for
   example `http://192.168.1.20:8080`), set the flag to **Enabled** and restart Chrome.
4. Tap the round **microphone** at the bottom right of the screen. The first time, Chrome asks
   to use the microphone: tap **Allow**.
5. Say a short sentence. The screen shows what it understood, Beranda answers out loud and does it.

> **Privacy.** Chrome and Edge turn your voice into text with the browser maker's *online*
> service, so the sound of your voice goes over the internet to them. Beranda itself only
> receives the resulting text, uses it and keeps nothing.

## Which languages?

The tablet listens in the **display language** chosen in box 2 of the settings page.

- Ten languages have ready-made phrases: English, French, German, Spanish, Italian, Portuguese,
  Brazilian Portuguese, Arabic, Swahili and Indonesian. In those, Beranda also answers out loud
  in that language.
- Any of the other 47 display languages understands the **English** phrases, and any language at
  all works for **your own phrases** (below), as long as Chrome can recognise it.

## What you can say (default phrases)

Several phrases mean the same thing: say any one of them. The sentence can be longer than the
phrase ("hey, what's the weather like today?"): Beranda looks for the phrase inside it. If two
phrases fit, the longest one wins.

Saying only "play" (or its equivalent) starts your **first** favourite station; "play France
Inter" starts the favourite whose name is closest to what was heard. Only your own favourite
stations (box 8) can be started.

**English** (`en`)

| What | You can say |
|---|---|
| Weather | “what's the weather” · “weather” · “forecast” |
| Time | “what time is it” · “time” |
| Tonight on TV | “tv tonight” · “what's on tonight” · “on tv” · “television” |
| Play a station (say its name after) | “play” |
| Stop the radio | “turn off the radio” · “stop the radio” · “stop” · “quiet” |
| Next station | “next station” · “next radio” · “skip” |
| Previous station | “previous station” · “last station” · “go back” |
| Volume up | “volume up” · “louder” · “turn it up” |
| Volume down | “volume down” · “quieter” · “turn it down” |

**Français** (`fr`)

| What | You can say |
|---|---|
| Weather | “quel temps fait-il” · “météo” · “previsions” |
| Time | “quelle heure est-il” · “heure” |
| Tonight on TV | “à la télé” · “programme tv” · “programme télé” · “télévision” |
| Play a station (say its name after) | “joue” · “mets” · “écoute” |
| Stop the radio | “coupe la radio” · “arrête la radio” · “silence” · “arrête” · “stop” |
| Next station | “station suivante” · “radio suivante” · “suivante” · “suivant” |
| Previous station | “station précédente” · “radio précédente” · “précédente” · “précédent” |
| Volume up | “plus fort” · “monte le son” · “augmente le volume” |
| Volume down | “moins fort” · “baisse le son” · “baisse le volume” |

**Deutsch** (`de`)

| What | You can say |
|---|---|
| Weather | “wie ist das wetter” · “wetter” · “vorhersage” |
| Time | “wie spät ist es” · “uhrzeit” · “zeit” |
| Tonight on TV | “fernsehprogramm” · “im fernsehen” · “tv-programm” · “fernsehen” |
| Play a station (say its name after) | “spiele” · “spiel” |
| Stop the radio | “radio aus” · “stopp” · “stop” · “leise” |
| Next station | “nächster sender” · “nächste station” · “nächster” |
| Previous station | “vorheriger sender” · “letzter sender” · “zurück” |
| Volume up | “lauter” |
| Volume down | “leiser” |

**Español** (`es`)

| What | You can say |
|---|---|
| Weather | “qué tiempo hace” · “tiempo” · “pronóstico” |
| Time | “qué hora es” · “hora” |
| Tonight on TV | “en la tele” · “programa de tv” · “televisión” |
| Play a station (say its name after) | “pon” · “reproduce” · “escucha” |
| Stop the radio | “para la radio” · “detén la radio” · “silencio” · “para” |
| Next station | “siguiente emisora” · “siguiente” |
| Previous station | “emisora anterior” · “anterior” |
| Volume up | “sube el volumen” · “más fuerte” · “más alto” · “sube” |
| Volume down | “baja el volumen” · “más bajo” · “baja” |

**Italiano** (`it`)

| What | You can say |
|---|---|
| Weather | “che tempo fa” · “meteo” · “previsioni” |
| Time | “che ora è” · “ora” |
| Tonight on TV | “stasera in tv” · “programma tv” · “in tv” · “televisione” |
| Play a station (say its name after) | “metti” · “riproduci” · “ascolta” |
| Stop the radio | “ferma la radio” · “silenzio” · “stop” |
| Next station | “stazione successiva” · “successiva” · “prossima” |
| Previous station | “stazione precedente” · “precedente” |
| Volume up | “alza il volume” · “più forte” · “volume su” |
| Volume down | “abbassa il volume” · “più piano” · “volume giù” |

**Português** (`pt`)

| What | You can say |
|---|---|
| Weather | “que tempo faz” · “previsão” · “meteorologia” |
| Time | “que horas são” · “hora” |
| Tonight on TV | “na televisão” · “programação” · “na tv” · “televisão” |
| Play a station (say its name after) | “põe” · “toca” · “ouve” |
| Stop the radio | “para a rádio” · “silêncio” · “para” |
| Next station | “estação seguinte” · “seguinte” |
| Previous station | “estação anterior” · “anterior” |
| Volume up | “aumenta o volume” · “mais alto” · “mais forte” |
| Volume down | “diminui o volume” · “mais baixo” · “mais fraco” |

**Português (Brasil)** (`pt-BR`)

| What | You can say |
|---|---|
| Weather | “que tempo faz” · “previsão” · “meteorologia” |
| Time | “que horas são” · “hora” |
| Tonight on TV | “na televisão” · “programação” · “na tv” · “televisão” |
| Play a station (say its name after) | “põe” · “toca” · “ouve” |
| Stop the radio | “para o rádio” · “silêncio” · “para” |
| Next station | “rádio seguinte” · “seguinte” · “próxima” |
| Previous station | “rádio anterior” · “anterior” |
| Volume up | “aumenta o volume” · “mais alto” · “mais forte” |
| Volume down | “diminui o volume” · “mais baixo” · “mais fraco” |

**العربية** (`ar`)

| What | You can say |
|---|---|
| Weather | “كيف حال الطقس” · “الطقس” · “توقعات” |
| Time | “كم الساعة” · “الوقت” |
| Tonight on TV | “برنامج التلفاز” · “على التلفاز” · “التلفزيون” |
| Play a station (say its name after) | “شغل” · “استمع” |
| Stop the radio | “أوقف الراديو” · “صمت” · “قف” |
| Next station | “المحطة التالية” · “التالي” |
| Previous station | “المحطة السابقة” · “السابق” |
| Volume up | “ارفع الصوت” |
| Volume down | “اخفض الصوت” |

**Kiswahili** (`sw`)

| What | You can say |
|---|---|
| Weather | “hali ya hewa” · “utabiri” |
| Time | “saa ngapi” · “muda” |
| Tonight on TV | “kwenye tv” · “televisheni” |
| Play a station (say its name after) | “cheza” · “sikiliza” |
| Stop the radio | “zima redio” · “kimya” · “simama” |
| Next station | “kituo kinachofuata” · “kinachofuata” |
| Previous station | “kituo kilichotangulia” · “kilichotangulia” |
| Volume up | “ongeza sauti” |
| Volume down | “punguza sauti” |

**Bahasa Indonesia** (`id`)

| What | You can say |
|---|---|
| Weather | “bagaimana cuacanya” · “cuaca” · “ramalan” |
| Time | “jam berapa” · “waktu” |
| Tonight on TV | “acara tv” · “di tv” · “televisi” |
| Play a station (say its name after) | “putar” · “dengarkan” |
| Stop the radio | “matikan radio” · “diam” · “berhenti” |
| Next station | “stasiun berikutnya” · “berikutnya” |
| Previous station | “stasiun sebelumnya” · “sebelumnya” |
| Volume up | “naikkan volume” · “lebih keras” |
| Volume down | “turunkan volume” · “lebih pelan” |

## Adding your own phrases

In box **10**, under **Your own phrases**, press **+ Add a phrase**:

1. type what *you* will say (for example *good night*, *wake me up*, *what's for tonight*);
2. choose what should happen: start the radio (and which favourite), stop it, next or previous
   station, volume up or down, tell the weather or the time, read tonight's TV, or **just answer
   with a sentence** that you write (for example *Sleep well*);
3. press **Save**.

Your phrases always win over the built-in ones, and the longest phrase wins among yours. You can
keep up to 50. They are stored in the `[[voice.commands]]` part of the configuration file:

```toml
[voice]
enabled = true

[[voice.commands]]
phrase = "good night"
action = "say"
reply = "Sleep well"

[[voice.commands]]
phrase = "wake me up"
action = "radio_play"
station = "960d0c25-0601-11e8-ae97-52543be04c81"   # the favourite's uuid; leave out = the first one
```

Actions: `radio_play`, `radio_stop`, `radio_next`, `radio_prev`, `volume_up`, `volume_down`,
`weather`, `time`, `tv`, `say`.

## If it does not work

- **No microphone button on the screen**: the box in step 1 is not ticked, or Save was not pressed.
  The button only exists once voice control is saved as on; it then shows up within a minute
  (reload the screen to see it at once).
- *"Microphone unavailable"* on the screen: step 3 (secure page) or step 4 (permission) is missing.
  The settings page also says whether **this** device can listen.
- Nothing is understood: speak close to the tablet, and check the display language (box 2).
- The browser's speech service needs internet; the rest of Beranda does not.
