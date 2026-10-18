#!/usr/bin/env bash
# Remove Beranda. Your settings in /etc/beranda are kept unless you add --purge.
#   sudo /opt/beranda/src/uninstall.sh [--purge]
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Please run with sudo." >&2; exit 1; }
PURGE=0; [ "${1:-}" = "--purge" ] && PURGE=1
# Beranda lives where this script's own copy of the code sits ($PREFIX/src/uninstall.sh), or
# in the usual place when run from elsewhere. install.env is deliberately not read: it may sit in
# /etc/beranda, which the web server can write, and the folder named here is deleted as root.
PREFIX="/opt/beranda"
here="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
if [ -f "$here/install.env" ] || [ -x "$here/bin/beranda-action" ]; then PREFIX="$here"; fi

for unit in beranda-wifi-setup.service beranda-kiosk.service beranda.service beranda-actions.path beranda-actions.service; do
    systemctl disable --now "$unit" 2>/dev/null || true
    rm -f "/etc/systemd/system/$unit"
done
systemctl daemon-reload
rm -f /etc/NetworkManager/dnsmasq-shared.d/beranda-captive.conf
rm -rf "$PREFIX" /usr/local/bin/beranda
if [ "$PURGE" = 1 ]; then
    rm -rf /etc/beranda /var/lib/beranda
    userdel beranda 2>/dev/null || true
    echo "Beranda and its settings are removed."
else
    echo "Beranda is removed. Your settings are kept in /etc/beranda (remove them with --purge)."
fi
echo "The system packages (Chromium, Cage, fonts) are left installed."
