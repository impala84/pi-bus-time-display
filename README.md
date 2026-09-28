# Pi Bus Time Display

A single-card Raspberry Pi appliance that runs **Roon Bridge all day**, turns the official touchscreen into a highly legible Singapore bus display each morning, then returns it to Roon Now Playing.

The included configuration is ready for **Flamingo Valley, Siglap Road (83249)** and services **40 and 42**. From 06:00–10:00 it shows two large, colour-separated service rows with three arrivals each. Outside that window it shows a custom Roon controller with album artwork, metadata, progress, playback and volume controls while Roon Bridge continues running normally.

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
8. Reboot. In the Roon app, open **Settings → Audio**, find this Raspberry Pi and enable its audio output. Then open **Settings → Extensions** and enable **Pi Bus Roon Controller**.

The bus installer creates an unprivileged service account, keeps the LTA key outside the repository and launches a lightweight native GTK4 touchscreen. Chromium is not installed or used. The native application changes between Bus, Roon, Settings and Sleep without browser loading screens, desktop flashes or keyring prompts. Roon's installer starts Roon Bridge at boot and manages its own updates.

## Web settings

From a phone or computer on the same network, open `http://<pi-address>:8765/admin`. The dedicated sign-in page uses username `admin` and the `ADMIN_PASSWORD` stored in `/etc/pi-bus-time-display/secrets.env`. Its ordinary username and password fields allow browsers and password managers to save and autofill the credentials; a successful sign-in lasts for 30 days. The touchscreen itself opens Settings directly.

The web admin is organised into **Schedule**, **Bus stop**, **Roon** and **System**. It controls display schedules, stop and LTA credentials, Now Playing preferences, Roon Bridge start/stop/restart, device name, Wi-Fi and software updates. Web authentication can be renamed, reset or disabled under System; disabling it exposes every setting to the home network. The existing AccountKey and Wi-Fi password are never displayed back to the browser. Because this admin server uses ordinary HTTP, keep it on a trusted home network and use authentication unless the network itself is trusted.

On the touchscreen, tap the title at top left for Settings and tap the clock at top right to sleep. The bottom navigation switches directly between **Now Playing** and **Bus Times**. By default sleep powers off the display backlight; touch remains active, so tap anywhere to wake it. Enable **Show clock while sleeping** under Schedule if you prefer a black clock screen instead. Touchscreen Settings intentionally exposes only safe status and update controls; schedules, credentials, bus configuration, Roon service control and network settings remain in the authenticated web admin.

The installer generates a unique admin password and prints it once. You can retrieve or change it later in `/etc/pi-bus-time-display/secrets.env`.

### Connect the Roon controller

1. After installation, open **Roon → Settings → Extensions**.
2. Find **Pi Bus Roon Controller** and choose **Enable**. This is the one-time authorisation required by Roon's extension API.
3. In Pi Bus Settings, optionally enter the exact Roon zone name. Leave it blank to follow the currently playing zone.

The controller shows album artwork rather than artist photography, track and artist text, elapsed/remaining progress, previous/play-pause/next controls, mute and volume. Long titles use a restrained two-line treatment rather than scrolling, and transport controls use consistent SVG artwork. If the selected output exposes no adjustable volume, it shows **Fixed volume** instead. Roon Server and the Pi must be on the same network.

## Updates

After the initial installation, update the appliance with one command:

```sh
sudo pi-bus-update
```

The updater follows the supported `main` branch, preserves any local checkout differences in a recoverable Git stash, reinstalls the application, refreshes its services, verifies both HTTP services and reboots automatically. Updates can be started from the protected web System section or the restricted touchscreen Settings screen. Your settings and secrets remain untouched in `/etc/pi-bus-time-display/`. Releases use semantic versions, shown in Settings and recorded in [CHANGELOG.md](CHANGELOG.md). The GTK preview is **v0.3.0rc8**.

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

Display orientation can be changed remotely under **System → Display**. The setting coordinates kernel-console and Wayland rotation, so both the operating-system boot screen and Pi Bus use the same orientation after reboot. The equivalent recovery command is `sudo pi-bus-appliance-mode rotate 180`; use `normal` instead of `180` to turn rotation off.

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
- `sleep_when_roon_idle`: sleep outside the bus window unless the selected Roon zone is playing

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

## Licence

MIT
