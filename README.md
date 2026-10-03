# Pi Home

A single-card Raspberry Pi home dashboard that combines **Roon Bridge**, Roon Now Playing, Singapore bus arrivals and selected Home Assistant controls on the official touchscreen.

Planned display automation, multi-service layouts, Touch Display 2 support and performance work are tracked in the [roadmap](ROADMAP.md).

The included configuration is ready for **Flamingo Valley, Siglap Road (83249)** and services **40 and 42**. It shows up to four adaptive, colour-separated service rows with three arrivals each. Automatic mode can move from Bus Times to Now Playing when music starts, retain it through a configurable pause, then return to buses—or sleep during overnight hours—while Roon Bridge continues running normally.

This deliberately replaces RoPieee. It does not try to fork or preserve RoPieee; the public RoPieee repository does not contain its full appliance build. If necessary, the card can simply be reflashed with RoPieee later.

## Install on the Pi

You need one microSD card (16 GB or larger) and an LTA DataMall AccountKey.

1. Register at [LTA DataMall](https://datamall.lta.gov.sg/) and obtain an AccountKey.
2. Flash **Raspberry Pi OS with desktop, 64-bit** using Raspberry Pi Imager. Configure Wi-Fi, timezone `Asia/Singapore`, a username and SSH in Imager's settings.
3. Boot the Pi, open a terminal and clone this repository.
4. Run `sudo ./scripts/install-pi.sh`.
5. Run `sudo ./scripts/install-roon-bridge.sh`. This uses Roon's official installer for the detected ARM architecture.
6. Put the LTA key in `/etc/pi-bus-time-display/secrets.env` and review `/etc/pi-bus-time-display/config.toml`.
7. Run `sudo pi-bus-appliance-mode enable` to replace the full desktop with the lightweight kiosk session.
8. Reboot. In the Roon app, open **Settings → Audio**, find this Raspberry Pi and enable its audio output. Then open **Settings → Extensions** and enable **Pi Home Roon Controller**.

The installer creates an unprivileged service account, keeps credentials outside the repository and launches a lightweight native GTK4 touchscreen. Chromium is not installed or used. The native application changes between Bus, Roon, Home, Settings and Sleep without browser loading screens, desktop flashes or keyring prompts. Roon's installer starts Roon Bridge at boot and manages its own updates.

## Web settings

From a phone or computer on the same network, open `http://<pi-address>:8765/admin`. The dedicated sign-in page uses username `admin` and the `ADMIN_PASSWORD` stored in `/etc/pi-bus-time-display/secrets.env`. Its ordinary username and password fields allow browsers and password managers to save and autofill the credentials; a successful sign-in lasts for 30 days. The touchscreen itself opens Settings directly.

The web admin is organised into **Schedule**, **Bus stop**, **Roon**, **Home** and **System**. It controls display schedules, stop and LTA credentials, Now Playing preferences, Roon Bridge start/stop/restart, the optional Home Assistant panel, device name, Wi-Fi and software updates. Web authentication can be renamed, reset or disabled under System; disabling it exposes every setting to the home network. Existing API keys, access tokens and Wi-Fi passwords are never displayed back to the browser. Because this admin server uses ordinary HTTP, keep it on a trusted home network and use authentication unless the network itself is trusted.

On the touchscreen, tap the title at top left for Settings and tap the clock at top right to sleep. The bottom navigation switches directly between **Now Playing**, **Bus Times** and the optional **Home** panel. Touchscreen Settings can start or stop Roon Bridge and temporarily show or hide configured buses; adding services and changing credentials remains protected in web administration. By default sleep powers off the display backlight; touch remains active, so tap anywhere to wake it.

### Home Assistant

Under web Settings → Home, enable the integration, enter the local Home Assistant address and a Long-Lived Access Token, then list up to eight entity IDs in display order. The Home touchscreen panel supports `fan`, `light`, `switch` and `input_boolean` entities in a fixed 4×2 grid. Tap a device icon to toggle it; supported lights and variable-speed fans also provide a vertical touch control for brightness or speed. Only those allow-listed entities can be controlled; locks, alarms, covers and other sensitive domains are deliberately rejected. The token is stored in `/etc/pi-bus-time-display/secrets.env` and is never sent to the touchscreen UI.

The installer generates a unique admin password and prints it once. You can retrieve or change it later in `/etc/pi-bus-time-display/secrets.env`.

### Connect the Roon controller

1. After installation, open **Roon → Settings → Extensions**.
2. Find **Pi Home Roon Controller** and choose **Enable**. This is the one-time authorisation required by Roon's extension API.
3. In Pi Bus Settings, optionally enter the exact Roon zone name. Leave it blank to follow the currently playing zone.

The controller shows album artwork rather than artist photography, track and artist text, elapsed/remaining progress, previous/play-pause/next controls, mute and volume. Its optional **Browse** view exposes Roon search and the live Roon library hierarchy in a touch-scrollable window while keeping both navigation rows fixed. Browse can be enabled or hidden under web **Settings → Roon & BluOS**. Long titles pause and scroll only when needed, and transport controls use consistent SVG artwork. If the selected output exposes no adjustable volume, it shows **Fixed volume** instead. Roon Server and the Pi must be on the same network.

### Connect an NAD / BluOS amplifier

Under web **Settings → Roon**, enable BluOS control and discover the player or enter its local hostname/IP address. Save once, then use **Load amplifier inputs** to choose exactly which live inputs appear in Pi Home and optionally give each one a shorter Pi Home display name such as “TV” or “Rega”. An empty initial selection shows every input. Enabled sources sit directly beside **Now Playing** and **Queue**, without a dropdown. Pi Home listens to BluOS status changes using the player's long-polling API rather than repeatedly polling it. When a physical input is active, its screen provides a large volume number, minus/plus controls and mute. Now Playing and Queue are view-only: browsing them leaves the physical source untouched, and pressing Play from Now Playing is the explicit action that makes Roon reclaim the zone.

## Updates

After the initial installation, update the appliance with one command:

```sh
sudo pi-bus-update
```

The updater follows the supported `main` branch, preserves any local checkout differences in a recoverable Git stash, reinstalls the application, reapplies saved display/input orientation, refreshes and verifies its services, then restarts the native touchscreen without rebooting the Pi. Already-installed operating-system components are not downloaded again. Touch Display 2 orientation updates its hardware touch overlay and requests one reboot only when that boot configuration actually changes. Updates can be started from the protected web System section or the restricted touchscreen Settings screen. Your settings and secrets remain untouched in `/etc/pi-bus-time-display/`. Both interfaces show live installation stages while an update is running. Releases use semantic versions, shown in Settings and recorded in [CHANGELOG.md](CHANGELOG.md). The current release is **v0.11.29**.

Display brightness is shared between touchscreen Settings and web Settings → System. It is applied through Linux's hardware backlight interface, persisted across reboots and limited to 10–100% so the panel cannot accidentally become unusable. The System page also reports the real `netdata.service` state when Netdata is installed and can enable/start or disable/stop that single service through Pi Home's existing fixed-action privileged broker; no general sudo access is granted. The same page can turn the Raspberry Pi ACT/PWR status lights on or off; they default to off, persist across reboots, and are reapplied by a one-shot boot service rather than a resident process.

## Lightweight appliance mode

The ordinary Raspberry Pi desktop is useful for initial setup but unnecessary in daily use. Enable the included Cage-based Wayland kiosk after installation:

```sh
sudo pi-bus-appliance-mode enable
sudo reboot
```

This boots to a minimal compositor running only Pi Bus, while networking, SSH, Roon Bridge and web administration continue normally. It disables the graphical desktop without uninstalling it, so recovery is simple:

```sh
sudo pi-bus-appliance-mode disable
sudo reboot
```

Check the current mode with `sudo pi-bus-appliance-mode status`.

Display orientation can be changed remotely under **Display → Screen hardware**. The original Touch Display retains its libinput calibration path. Touch Display 2 is natively portrait, so Pi Home rotates its Cage/Wayland output and configures the matching Raspberry Pi Device Tree touch axes; select the exact 5-, 7- or 10-inch model and reboot once after applying a new orientation. The same setting rotates the boot console. The native display hides its pointer without disabling input devices.

### Official touchscreen

Current Raspberry Pi OS releases normally detect the official display automatically. Set rotation in Screen Configuration if necessary before enabling appliance mode. Pi Bus manages backlight sleep itself.

## Configuration

Edit `/etc/pi-bus-time-display/config.toml`:

- `bus_stop_code`: LTA stop code (`83249`)
- `bus_stop_name`: heading shown on screen
- `services`: one or more service numbers; an empty list shows all returned services
- `walking_minutes`: time from home to the stop
- `poll_seconds`: defaults to 20 seconds, matching LTA's published refresh cadence
- `morning_start` and `morning_end`: touchscreen bus-display window
- `sleep_start` and `sleep_end`: automatic black-screen window
- `roon_zone_name`: exact preferred Roon zone; blank follows the playing zone
- `roon_display_name`: short name for the Roon section in touchscreen navigation
- `bluos_enabled`, `bluos_player_address` and `bluos_visible_inputs`: optional NAD/BluOS source and amplifier controls
- `sleep_when_roon_idle`: sleep outside the bus window unless the selected Roon zone is playing
- `auto_switch_to_roon`: let active playback temporarily take over Automatic mode
- `roon_idle_return_seconds`: delay before returning to buses after playback stops
- `outside_hours_wake_seconds`: how long a touch wake lasts during overnight hours
- `daytime_inactivity_seconds`: seconds without a touch before the display sleeps during the day; `0` disables it
- `home_assistant_enabled`, `home_assistant_url` and `home_assistant_entities`: optional Home panel connection and allow-list (the token remains in `secrets.env`)
- `openobserve_enabled`, `openobserve_url`, `openobserve_org`, `openobserve_stream` and `openobserve_username`: optional central operational logging; set the password through System settings or as `OPENOBSERVE_PASSWORD` in `secrets.env`

Restart after changes with `sudo systemctl restart pi-bus-time-display`.

## Try it without the Pi

Simulation needs no API key:

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
cp config.example.toml config.toml
.venv/bin/pi-bus-time-display --simulate
```

Open <http://127.0.0.1:8765>. For live data, copy `.env.example` to `.env`, add the AccountKey and start without `--simulate`.

This is also the quickest design-preview loop: leave simulation running, refresh the browser after a code change, and no Raspberry Pi rebuild is needed.

## Reliability and privacy

The browser never receives the LTA key. If LTA or the network fails, the display retains the last successful arrivals and marks them offline/stale. The backend validates configuration, floors arrival minutes following LTA's published guidance, and polls no faster than configured.

Roon Bridge uses ALSA directly and runs independently of the GTK display. The controller uses Roon's official extension services for transport, volume and artwork, and listens only on the Pi's loopback interface. Raspberry Pi OS 64-bit uses Roon's supported ARMv8 build; the helper selects ARMv7 only on a 32-bit system.

## Tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Sources

- [LTA DataMall API guide](https://datamall.lta.gov.sg/content/dam/datamall/datasets/LTA_DataMall_API_User_Guide.pdf) — Bus Arrival v3 fields, 20-second update frequency and rounding guidance.
- [Roon's Linux installation guide](https://help.roonlabs.com/portal/en/kb/articles/linux-install) — official ARMv8/ARMv7 installers and service behaviour.
- [Roon system requirements](https://help.roonlabs.com/portal/en/kb/articles/faq-what-are-the-minimum-requirements) — current Raspberry Pi OS support for Roon Bridge.
- [Roon JavaScript API](https://github.com/RoonLabs/node-roon-api) — official extension pairing and service API.
- [Roon transport API](https://github.com/RoonLabs/node-roon-api-transport) — zone metadata, playback, seek and volume controls.
- [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/) — authenticated entity state and service calls.

## Licence

MIT
