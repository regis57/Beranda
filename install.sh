#!/usr/bin/env bash
# Beranda installer for Raspberry Pi OS (Bookworm or newer) and other Debian-based systems.
#
#   curl -fsSL https://raw.githubusercontent.com/regis57/Beranda/main/install.sh | sudo bash
#
# What it does, in order (nothing else):
#   1. installs the system packages it needs (Python, fonts, and for the screen: Cage + Chromium)
#   2. creates a "beranda" system user that runs everything (not root)
#   3. downloads Beranda into /opt/beranda and installs it in its own Python environment
#   4. starts it at every boot, and shows it full screen on the HDMI screen
# Run it again at any time to repair or update. To remove: sudo /opt/beranda/src/uninstall.sh
#
# Options (after "bash -s --" when piped, e.g. "... | sudo bash -s -- --no-screen"):
#   --no-screen        server only: no full-screen browser (for a tablet or another screen)
#   --hostname NAME    rename the Pi, so the settings are at http://NAME.local:8080/admin
#   --branch NAME      install another branch of the repository (default: main)
#   --source DIR       install from a local copy instead of downloading (for developers)
#   --no-systemd       do not install the services (containers, tests)
#   --with-wifi-setup  no Wi-Fi configured yet? let the Pi offer its own "Beranda setup"
#                      Wi-Fi network to pick one from a phone, with no keyboard at all
#   --dry-run          print what would be done, change nothing
set -euo pipefail

REPO="https://github.com/regis57/Beranda.git"
BRANCH="main"
PREFIX="/opt/beranda"
CONFDIR="/etc/beranda"
STATEDIR="/var/lib/beranda"
USER_NAME="beranda"
SCREEN=1
SYSTEMD=1
WIFI_SETUP=0
DRY=0
SOURCE=""
NEW_HOSTNAME=""

say()  { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m==> %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[1;31mError: %s\033[0m\n' "$*" >&2; exit 1; }
run()  { if [ "$DRY" = 1 ]; then printf '    $ %s\n' "$*"; else "$@"; fi; }

while [ $# -gt 0 ]; do
    case "$1" in
        --no-screen) SCREEN=0 ;;
        --no-systemd) SYSTEMD=0 ;;
        --with-voice) warn "--with-voice is no longer needed: voice control now runs in the tablet's own browser (see the Voice card in the settings)." ;;
        --with-wifi-setup) WIFI_SETUP=1 ;;
        --dry-run) DRY=1 ;;
        --hostname) NEW_HOSTNAME="${2:?--hostname needs a name}"; shift ;;
        --branch) BRANCH="${2:?--branch needs a name}"; shift ;;
        --source) SOURCE="${2:?--source needs a folder}"; shift ;;
        --prefix) PREFIX="${2:?}"; shift ;;
        --help|-h) sed -n '2,22p' "$0"; exit 0 ;;
        *) die "unknown option: $1 (try --help)" ;;
    esac
    shift
done

# ------------------------------------------------------------------ checks ---
if [ "$DRY" = 0 ] && [ "$(id -u)" != 0 ]; then
    die "please run with sudo:  curl -fsSL https://raw.githubusercontent.com/regis57/Beranda/main/install.sh | sudo bash"
fi
command -v apt-get >/dev/null || die "this installer needs a Debian-based system (Raspberry Pi OS, Debian, Ubuntu)"
if [ -n "$NEW_HOSTNAME" ] && ! [[ "$NEW_HOSTNAME" =~ ^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$ ]]; then
    die "the name must use lowercase letters, digits and dashes, e.g. beranda or mirror-kitchen"
fi

# ------------------------------------------------------------------ 1. packages ---
say "1/4 Installing system packages (this can take a few minutes on a Raspberry Pi)"
packages=(git curl python3 python3-venv python3-pip avahi-daemon fonts-noto-core fonts-noto-cjk)
if [ "$SCREEN" = 1 ]; then
    packages+=(cage wlr-randr)
    # Raspberry Pi OS calls its Chromium "chromium-browser"; Debian and Ubuntu call it "chromium".
    if apt-cache show chromium-browser >/dev/null 2>&1; then packages+=(chromium-browser); else packages+=(chromium); fi
fi
[ "$WIFI_SETUP" = 1 ] && packages+=(network-manager)
run apt-get update -q
run env DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends "${packages[@]}"

# ------------------------------------------------------------------ 2. user ---
say "2/4 Creating the '$USER_NAME' user"
if ! id "$USER_NAME" >/dev/null 2>&1; then
    run useradd --system --home-dir "$STATEDIR" --create-home --shell /usr/sbin/nologin "$USER_NAME"
fi
# video/render: draw on the screen; input: the touch screen, if any; audio: play radio.
for group in video render input audio; do
    if getent group "$group" >/dev/null; then run usermod -aG "$group" "$USER_NAME"; fi
done
run install -d -m 0750 -o "$USER_NAME" -g "$USER_NAME" "$CONFDIR" "$STATEDIR" "$STATEDIR/requests" "$STATEDIR/photos"

# ------------------------------------------------------------------ 3. Beranda ---
say "3/4 Installing Beranda in $PREFIX"
run install -d -m 0755 "$PREFIX" "$PREFIX/bin"
if [ -n "$SOURCE" ]; then
    run rm -rf "$PREFIX/src"
    run cp -a "$SOURCE" "$PREFIX/src"
