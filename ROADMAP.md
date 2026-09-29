# Roadmap

This roadmap records intended improvements without promising a release date. Reliability on the installed Raspberry Pi remains the first priority.

## Display automation

- Automatically switch from Bus Times to Now Playing when the selected Roon zone starts playing.
- After playback stops or pauses, return to Bus Times after a configurable delay.
- Make the return delay configurable and distinguish a brief pause from genuinely finished listening.
- Add a configurable inactivity timeout for manually awakened screens outside normal waking hours.
- Keep the display awake while it is being touched or while relevant Roon playback is active.
- Add configurable sleep duration and clearer schedule precedence between manual choices, bus hours, playback and overnight sleep.

## Bus layout

- Support three or more configured services without scrolling the appliance display.
- Adapt row height, type size and spacing to the number of visible services while preserving across-the-room legibility.
- Retain the current spacious two-service layout when only services 40 and 42 are selected.
- Add a preview for two-, three- and four-service layouts before enabling them on the device.

## Touch Display 2

- Detect the connected DSI panel and its native resolution instead of assuming the original `800×480` Touch Display.
- Add profiles for the 5-inch and 7-inch Touch Display 2 (`720×1280`) and the 10-inch model (`1200×1920`).
- Make landscape orientation, touchscreen calibration, boot-console rotation and physical sleep work as one tested configuration for each panel.
- Scale typography, artwork, controls and touch targets from the actual display size and pixel density.
- Preserve a recovery path if a display change produces an unusable orientation.

## Performance and diagnostics

- Add a lightweight System diagnostics panel showing total and available memory, process memory, CPU use, uptime and service status.
- Measure the Python API, GTK/Cage display, Node Roon controller and Roon Bridge separately before removing components.
- Review whether the Roon controller can be consolidated or started on demand without harming playback detection or reliability.
- Continue running without the Raspberry Pi desktop and avoid Chromium, keyrings and unnecessary background services.
- Document a repeatable before-and-after performance baseline for supported Pi models.

