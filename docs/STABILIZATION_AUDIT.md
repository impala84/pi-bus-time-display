# V8 stabilization audit

Date: 1 October 2026

## Fixed in the first audit pass

1. **Privileged requests could overwrite each other (critical).** Sleep, wake,
   brightness, update and service commands shared one request filename. Two
   requests arriving before systemd consumed the first silently lost one. The
   broker now uses atomic, ordered queue entries and drains the full queue. A
   failing entry no longer strands later requests. The legacy filename remains
   readable during upgrades.
2. **Web Queue and Details could become stale (high).** State received while an
   external BluOS input was visible returned before those views rendered. Both
   bounded views now stay current even while hidden.
3. **Roon broadcasts repeatedly performed synchronous config reads (medium).**
   Runtime configuration is cached for one second, collapsing several reads
   per broadcast into at most one without adding a timer or background task.
4. **Optional BluOS input discovery could disable all amplifier control
   (medium).** A player that rejects Capture browsing can now retain status and
   volume control with an empty input list.

## Next stabilization work

### High priority

- Add an acknowledgement model for backlight actions. GTK currently knows that
  a request was accepted, not that a `/sys/class/backlight` write succeeded.
  Expose requested and applied state plus the selected backlight device in
  diagnostics before making further wake-policy changes.
- Add a small display-policy module independent of GTK and cover manual sleep,
  scheduled wake, inactivity sleep and Roon takeover as transition-table
  tests. Current backend policy tests are useful, but GTK transition decisions
  remain embedded in the display class.
- Add a Raspberry Pi hardware acceptance script covering sleep/wake, brightness
  restoration, update-without-reboot and schedule boundaries. Raw touch and
  backlight behavior cannot be proven on the development Mac.

### Medium priority

- Split the Python HTTP handlers and the GTK display into focused modules. Both
  files now combine transport, policy, persistence and presentation, which
  increases regression risk.
- Protect mutable Python state consistently. Bus state uses a lock, while Home
  state, enabled services and configuration replacement rely on atomic object
  assignment/GIL behavior.
- Replace comma-separated input parsing in web forms with structured arrays.
  Home entity IDs are safe today, but free-form BluOS aliases containing `,`
  or `=` are ambiguous.
- Add integration tests for the reverse proxy, login/session expiry and config
  save/reload. Existing tests concentrate on pure policy and Roon state.

### Low priority

- Move synchronous static-file reads in the Node server to a startup cache.
- Add shell linting in CI for install/update/appliance scripts.
- Add bounded diagnostic visibility for the low-level touchscreen listener so
  device matching or input-group failures are visible without journal access.

## Verification baseline

- Python source and privileged helper compile successfully against the declared
  Python 3.11+ syntax (local host is Python 3.9, so the full Python suite must
  run in CI or on the Pi).
- Node syntax checks pass.
- All 13 Node tests pass.
- All shell scripts pass `bash -n`.
- Queue writes have focused tests for atomicity and rapid off/on preservation.

Hardware acceptance is still required before calling the sleep/wake path fully
verified.

