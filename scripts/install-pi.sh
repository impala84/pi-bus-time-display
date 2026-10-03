#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Run with sudo: sudo ./scripts/install-pi.sh"
  exit 1
fi

SOURCE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
apt-get update
apt-get install -y git nodejs npm python3-venv python3-gi python3-gi-cairo gir1.2-gtk-4.0 fonts-inter avahi-utils wlr-randr grim
id morningbus >/dev/null 2>&1 || useradd --create-home --shell /bin/bash morningbus
install -d -o morningbus -g morningbus /opt/pi-bus-time-display /etc/pi-bus-time-display /var/lib/pi-bus-time-display /var/lib/pi-bus-time-display/roon
cp -a "${SOURCE_DIR}/." /opt/pi-bus-time-display/
python3 -m venv --system-site-packages /opt/pi-bus-time-display/.venv
/opt/pi-bus-time-display/.venv/bin/pip install --no-deps /opt/pi-bus-time-display
npm --prefix /opt/pi-bus-time-display/roon-controller ci --omit=dev --no-audit --no-fund
sha256sum /opt/pi-bus-time-display/roon-controller/package-lock.json | cut -d' ' -f1 >/var/lib/pi-bus-time-display/roon-package-lock.sha256
chmod 0644 /var/lib/pi-bus-time-display/roon-package-lock.sha256
[[ -f /etc/pi-bus-time-display/config.toml ]] || install -m 0640 -o morningbus -g morningbus /opt/pi-bus-time-display/config.example.toml /etc/pi-bus-time-display/config.toml
[[ -f /etc/pi-bus-time-display/secrets.env ]] || install -m 0600 -o morningbus -g morningbus /opt/pi-bus-time-display/.env.example /etc/pi-bus-time-display/secrets.env
[[ -f /etc/pi-bus-time-display/roon.env ]] || install -m 0640 -o morningbus -g morningbus /dev/null /etc/pi-bus-time-display/roon.env
if grep -q '^ADMIN_PASSWORD=change-me-now$' /etc/pi-bus-time-display/secrets.env; then
  admin_password=$(openssl rand -hex 8)
  sed -i "s/^ADMIN_PASSWORD=change-me-now$/ADMIN_PASSWORD=${admin_password}/" /etc/pi-bus-time-display/secrets.env
  echo "Web settings password: ${admin_password}"
fi
install -m 0644 /opt/pi-bus-time-display/systemd/*.service /etc/systemd/system/
install -m 0644 /opt/pi-bus-time-display/systemd/*.path /etc/systemd/system/
install -m 0755 /opt/pi-bus-time-display/scripts/pi-bus-update /usr/local/sbin/pi-bus-update
install -m 0755 /opt/pi-bus-time-display/scripts/pi-bus-system-action /usr/local/sbin/pi-bus-system-action
install -m 0755 /opt/pi-bus-time-display/scripts/pi-bus-appliance-mode /usr/local/sbin/pi-bus-appliance-mode
desktop_user=${SUDO_USER:-}
if [[ -z ${desktop_user} || ${desktop_user} == root ]]; then
  echo "Run this installer with sudo from the Raspberry Pi desktop user."
  exit 1
fi
desktop_home=$(getent passwd "${desktop_user}" | cut -d: -f6)
install -d -o "${desktop_user}" -g "${desktop_user}" "${desktop_home}/.config/autostart"
install -m 0644 -o "${desktop_user}" -g "${desktop_user}" /opt/pi-bus-time-display/native-display/pi-bus-native.desktop "${desktop_home}/.config/autostart/pi-bus-native.desktop"
rm -f "${desktop_home}/.config/autostart/pi-bus-time-display.desktop"
chmod 0755 /opt/pi-bus-time-display/native-display/pi_bus_native.py
chmod 0755 /opt/pi-bus-time-display/scripts/pi-bus-cage-launch
usermod -a -G morningbus "${desktop_user}"
systemctl daemon-reload
systemctl enable pi-bus-time-display.service
systemctl enable pi-bus-roon-controller.service
systemctl enable --now pi-bus-system-action.path
systemctl enable --now pi-home-leds.service
echo "Installed native GTK display. Edit /etc/pi-bus-time-display/config.toml and /etc/pi-bus-time-display/secrets.env, then reboot."
echo "Future application updates: sudo pi-bus-update"
