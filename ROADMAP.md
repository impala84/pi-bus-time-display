# Roadmap

This roadmap records intended improvements without promising a release date. Reliability on the installed Raspberry Pi remains the first priority.

## Delivered in v0.4.0

- Automatic Roon playback takeover, configurable return delay and temporary overnight touch wake.
- Adaptive, non-scrolling two-, three- and four-service bus layouts.
- Original Touch Display and Touch Display 2 resolution/orientation profiles.
- Live system and per-component memory, CPU, load and uptime diagnostics.

## Further display automation

- Consider separate paused and stopped delays if real-world playback behaviour shows that one grace period is insufficient.
- Add optional touch-activity extension while a temporary overnight wake is active.

## Further bus layout

- Add web previews for two-, three- and four-service layouts before enabling them on the device.

## Further Touch Display 2 work

- Validate the new profiles on physical 5-, 7- and 10-inch panels and refine their scaling from photographs.
- Investigate reliable panel auto-detection without jeopardising the current display's known-good boot rotation.
- Preserve a recovery path if a display change produces an unusable orientation.

## Performance and diagnostics

- Measure the Python API, GTK/Cage display, Node Roon controller and Roon Bridge separately before removing components.
- Review whether the Roon controller can be consolidated or started on demand without harming playback detection or reliability.
- Continue running without the Raspberry Pi desktop and avoid Chromium, keyrings and unnecessary background services.
- Document a repeatable before-and-after performance baseline for supported Pi models.
