# Changelog

## 0.3.0-rc.1 — 29 September 2026

- Replaced the Chromium kiosk with a lightweight native GTK4 touchscreen.
- Added persistent Bus Times and Now Playing navigation, corner Settings and Sleep actions, and tap-anywhere wake.
- Added a restricted touchscreen settings screen with safe, one-tap software updates.
- Restored native Roon artwork, progress, playback and volume controls.
- Reorganised web administration into Schedule, Bus Stop, Roon and System sections.
- Added authenticated Roon Bridge controls, hostname, Wi-Fi and software-update actions.
- Added configurable web username/password management and optional authentication.

## 0.2.1 — 28 September 2026

- Prevented Chromium from launching before the main display service responds.
- Changed Chromium's initial background to black so startup cannot flash a white page.
- Made the updater wait for and verify both HTTP services, printing their logs on failure.

## 0.2.0 — 28 September 2026

- Replaced the bus summary panel with two much larger service rows.
- Added a proper password-manager-compatible admin login page.
- Added a persistent display shell for seamless Bus, Roon and Sleep switching.
- Added a dark, automatically recovering screen when the Roon controller is unavailable.
- Made the Roon service create its own working directory and report startup failures during updates.
- Changed Roon dependencies to immutable public HTTPS downloads.
- Added optional sleep while Roon is idle, waking automatically for playback.
- Refined Roon typography, transport icons and control shapes.

## 0.1.0 — 28 September 2026

- Initial Raspberry Pi bus display, web settings, kiosk service and Roon integration.
