#!/usr/bin/env bash
# Remove Beranda. Your settings in /etc/beranda are kept unless you add --purge.
#   sudo /opt/beranda/src/uninstall.sh [--purge]
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Please run with sudo." >&2; exit 1; }
PURGE=0; [ "${1:-}" = "--purge" ] && PURGE=1
PREFIX="/opt/beranda"
# shellcheck source=/dev/null
[ -f /etc/beranda/install.env ] && source /etc/beranda/install.env

for unit in beranda-voice.service beranda-kiosk.service beranda.service beranda-actions.path beranda-actions.service; do
    systemctl disable --now "$unit" 2>/dev/null || true
    rm -f "/etc/systemd/system/$unit"
done
systemctl daemon-reload
rm -rf "$PREFIX" /usr/local/bin/beranda
if [ "$PURGE" = 1 ]; then
    rm -rf /etc/beranda /var/lib/beranda
    userdel beranda 2>/dev/null || true
    echo "Beranda and its settings are removed."
else
    echo "Beranda is removed. Your settings are kept in /etc/beranda (remove them with --purge)."
fi
echo "The system packages (Chromium, Cage, fonts) are left installed."
