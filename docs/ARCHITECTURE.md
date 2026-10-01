# Pi Home runtime architecture

This document records the supported runtime boundaries for the V8 line. It is
intentionally brief: each component should have one clear authority and avoid
duplicating state owned elsewhere.

## Components

| Component | Authority | Update model |
| --- | --- | --- |
| Python service (`:8765`) | configuration, bus data, Home Assistant allow-list, schedule policy, web administration | LTA at the configured interval; Home Assistant every 3 seconds |
| Roon/BluOS controller (`127.0.0.1:8766`) | Roon subscription state, queue, metadata, artwork cache and amplifier state | Roon subscriptions and BluOS long polling |
| Native GTK display | presentation, touch activity and local view selection | compact state refresh every 2 seconds; network and image work off the GTK thread |
| Privileged action broker | backlight, update, systemd services, display setup and Pi LEDs | systemd path activation; no resident privileged process |

The browser dashboard reaches Roon through the Python reverse proxy. The Node
controller remains loopback-only. The GTK display talks to both loopback
services directly.

## Display state

The persisted display mode is one of `auto`, `bus`, `roon`, `home` or `sleep`.
The Python service resolves it to a target using the schedule, recent Roon
playback and the temporary wake deadline. A manual mode expires at the next
schedule-period boundary. Explicit `sleep` is cleared on a backend restart so
an interrupted update cannot strand the panel black.

Daytime inactivity is intentionally local to GTK because it is driven by real
touch activity. Scheduled sleep remains authoritative. A scheduled wake resets
the inactivity clock before the next inactivity decision.

Backlight changes are privileged actions. Each action is stored as its own
atomic queue entry and consumed in filename order. The old single request file
is accepted only for upgrade compatibility.

## Roon and BluOS

Roon owns Now Playing, Queue and artwork. Queue subscription begins when the
zone is established and stays in memory. BluOS owns physical input selection,
amplifier volume and mute. Opening Now Playing or Queue is view-only; selecting
a physical source changes the amplifier. Pressing Play is the explicit action
that may reclaim the Roon source.

## Threading rule

GTK construction and mutation run only on the GTK main thread. HTTP, image
downloads and raw input reads run in workers and return through `GLib.idle_add`.
The Python web server uses one thread per request. Privileged actions never run
inside either application service.

