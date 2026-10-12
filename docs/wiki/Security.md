# Security

Beranda lives on your home network, next to your phone and your computer. This page says, in plain
words, what protects it, what does not, and how every change to the code is checked.

Found a problem? Please tell us privately first:
**[Security → Report a vulnerability](https://github.com/regis57/Beranda/security/advisories/new)**
(more in [SECURITY.md](https://github.com/regis57/Beranda/blob/main/SECURITY.md)).

## In one minute: what you should do

1. **Keep it at home.** Never open ("forward") Beranda's port on your router. It is made for your
   home network, not for the internet.
2. **Set a PIN** (settings page → *Access*) if people you do not fully trust use your Wi-Fi:
   guests, flatmates, a shared building network. Choose **6 digits or more**.
3. **Keep it up to date**: settings page → *System* → *Update*. Fixes arrive that way.
4. **Use Google Chrome** for the settings page and the screen.
5. **Read the diagnostic file before you share it.** It is made to be shared, and holds no
   password or private link, but it is your file and your decision.

## What protects your Beranda

### The settings page

| Protection | What it means for you |
|---|---|
| **Home network only** | The settings page and its API answer only addresses from a home network (`192.168.x.x`, `10.x.x.x` and the like). From anywhere else, the answer is "refused". |
| **Optional PIN** | Once set, every change needs it. It is compared in a way that does not leak, digit by digit, how close a guess was. |
| **No changes from other websites** | A website open in another tab of your browser cannot send changes to your Beranda: a change must come from Beranda's own page. |
| **Size limits** | Lists (calendars, feeds, photos...) are capped to what your board can carry, so a mistake, or a file edited by hand, cannot overload a small Pi. See [the limits per board](https://github.com/regis57/Beranda#what-your-raspberry-pi-can-hold). |

### The Raspberry Pi itself

| Protection | What it means for you |
|---|---|
| **The web server never runs as root** | It runs as its own user, `beranda`, which can only touch Beranda's own files. |
| **Root jobs are a short fixed list** | Update, restart, reboot, start over and Wi-Fi changes need root. The web server cannot do them itself: it leaves a request (a file with a fixed name) for a separate root service, which checks it and refuses anything it does not know. |
| **No command is ever built from what you type** | Every command is run as a list of words, never handed to a shell. A Wi-Fi name like `x; rm -rf /` is just a strange Wi-Fi name. |
| **Root services choose where commands come from** | They set their own `PATH`, so a command such as `nmcli` can only ever be found in folders that root owns. |
| **The SD card is kept tidy** | Every update clears old caches and caps the logs (50 MB), so a full card does not stop the Pi. |

### Your secrets

| Secret | Where it lives | Where it never goes |
|---|---|---|
| Calendar links, Dropbox link, PIN | `/etc/beranda/config.toml`, readable by Beranda only (mode 0600) | logs, the diagnostic file, error messages |
| Wi-Fi passwords | the Pi's own network manager (NetworkManager), like any Linux computer | Beranda's settings, logs, answers to the page |
| A Wi-Fi password on its way | a small request file, readable by its owner only, **deleted the moment it is read** | anywhere else |

On top of that:

- **Logs say what failed, never the details.** A log line names the kind of source ("weather",
  "calendar") and the type of problem ("ConnectTimeout"). Never a web address (it can hold a secret),
  never the town's coordinates.
- **The diagnostic file is cleaned before you get it**: every web address is cut down to its site
  name, your position is rounded to about 10 km, and no password, PIN or private link is in it.
  See [Data sources & privacy](Data-sources-and-privacy).

### What Beranda downloads

Your calendar, your news feeds and your TV guide are addresses **you** type. Beranda is careful with them:

- **Every address is checked, twice**: when you save the settings, so a typing mistake shows up while
  you are still looking at the screen, and again just before each download. It must start with
  `http://` or `https://` (or `webcal://` for a calendar), name a real site, carry no user name or
  password, and hold no invisible characters. Anything else, such as `file://`, is refused.
- **Every download has a maximum size**: 8 MB for a calendar, 3 MB for a news feed, 25 MB for a TV guide
  (300 MB once unpacked, read bit by bit, never all at once).
- **News, TV and weather warnings are read with a hardened XML reader** (`defusedxml`), so a booby-trapped
  file (an "XML bomb") cannot freeze the Pi.
- **The "Test" buttons only send back what reads as a calendar, a feed or a guide**, never the page
  itself, so they cannot be used to peek at another device on your network.

### Your photos

- A shared Dropbox folder is unpacked **one picture at a time**: each file keeps only its own name (it
  cannot land outside the photo folder), must really be a picture (its first bytes are checked, not just
  its name), and must weigh less than 15 MB.
- The screen can only show picture files that are **inside your photo folder**: asking for
  `../../etc/passwd` gets "not found".

### The screen and the browser

- **The screen loads nothing but Beranda's own files** (a strict *Content-Security-Policy*). A calendar
  entry or a headline written to attack the mirror is shown as plain text and cannot run anything.
- **Your addresses are not sent to other sites** when a link is opened (*no-referrer*), and files are
  never guessed as another type than the one they are (*nosniff*).
- **https on the same port**, with a certificate Beranda makes itself, so the browser allows the
  microphone. It encrypts what travels between the browser and the Pi. Because no official authority
  signed it, the browser warns once: that is expected.

### Wi-Fi

- The **Wi-Fi box** shows, saves and switches networks through the root service above. If a switch
  fails, the Pi goes back to the network that worked, by itself, after 45 seconds.
- The **"Beranda setup" safety net** opens a Wi-Fi network of its own only when the Pi has had **no
  connection at all** for a while (45 seconds on a first start, 2 minutes later on). It closes as soon
  as the Pi is connected, or after 15 minutes (5 once a network is known) to let the Pi try its known
  networks again.

## What Beranda is not built to withstand

Being clear about the limits matters as much as the protections:

- **Someone already on your home network who knows the PIN**, or anyone with the Pi or its SD card in
  their hands. The SD card is not encrypted.
- **The screen itself is open to your home network.** The display page, its data (your agenda, the
  news) and your photos answer any device on your network, with no PIN: that is how a tablet shows
  them. One more reason never to open the port on your router.
- **Wrong PINs are not counted yet.** Someone on your network could try PIN after PIN. A 6-digit PIN
  or longer makes that slow; a limit is a planned improvement.
- **Over `http://`, the PIN crosses your home network unencrypted.** Your Wi-Fi password protects it
  from outside; if you do not trust everyone on your network, open the settings page with `https://`.
- **While "Beranda setup" is open, it is an open network.** Anyone close enough can join it during
  those minutes and see the Wi-Fi picker. It only opens when the Pi has no connection at all.

## How every change is checked

Nothing reaches the `main` branch without going through a pull request and these checks:

| Check | What it looks for | When |
|---|---|---|
| **Automated tests** (about 530) | Beranda doing what it should, including refusing what it should | every change |
| **ruff**, with its security rules on | risky patterns in Python: shell commands, unsafe temporary files, swallowed errors, dates without a time zone... | every change |
| **shellcheck** | mistakes in the installer and the root scripts | every change |
| **A full install** | the one-line installer, on a fresh Ubuntu machine | every change |
| **[CodeQL](https://codeql.github.com)** (GitHub) | the paths behind real flaws, in the Python and the JavaScript: a command or a path built from something a visitor typed, a secret reaching a log... | every pull request, every change to `main`, and once a week |
| **[gitleaks](https://github.com/gitleaks/gitleaks)** | anything shaped like a password, a key or a token, in **every commit ever made** | every change, and once a week |
| **[Dependabot](https://docs.github.com/en/code-security/dependabot)** (GitHub) | known flaws in the libraries Beranda uses and in the CI actions; proposes the update itself | every week |

And around them:

- **CI actions are named by their exact commit**, not by a tag: a tag can be moved to point at
  other code, and these run with access to the repository.
- **Each CI job gets the smallest permission it needs**, most of them "read the code, nothing else".
- **Private vulnerability reporting** is switched on, so a flaw can be reported without being public.

### When a check flags something on purpose

It is not quietly switched off: the reason is written next to the code, in one sentence. Three things
are deliberate and will keep being flagged:

- **Beranda listens on every address of the Pi.** It has to: your phone must be able to reach it.
- **The photo folder and the folder for downloaded copies are paths you choose.** Choosing them is the
  point. Beranda runs as its own user, so it can only read and write where that user may.
- **Beranda downloads from addresses you give it.** That is the whole feature; each one goes through
  the check described above (`src/beranda/urls.py`).

In October 2026 every CodeQL alert was gone through: the real ones were fixed in 0.16.8, the
deliberate ones were explained in the code and closed with that reason.
