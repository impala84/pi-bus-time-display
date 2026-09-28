# Pi Bus Time Display

A single-card Raspberry Pi appliance that runs **Roon Bridge all day**, turns the official touchscreen into a highly legible Singapore bus display each morning, then returns it to Roon Now Playing.

The included configuration is ready for **Flamingo Valley, Siglap Road (83249)** and services **40, 42 and 401**. From 06:00–10:00 it shows the next useful bus, three arrivals per service and a walking-time-aware **LEAVE IN / LEAVE NOW** instruction. Outside that window it shows Roon's browser-based Now Playing display while Roon Bridge continues running normally.

This deliberately replaces RoPieee. It does not try to fork or preserve RoPieee; the public RoPieee repository does not contain its full appliance build. If necessary, the card can simply be reflashed with RoPieee later.

## Install on the Pi

You need one microSD card (16 GB or larger) and an LTA DataMall AccountKey.

1. Register at [LTA DataMall](https://datamall.lta.gov.sg/) and obtain an AccountKey.
2. Flash **Raspberry Pi OS with desktop, 64-bit** using Raspberry Pi Imager. Configure Wi-Fi, timezone `Asia/Singapore`, a username and SSH in Imager's settings.
3. Boot the Pi, open a terminal and clone this repository.
4. Run `sudo ./scripts/install-pi.sh`.
5. Run `sudo ./scripts/install-roon-bridge.sh`. This uses Roon's official installer for the detected ARM architecture.
6. Put the LTA key in `/etc/pi-bus-time-display/secrets.env` and review `/etc/pi-bus-time-display/config.toml`.
7. Reboot. In the Roon app, open **Settings → Audio**, find this Raspberry Pi and enable its audio output.

The bus installer creates an unprivileged service account, keeps the LTA key outside the repository, restarts the data service after failures and launches Chromium full-screen in the configured Raspberry Pi desktop session. Roon's installer starts Roon Bridge at boot and manages its own updates.

## Web settings

From a phone or computer on the same network, open `http://<pi-address>:8765/admin`. Sign in with username `admin` and the `ADMIN_PASSWORD` stored in `/etc/pi-bus-time-display/secrets.env`.

The settings page also acts as a remote control. Choose **Automatic**, **Bus times**, **Roon Now Playing**, or **Sleep display** to switch the touchscreen within about five seconds. A manual selection remains active until you return it to Automatic. You can also change the stop code and name, tracked services, walking time, display window, polling interval, Roon Display URL and LTA AccountKey. Changes take effect without rebooting. The existing AccountKey is never displayed back to the browser. Because this small admin server uses ordinary HTTP, keep it on a trusted home network and choose a unique password.

On the touchscreen, tap **SETTINGS** in the top-right corner. The same control appears over Roon Now Playing, so no address or keyboard is needed. **Sleep display** makes the screen black while leaving Roon Bridge and the bus service running; tap the discreet **WAKE** target in the bottom-right corner to return to Settings. Local touchscreen access opens directly, while access from another device still requires the admin password.

The installer generates a unique admin password and prints it once. You can retrieve or change it later in `/etc/pi-bus-time-display/secrets.env`.

### Connect Roon Now Playing

1. In the Roon app, open **Settings → Displays** and copy the Web Display URL. It normally resembles `http://<roon-server-address>:9330/display/`; do not use `127.0.0.1` because that refers to the Pi itself.
2. Paste that URL into the Pi Bus web settings page.
3. When the Pi browser appears in Roon, associate it with the Pi's audio zone and choose **Start On Playback**.

Roon documents browser displays as a supported way to show Now Playing information and lyrics. The Roon Server and Pi must be able to reach each other on the same network.

## Updates

After the initial installation, update the appliance with one command:

```sh
sudo pi-bus-update
```

The updater accepts only a fast-forward update from the configured GitHub repository, reinstalls the application, refreshes its service definition and restarts it. Your settings and secrets remain untouched in `/etc/pi-bus-time-display/`. If the kiosk has cached an older screen, refresh it or reboot once.

### Official touchscreen

Current Raspberry Pi OS releases normally detect the official display automatically. Set rotation in Screen Configuration if necessary, and disable screen blanking under Raspberry Pi Configuration.

## Configuration

Edit `/etc/pi-bus-time-display/config.toml`:

- `bus_stop_code`: LTA stop code (`83249`)
- `bus_stop_name`: heading shown on screen
- `services`: one or more service numbers; an empty list shows all returned services
- `walking_minutes`: time from home to the stop
- `poll_seconds`: defaults to 20 seconds, matching LTA's published refresh cadence
- `morning_start` and `morning_end`: touchscreen bus-display window

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

Roon Bridge uses ALSA directly and runs independently of the Chromium display. Raspberry Pi OS 64-bit uses Roon's supported ARMv8 build; the helper selects ARMv7 only on a 32-bit system.

## Tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Sources

- [LTA DataMall API guide](https://datamall.lta.gov.sg/content/dam/datamall/datasets/LTA_DataMall_API_User_Guide.pdf) — Bus Arrival v3 fields, 20-second update frequency and rounding guidance.
- [Roon's Linux installation guide](https://help.roonlabs.com/portal/en/kb/articles/linux-install) — official ARMv8/ARMv7 installers and service behaviour.
- [Roon system requirements](https://help.roonlabs.com/portal/en/kb/articles/faq-what-are-the-minimum-requirements) — current Raspberry Pi OS support for Roon Bridge.
- [Roon Displays](https://help.roonlabs.com/portal/en/kb/articles/displays) — supported browser-based Now Playing displays and zone association.

## Licence

MIT
