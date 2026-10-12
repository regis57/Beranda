# Reporting a security problem

Thank you for looking. If you think you have found a way to break into Beranda, or to reach
something it should keep private, please tell us **privately first**, so it can be fixed before
it is public.

- Open a private report: **[Security → Report a vulnerability](https://github.com/regis57/Beranda/security/advisories/new)**
  (GitHub keeps it between you and the maintainer).
- Please do not open a normal issue for it, and please do not post it publicly until there is a fix.
- Expect a first answer within a week. Beranda is a spare-time project by one person, so please
  be patient; you will be credited in the fix unless you prefer otherwise.

Helpful in a report: what you did, what happened, and the version (settings page → *System*).
The **diagnostic file** (settings page → *Advanced user*) holds no password or private link and
tells us the version, the board and the settings.

## What is supported

The latest version on the `main` branch. Beranda is alpha: there are no long-term branches to
patch, so the fix for anything found goes into the next version.

## What Beranda is built to withstand

- **The settings page answers the home network only**, and can ask for a PIN. It is not meant to
  be reachable from the internet; do not forward its port on your router.
- **The web server never runs as root.** The few things that need root (update, restart, reboot,
  start over, Wi-Fi changes) are fixed requests dropped as files for a separate root service,
  which checks each one and refuses anything else.
- **Nothing a user types becomes part of a command**: every command is run from a list of
  arguments, never handed to a shell.
- **Secrets stay out of the way**: calendar links and the PIN live in a file only Beranda can
  read; Wi-Fi passwords stay with the system's own network manager. Neither reaches a log or the
  diagnostic file, where every web address is cut down to its site name.
- **The display loads nothing but its own files** (a strict Content-Security-Policy), so a hostile
  calendar entry or news headline cannot run code on the mirror.

## What it is not built to withstand

- Somebody who is already on your home network and knows the PIN, or who has physical access to
  the Raspberry Pi or its SD card.
- Beranda reads what you point it at: a calendar, a news feed, a TV guide. A deliberately
  malformed one should only ever make its own box empty - if you can make it do more, that is
  exactly the kind of report we want.

## How the code is checked

Every change runs automated tests, a linter with its security rules switched on, shellcheck on the
installer and the root services, and a full install on a clean machine. CodeQL reads the Python and
the JavaScript on every pull request and once a week, and gitleaks reads every commit ever made,
looking for anything shaped like a password or a key. Dependabot watches the libraries and the CI
actions. See [Contributing](https://github.com/regis57/Beranda/wiki/Contributing).