elif [ -d "$PREFIX/src/.git" ]; then
    run git -C "$PREFIX/src" fetch --depth 1 origin "$BRANCH"
    run git -C "$PREFIX/src" reset --hard FETCH_HEAD
else
    run git clone --depth 1 --branch "$BRANCH" "$REPO" "$PREFIX/src"
fi
[ -d "$PREFIX/venv" ] || run python3 -m venv "$PREFIX/venv"
run "$PREFIX/venv/bin/pip" install --quiet --no-cache-dir --upgrade pip
run "$PREFIX/venv/bin/pip" install --quiet --no-cache-dir --upgrade "$PREFIX/src"
run install -m 0755 "$PREFIX/src/system/beranda-kiosk" "$PREFIX/bin/beranda-kiosk"
run install -m 0755 "$PREFIX/src/system/beranda-action" "$PREFIX/bin/beranda-action"
run install -m 0755 "$PREFIX/src/system/beranda-tidy" "$PREFIX/bin/beranda-tidy"
# keep a small SD card from filling up (caches, old versions, log size, swap file): see the script
run env PREFIX="$PREFIX" "$PREFIX/bin/beranda-tidy"
run ln -sf "$PREFIX/venv/bin/beranda" /usr/local/bin/beranda

commit="$(git -C "$PREFIX/src" rev-parse --short HEAD 2>/dev/null || echo local)"
if [ "$DRY" = 0 ]; then
    cat > "$CONFDIR/install.env" <<INFO
# Written by install.sh: where Beranda lives. Read by the update service.
PREFIX=$PREFIX
BRANCH=$BRANCH
USER=$USER_NAME
CONFDIR=$CONFDIR
STATEDIR=$STATEDIR
SCREEN=$SCREEN
COMMIT=$commit
INFO
    chmod 0644 "$CONFDIR/install.env"
fi

# ------------------------------------------------------------------ 4. services ---
if [ "$SYSTEMD" = 1 ]; then
    say "4/4 Starting Beranda now and at every boot"
    units=(beranda.service beranda-actions.path beranda-actions.service)
    [ "$SCREEN" = 1 ] && units+=(beranda-kiosk.service)
    [ "$WIFI_SETUP" = 1 ] && units+=(beranda-wifi-setup.service)
    for unit in "${units[@]}"; do
        if [ "$DRY" = 1 ]; then
            printf '    $ write /etc/systemd/system/%s\n' "$unit"
        else
            sed -e "s|@PREFIX@|$PREFIX|g" -e "s|@USER@|$USER_NAME|g" \
                -e "s|@CONFDIR@|$CONFDIR|g" -e "s|@STATEDIR@|$STATEDIR|g" \
                "$PREFIX/src/system/$unit.in" > "/etc/systemd/system/$unit"
        fi
    done
    run systemctl daemon-reload
    [ "$WIFI_SETUP" = 1 ] && run systemctl enable --now beranda-wifi-setup.service
    run systemctl enable --now beranda.service beranda-actions.path
    if [ "$SCREEN" = 1 ]; then
        run systemctl set-default graphical.target
        run systemctl enable beranda-kiosk.service
        run systemctl restart beranda-kiosk.service
    else
        run systemctl disable --now beranda-kiosk.service 2>/dev/null || true
    fi
else
    say "4/4 Skipping the services (--no-systemd): start it yourself with $PREFIX/venv/bin/beranda"
fi

if [ -n "$NEW_HOSTNAME" ]; then
    say "Renaming this computer to $NEW_HOSTNAME"
    run hostnamectl set-hostname "$NEW_HOSTNAME"
    run sed -i "s/^127\.0\.1\.1.*/127.0.1.1\t$NEW_HOSTNAME/" /etc/hosts
    run systemctl restart avahi-daemon
fi

# ------------------------------------------------------------------ done ---
name="$(hostname 2>/dev/null || echo raspberrypi)"
ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
# the port saved in the settings page ("Advanced user"), 8080 unless it was changed
port="$(sed -n '/^\[server\]/,/^\[/{s/^port *= *\([0-9]\{1,5\}\).*/\1/p}' "$CONFDIR/config.toml" 2>/dev/null | head -n 1)"
port="${port:-8080}"
echo
say "Beranda is installed."
echo "    On your phone or computer (same Wi-Fi), open the settings page:"
echo "        http://$name.local:$port/admin"
[ -n "$ip" ] && echo "        or http://$ip:$port/admin"
[ "$SCREEN" = 1 ] && echo "    The screen shows the same address and a QR code until you have saved the settings."
echo "    Something wrong? Run:  beranda doctor"
if [ "$WIFI_SETUP" = 1 ]; then
    echo
    say "Wi-Fi setup is ready."
    echo "    From now on, if this Pi ever boots with no Wi-Fi and no network cable plugged in,"
    echo "    it opens its own Wi-Fi network called \"Beranda setup\" for about 15 minutes."
    echo "    Join it from a phone (the screen shows how, with a QR code) and a page opens by"
    echo "    itself to pick your real Wi-Fi - no computer, keyboard or terminal needed."
fi
