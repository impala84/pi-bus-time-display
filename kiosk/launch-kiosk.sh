#!/usr/bin/env bash
set -u

shell_url=http://127.0.0.1:8765/display-shell.html
browser_pid=

stop_browser() {
  if [[ -n ${browser_pid} ]] && kill -0 "${browser_pid}" 2>/dev/null; then
    kill "${browser_pid}" 2>/dev/null || true
    wait "${browser_pid}" 2>/dev/null || true
  fi
}
trap stop_browser EXIT TERM INT

sleep 8
while true; do
  if [[ -z ${browser_pid} ]] || ! kill -0 "${browser_pid}" 2>/dev/null; then
    chromium --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble \
      --password-store=basic --use-mock-keychain --disable-features=TranslateUI \
      --user-data-dir="${HOME}/.config/pi-bus-kiosk" "${shell_url}" &
    browser_pid=$!
  fi
  sleep 5
done
