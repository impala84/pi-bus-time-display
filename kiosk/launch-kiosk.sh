#!/usr/bin/env bash
set -u

config=/etc/pi-bus-time-display/config.toml
bus_url=http://127.0.0.1:8765/
sleep_url=http://127.0.0.1:8765/sleep.html
extension_dir=/opt/pi-bus-time-display/kiosk/touch-controls
active_url=
browser_pid=

choose_url() {
  python3 - "${config}" "${bus_url}" "${sleep_url}" <<'PY'
import sys, tomllib
from datetime import datetime, time
from zoneinfo import ZoneInfo

path, bus_url, sleep_url = sys.argv[1:]
with open(path, "rb") as handle:
    config = tomllib.load(handle)
now = datetime.now(ZoneInfo(config.get("timezone", "Asia/Singapore"))).time()
start = time.fromisoformat(config.get("morning_start", "06:00"))
end = time.fromisoformat(config.get("morning_end", "10:00"))
roon_url = config.get("roon_display_url", "").strip()
try:
    mode = open("/var/lib/pi-bus-time-display/display-mode", encoding="utf-8").read().strip()
except OSError:
    mode = "auto"
if mode == "bus":
    print(bus_url)
elif mode == "sleep":
    print(sleep_url)
elif mode == "roon" and roon_url:
    print(roon_url)
else:
    print(bus_url if start <= now < end or not roon_url else roon_url)
PY
}

stop_browser() {
  if [[ -n ${browser_pid} ]] && kill -0 "${browser_pid}" 2>/dev/null; then
    kill "${browser_pid}" 2>/dev/null || true
    wait "${browser_pid}" 2>/dev/null || true
  fi
}
trap stop_browser EXIT TERM INT

sleep 8
while true; do
  wanted_url=$(choose_url 2>/dev/null || printf '%s\n' "${bus_url}")
  if [[ ${wanted_url} != "${active_url}" ]] || [[ -z ${browser_pid} ]] || ! kill -0 "${browser_pid}" 2>/dev/null; then
    stop_browser
    chromium --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble \
      --disable-extensions-except="${extension_dir}" --load-extension="${extension_dir}" \
      --user-data-dir="${HOME}/.config/pi-bus-kiosk" "${wanted_url}" &
    browser_pid=$!
    active_url=${wanted_url}
  fi
  sleep 5
done
