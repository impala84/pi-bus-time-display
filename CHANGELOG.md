# Changelog

## 0.4.1 — 29 September 2026

- Removed expensive System and Wi-Fi diagnostics from the touchscreen's two-second display loop.
- Refresh configuration once per minute and System status only while touchscreen Settings is open.
- Replaced repeated Wi-Fi network listings with a lightweight active-connection query.
- Added swap use, SoC temperature and Raspberry Pi throttling state to diagnostics.

## 0.4.0 — 29 September 2026

- Added Automatic-mode Roon playback takeover with a configurable stopped-playing return delay.
- Added a configurable temporary wake timeout outside regular waking hours.
- Added adaptive two-, three- and four-service bus layouts without display scrolling.
- Added read-only live memory, load, uptime and per-component process diagnostics to System settings.
- Added selectable original Touch Display and Touch Display 2 resolution profiles with all four orientations.
- Added higher-resolution GTK scaling for Touch Display 2 while preserving the known-good original-display path.

## 0.3.0-rc.13 — 29 September 2026

- Removed the duplicate Wayland output transform that flipped the final display after the kernel had already rotated it.
- Made the kernel the sole picture-orientation authority and kept touchscreen calibration as a separate, matching libinput matrix.
- Hid the pointer directly in the native GTK display instead of disabling mouse-class input devices.

## 0.3.0-rc.12 — 29 September 2026

- Kept the last valid album cover through brief incomplete Roon metadata updates between tracks.
- Clear stale artwork only after five consecutive polls genuinely contain no artwork.

## 0.3.0-rc.11 — 29 September 2026

- URL-encoded Roon image keys so artwork containing reserved URL characters loads reliably.
- Reset the native artwork cache when playback or artwork disappears, allowing the same cover to load again when playback resumes.

## 0.3.0-rc.10 — 29 September 2026

- Made updates automatically reapply the saved display and touchscreen orientation before rebooting.

## 0.3.0-rc.9 — 29 September 2026

- Rotated touchscreen coordinates alongside the 180° display using libinput's calibration matrix.
- Suppressed non-touch pointer devices in appliance mode so Cage removes the mouse cursor.
- Strengthened physical display sleep with repeated backlight requests and the Raspberry Pi display-power fallback.

## 0.3.0-rc.8 — 29 September 2026

- Extended the display-orientation setting to the Raspberry Pi kernel console so the boot splash and GTK kiosk share the same orientation.
- Preserve the original kernel command line as `cmdline.txt.pi-bus-backup` before changing it.

## 0.3.0-rc.7 — 29 September 2026

- Added persistent appliance-mode display rotation with a simple 180° switch under System → Display.
- Added a command-line rotation recovery option and made 180° the initial appliance-mode orientation for this touchscreen mounting.

## 0.3.0-rc.6 — 29 September 2026

- Made software updates reboot automatically after successful service verification.
- Made sleep physically power down the official touchscreen backlight, while retaining touch-to-wake and the optional clock mode.
- Added a reversible Cage-based appliance mode that boots Pi Bus without loading the Raspberry Pi desktop.
- Replaced bottom navigation panels with understated active-view underlines.
- Reduced and re-centred album artwork and improved spacing around the transport controls.

## 0.3.0-rc.5 — 29 September 2026

- Distinguished the Now Playing controller from the Roon Bridge audio endpoint in web administration.
- Added clear Roon authorisation guidance and separate unavailable, unauthorised and idle states on the touchscreen.
- Refined the Now Playing split layout, artwork spacing, circular transport controls and bottom navigation emphasis.
- Made the native progress timeline touch-seekable, with debouncing and automatic disabling for non-seekable material.
- Added a Pi Bus favicon to web administration.

## 0.3.0-rc.4 — 29 September 2026

- Replaced raw command exceptions on touchscreen system actions with concise, useful failure messages while retaining full output in the service log.

## 0.3.0-rc.3 — 29 September 2026

- Made appliance updates preserve local checkout differences automatically instead of failing when an installed file has changed.
- Made installed appliances follow the supported `main` branch after the native GTK build became the primary release.

## 0.3.0-rc.2 — 29 September 2026

- Matched the native display typography to the Inter-based web administration and installed Inter automatically.
- Replaced visible main-screen utility buttons with large invisible title and clock touch targets.
- Removed page-transition animation and softened borders, status text and navigation chrome.
- Aligned and enlarged bus service and arrival figures on a shared baseline.
- Restored circular symbolic Roon transport controls and improved connected-but-idle wording.
- Added an optional completely black sleep screen while retaining tap-anywhere wake.

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
