#!/usr/bin/env python3
"""Native GTK4 touchscreen for Pi Home."""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk

BUS = "http://127.0.0.1:8765"
ROON = "http://127.0.0.1:8766"
TZ = ZoneInfo("Asia/Singapore")

CSS = b"""
window { background: #0b1110; color: #f4f0e6; font-family: Inter, Cantarell, sans-serif; }
button { border: 0; box-shadow: none; background-image: none; outline: none; }
.page { padding: 14px 20px 10px; }.eyebrow { color: #97a39f; font-size: 11px; font-weight: 700; letter-spacing: 2px; }
.clock { font-size: 31px; font-weight: 600; }.stop { font-size: 25px; font-weight: 700; }.stop-code { color: #7f8b87; font-size: 25px; font-weight: 550; }
.header-hotspot { min-height: 42px; padding: 0; border: 0; box-shadow: none; background: transparent; background-image: none; }
.header-hotspot:hover, .header-hotspot:active { background: transparent; box-shadow: none; }
.header-title { padding-left: 0; }.header-clock { padding-right: 0; }
.utility { min-width: 92px; min-height: 38px; border-radius: 7px; background: #18211f; color: #d9dedb; font-size: 11px; font-weight: 750; }
.service { background: #131c1a; border: 1px solid #26312e; border-radius: 14px; padding: 5px 16px; }
.service-blue { border-color: #28566e; background: #112027; }.service-green { border-color: #285e43; background: #102219; }
.service-violet { border-color: #554a77; background: #1d1929; }.service-amber { border-color: #75572a; background: #271e11; }
.service-no, .arrival { font-size: 82px; font-weight: 720; font-variant-numeric: tabular-nums; }
.service-no { font-weight: 760; }.service-blue .service-no { color: #55a9d7; }.service-green .service-no { color: #61c68f; }.service-violet .service-no { color: #a998e0; }.service-amber .service-no { color: #d4a85f; }
.service.compact .service-no, .service.compact .arrival { font-size: 59px; }.service.dense .service-no, .service.dense .arrival { font-size: 45px; }.service.compact, .service.dense { padding-top: 2px; padding-bottom: 2px; }
.arrival-sub { color: #7f8b87; font-size: 10px; font-weight: 650; }.muted { color: #78837f; font-size: 11px; font-weight: 400; }
.nav { padding-top: 3px; }.nav button { min-height: 40px; border: 0; border-bottom: 5px solid transparent; border-radius: 0; background: transparent; color: #7f8b87; font-size: 14px; font-weight: 700; }
.nav button.active { border-bottom-color: #6ed9ae; background: transparent; color: #dfe4e1; }.artwork { border-radius: 12px; }.roon-title { font-size: 35px; font-weight: 620; }.roon-artist { color: #b6c0bc; font-size: 18px; }
.transport button { min-width: 50px; min-height: 50px; border-radius: 25px; padding: 0; background: #18211f; color: #e4e7e4; }.transport .play { min-width: 68px; min-height: 68px; border-radius: 34px; background: #285f4d; }
.progress trough, .volume trough { min-height: 7px; border: 0; box-shadow: none; border-radius: 4px; background: #303a37; }.progress highlight, .volume highlight { border: 0; box-shadow: none; background: #6ed9ae; }.time { color: #87928e; font-size: 12px; }
.sleep { background: #000; }.sleep-clock { font-size: 112px; font-weight: 550; }.settings-title { font-size: 32px; font-weight: 650; }
.settings-card { background: #131c1a; border: 1px solid #26312e; border-radius: 14px; padding: 16px; }.settings-action { min-height: 54px; border-radius: 12px; background: #285f4d; color: #f4f0e6; font-weight: 750; }
.settings-select { min-height: 48px; border-radius: 8px; background: #0d1412; color: #f4f0e6; }.settings-row { padding: 7px 0; }.settings-diagnostic { color: #aab4b0; font-size: 12px; }
.settings-controls { padding: 4px 0; }.settings-column { padding: 0 5px; }.setting-line { min-height: 52px; padding: 0 12px; border-radius: 8px; background: #0d1412; }.setting-line label { font-size: 14px; font-weight: 650; }.setting-line checkbutton { font-size: 14px; font-weight: 650; }.setting-line check { min-width: 22px; min-height: 22px; border-radius: 5px; border: 2px solid #61706b; background: #111a18; }.setting-line check:checked { background: #6ed9ae; border-color: #6ed9ae; color: #082018; }
.stop-row { margin-bottom: 4px; }.home-grid { padding: 9px 0; }.home-tile { min-height: 120px; border-radius: 12px; padding: 10px 11px 8px; background: #131c1a; border: 1px solid #293633; color: #aab4b0; }.home-tile.on { background: #173229; border-color: #35785f; color: #f4f0e6; }.home-device-button { min-height: 92px; padding: 0; background: transparent; color: #9aaba5; }.home-tile.on .home-device-button { color: #6ed9ae; }.home-icon { opacity: .72; }.home-name { font-size: 15px; font-weight: 700; }.home-state { color: #7f8b87; font-size: 11px; }.home-level { min-width: 28px; min-height: 94px; }.home-level trough { min-width: 7px; border-radius: 4px; background: #303a37; }.home-level highlight { background: #6ed9ae; border-radius: 4px; }.home-level slider { min-width: 20px; min-height: 20px; border-radius: 10px; background: #f4f0e6; }
.high-resolution .page { padding: 22px 30px 16px; }.high-resolution .stop { font-size: 34px; }.high-resolution .clock { font-size: 42px; }.high-resolution .eyebrow { font-size: 15px; }.high-resolution .service-no, .high-resolution .arrival { font-size: 108px; }.high-resolution .service.compact .service-no, .high-resolution .service.compact .arrival { font-size: 80px; }.high-resolution .service.dense .service-no, .high-resolution .service.dense .arrival { font-size: 62px; }.high-resolution .artwork { min-width: 380px; min-height: 380px; }.high-resolution .roon-title { font-size: 48px; }.high-resolution .roon-artist { font-size: 25px; }.high-resolution .nav button { min-height: 54px; font-size: 19px; }
"""


def get_json(url: str, timeout: float = .8):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.load(response)
    except Exception:
        return None


def post_json(url: str, data: dict, timeout: float = 1.2):
    try:
        request = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except Exception:
        return None


def get_bytes(url: str, timeout: float = 1.2):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read()
    except Exception:
        return None


class Display(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="uk.co.dallabs.PiBusNative")
        self.polling = False
        self.state = None
        self.settings_open = False
        self.last_mode = "bus"
        self.settings_data = {}
        self.image_key = None
        self.image_misses = 0
        self.volume_updating = False
        self.seek_updating = False
        self.seek_timeout = None
        self.screen_powered = None
        self.system_data = {}
        self.last_config_fetch = 0.0
        self.last_system_fetch = 0.0
        self.bus_signature = None
        self.display_controls_loaded = False
        self.touch_controls = {}
        self.home_signature = None
        self.home_nav_buttons = []
        self.home_value_timeouts = {}
        self.brightness_updating = False
        self.brightness_timeout = None
        self.brightness_applied = False
        self.views_prewarmed = False
        self.started_at = time.monotonic()
        self.refresh_count = 0

    def label(self, text="", css=None, x=0):
        widget = Gtk.Label(label=text, xalign=x)
        if css:
            widget.add_css_class(css)
        return widget

    def button(self, text, callback, css="utility"):
        widget = Gtk.Button(label=text)
        if css:
            widget.add_css_class(css)
        widget.connect("clicked", callback)
        return widget

    def icon_button(self, icon, callback, css=""):
        widget = Gtk.Button()
        if css:
            widget.add_css_class(css)
        widget.set_child(Gtk.Image.new_from_icon_name(icon))
        widget.connect("clicked", callback)
        return widget

    def do_activate(self):
        provider = Gtk.CssProvider(); provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window = Gtk.ApplicationWindow(application=self); self.window.set_decorated(False); self.window.set_default_size(800, 480); self.window.fullscreen()
        transparent = Gdk.MemoryTexture.new(
            1, 1, Gdk.MemoryFormat.R8G8B8A8_PREMULTIPLIED,
            GLib.Bytes.new(b"\x00\x00\x00\x00"), 4,
        )
        self.hidden_cursor = Gdk.Cursor.new_from_texture(transparent, 0, 0, None)
        self.window.set_cursor(self.hidden_cursor)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.NONE, transition_duration=0)
        self.stack.add_named(self.build_bus(), "bus"); self.stack.add_named(self.build_roon(), "roon"); self.stack.add_named(self.build_home(), "home"); self.stack.add_named(self.build_settings(), "settings"); self.stack.add_named(self.build_sleep(), "sleep")
        self.window.set_child(self.stack); self.window.present()
        GLib.idle_add(self.adapt_display)
        GLib.timeout_add_seconds(1, self.tick); GLib.timeout_add_seconds(2, self.start_poll); self.tick(); self.start_poll()

    def adapt_display(self):
        monitors = Gdk.Display.get_default().get_monitors()
        monitor = monitors.get_item(0) if monitors.get_n_items() else None
        if monitor and max(monitor.get_geometry().width, monitor.get_geometry().height) >= 1200:
            self.window.add_css_class("high-resolution")
        return False

    def header(self, centre, clock):
        row = Gtk.Box(spacing=10)
        centre.set_xalign(0)
        title = Gtk.Button(); title.add_css_class("header-hotspot"); title.add_css_class("header-title"); title.set_child(centre); title.set_hexpand(True); title.connect("clicked", self.open_settings); row.append(title)
        clock.set_xalign(1)
        clock_button = Gtk.Button(); clock_button.add_css_class("header-hotspot"); clock_button.add_css_class("header-clock"); clock_button.set_child(clock); clock_button.connect("clicked", self.sleep); row.append(clock_button)
        return row

    def navigation(self, active):
        row = Gtk.Box(spacing=8); row.add_css_class("nav")
        now = self.button("Now Playing", lambda *_: self.set_mode("roon"), "")
        bus = self.button("Bus Times", lambda *_: self.set_mode("bus"), "")
        home = self.button("Home", lambda *_: self.set_mode("home"), ""); self.home_nav_buttons.append(home)
        {"roon": now, "bus": bus, "home": home}.get(active, bus).add_css_class("active")
        for button in (now, bus, home): button.set_hexpand(True); row.append(button)
        return row

    def build_bus(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); page.add_css_class("page")
        self.bus_clock = self.label("--:--", "clock", 1); page.append(self.header(self.label("PI HOME", "eyebrow"), self.bus_clock))
        stop_row = Gtk.Box(spacing=8); stop_row.add_css_class("stop-row"); stop_row.set_halign(Gtk.Align.CENTER); self.stop = self.label("Connecting…", "stop"); self.stop_code = self.label("", "stop-code"); stop_row.append(self.stop); stop_row.append(self.stop_code); page.append(stop_row)
        self.services = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9); self.services.set_vexpand(True); page.append(self.services)
        footer = Gtk.Box(); self.bus_status = self.label("Starting", "muted"); self.updated = self.label("", "muted", 1); self.updated.set_hexpand(True); footer.append(self.bus_status); footer.append(self.updated); page.append(footer)
        page.append(self.navigation("bus")); return page

    def build_roon(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); page.add_css_class("page")
        self.zone = self.label("ROON NOW PLAYING", "eyebrow"); self.roon_clock = self.label("--:--", "clock", 1); page.append(self.header(self.zone, self.roon_clock))
        content = Gtk.Box(spacing=26); content.set_vexpand(True); content.set_margin_start(8); content.set_margin_end(8); content.set_margin_top(8); content.set_margin_bottom(8)
        self.artwork = Gtk.Picture(); self.artwork.add_css_class("artwork"); self.artwork.set_size_request(280, 280); self.artwork.set_valign(Gtk.Align.CENTER); self.artwork.set_content_fit(Gtk.ContentFit.COVER); content.append(self.artwork)
        centre = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); centre.set_valign(Gtk.Align.CENTER); centre.set_hexpand(True)
        self.title = self.label("Waiting for Roon…", "roon-title", .5); self.title.set_wrap(True); self.title.set_lines(2); self.title.set_justify(Gtk.Justification.CENTER)
        self.artist = self.label("Enable Pi Home Roon Controller in Roon", "roon-artist", .5); self.artist.set_wrap(True); self.artist.set_justify(Gtk.Justification.CENTER); centre.append(self.title); centre.append(self.artist)
        self.progress = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1); self.progress.add_css_class("progress"); self.progress.set_draw_value(False); self.progress.set_sensitive(False); self.progress.connect("value-changed", self.change_seek); centre.append(self.progress)
        times = Gtk.Box(); self.elapsed = self.label("0:00", "time"); self.remaining = self.label("−0:00", "time", 1); self.remaining.set_hexpand(True); times.append(self.elapsed); times.append(self.remaining); centre.append(times)
        self.controls = Gtk.Box(spacing=14); self.controls.set_halign(Gtk.Align.CENTER); self.controls.add_css_class("transport")
        self.controls.set_margin_top(6); self.controls.set_margin_bottom(16)
        self.prev = self.icon_button("media-skip-backward-symbolic", lambda *_: self.control("previous")); self.play = self.icon_button("media-playback-start-symbolic", lambda *_: self.control("playpause"), "play"); self.next = self.icon_button("media-skip-forward-symbolic", lambda *_: self.control("next"))
        self.prev.set_size_request(50, 50); self.prev.set_valign(Gtk.Align.CENTER); self.play.set_size_request(68, 68); self.play.set_valign(Gtk.Align.CENTER); self.next.set_size_request(50, 50); self.next.set_valign(Gtk.Align.CENTER)
        self.controls.append(self.prev); self.controls.append(self.play); self.controls.append(self.next); centre.append(self.controls)
        volume_row = Gtk.Box(spacing=10); volume_row.append(self.label("VOL", "eyebrow")); self.volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1); self.volume.add_css_class("volume"); self.volume.set_hexpand(True); self.volume.set_draw_value(False); self.volume.connect("value-changed", self.change_volume); volume_row.append(self.volume); self.volume_value = self.label("—", "time", 1); volume_row.append(self.volume_value); centre.append(volume_row)
        content.append(centre); page.append(content); page.append(self.navigation("roon")); return page

    def build_home(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); page.add_css_class("page")
        self.home_clock = self.label("--:--", "clock", 1); page.append(self.header(self.label("HOME", "eyebrow"), self.home_clock))
        self.home_status = self.label("Connecting to Home Assistant…", "muted", .5); page.append(self.home_status)
        self.home_grid = Gtk.Grid(column_spacing=11, row_spacing=11); self.home_grid.add_css_class("home-grid"); self.home_grid.set_column_homogeneous(True); self.home_grid.set_row_homogeneous(True); self.home_grid.set_vexpand(True); page.append(self.home_grid)
        page.append(self.navigation("home")); return page

    def build_settings(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); page.add_css_class("page")
        top = Gtk.Box(spacing=10); top.append(self.button("BACK", self.close_settings)); title = self.label("Touchscreen settings", "settings-title", .5); title.set_hexpand(True); top.append(title); top.append(self.button("SLEEP", self.sleep)); page.append(top)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); card.add_css_class("settings-card"); card.set_vexpand(True)
        self.device_status = self.label("Checking system…", "muted", .5); card.append(self.device_status)
        self.touch_diagnostics = self.label("Loading diagnostics…", "settings-diagnostic", .5); self.touch_diagnostics.set_wrap(True); self.touch_diagnostics.set_justify(Gtk.Justification.CENTER); card.append(self.touch_diagnostics)
        controls = Gtk.Box(spacing=16); controls.add_css_class("settings-controls"); controls.set_vexpand(True)
        daily = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); daily.add_css_class("settings-column"); daily.set_size_request(430, -1); daily.append(self.label("DAILY CONTROLS", "eyebrow")); self.touch_daily = daily; controls.append(daily)
        display_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); display_column.add_css_class("settings-column"); display_column.set_hexpand(True); display_column.append(self.label("DISPLAY", "eyebrow"))
        self.touch_profile = Gtk.DropDown.new_from_strings(["Profile · Original 800×480", "Profile · Touch 2 5/7-inch", "Profile · Touch 2 10-inch"]); self.touch_profile.add_css_class("settings-select"); display_column.append(self.touch_profile)
        self.touch_orientation = Gtk.DropDown.new_from_strings(["Orientation · Normal", "Orientation · 90°", "Orientation · 180°", "Orientation · 270°"]); self.touch_orientation.add_css_class("settings-select"); display_column.append(self.touch_orientation); controls.append(display_column); card.append(controls)
        brightness_row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3); brightness_row.add_css_class("setting-line"); brightness_row.append(self.label("Display brightness", "muted")); self.touch_brightness = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 100, 1); self.touch_brightness.set_draw_value(True); self.touch_brightness.set_value_pos(Gtk.PositionType.RIGHT); self.touch_brightness.connect("value-changed", self.change_brightness); brightness_row.append(self.touch_brightness); display_column.append(brightness_row)
        actions = Gtk.Box(spacing=12); actions.set_valign(Gtk.Align.END); self.apply_display_button = self.button("APPLY & REBOOT", self.request_display_settings, "settings-action"); self.apply_display_button.set_hexpand(True); actions.append(self.apply_display_button); self.update_button = self.button("INSTALL UPDATE", self.request_update, "settings-action"); self.update_button.set_hexpand(True); actions.append(self.update_button); card.append(actions); page.append(card)
        return page

    def build_sleep(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); box.add_css_class("sleep"); box.set_halign(Gtk.Align.FILL); box.set_valign(Gtk.Align.FILL); box.set_hexpand(True); box.set_vexpand(True)
        centre = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); centre.set_halign(Gtk.Align.CENTER); centre.set_valign(Gtk.Align.CENTER); centre.set_hexpand(True); centre.set_vexpand(True)
        self.sleep_clock = self.label("--:--", "sleep-clock", .5); centre.append(self.sleep_clock); self.sleep_hint = self.label("TAP ANYWHERE TO WAKE", "eyebrow", .5); centre.append(self.sleep_hint); box.append(centre)
        gesture = Gtk.GestureClick(); gesture.connect("released", self.wake); box.add_controller(gesture); return box

    def tick(self):
        now = datetime.now(TZ).strftime("%H:%M"); self.bus_clock.set_text(now); self.roon_clock.set_text(now); self.home_clock.set_text(now); self.sleep_clock.set_text(now); return True

    def start_poll(self):
        if not self.polling:
            self.polling = True; threading.Thread(target=self.poll, daemon=True).start()
        return True

    def poll(self):
        started = time.monotonic()
        target = get_json(BUS + "/api/display-target") or {}; status = get_json(BUS + "/api/status"); roon = get_json(ROON + "/api/state"); device = get_json(BUS + "/api/device/controls") or {}
        now = time.monotonic(); config = None; system = None
        if not self.settings_data or now - self.last_config_fetch >= 60:
            config = get_json(BUS + "/api/admin/config") or {}; self.last_config_fetch = now
        if self.settings_open and (not self.system_data or now - self.last_system_fetch >= 15):
            system = get_json(BUS + "/api/admin/system") or {}; self.last_system_fetch = now
        zone = (roon or {}).get("zone") or {}; key = (zone.get("now_playing") or {}).get("image_key")
        GLib.idle_add(self.apply, target.get("target", "/"), status, roon, config, system, device, key, None)
        self.polling = False
        image = get_bytes(f"{ROON}/api/image?key={quote(key, safe='')}") if key and key != self.image_key else None
        if image:
            GLib.idle_add(self.apply_artwork, key, image)
        elapsed = time.monotonic() - started; self.refresh_count += 1
        if self.refresh_count <= 5 and elapsed > .25:
            print(f"Pi Home core refresh completed in {elapsed:.3f}s", flush=True)

    def apply(self, target, status, roon, config, system, device, image_key, image):
        if config is not None:
            self.settings_data = config
            self.controls.set_visible(config.get("roon_show_controls", True)); self.roon_clock.set_visible(config.get("roon_show_clock", True))
            show_sleep_clock = config.get("sleep_show_clock", False); self.sleep_clock.set_visible(show_sleep_clock); self.sleep_hint.set_visible(show_sleep_clock)
            for button in self.home_nav_buttons: button.set_visible(bool(config.get("home_assistant_enabled") and config.get("home_assistant_entities")))
        if system is not None:
            self.system_data = system
            self.device_status.set_text(f"v{system.get('app_version', '—')}  ·  {system.get('update_status', 'Ready')}")
            diagnostics = system.get("diagnostics") or {}; memory = diagnostics.get("memory") or {}; processes = diagnostics.get("processes") or []
            states = {item.get("label"): item.get("active", bool(item.get("pids"))) for item in processes}
            temperature = diagnostics.get("temperature_c"); load = diagnostics.get("load") or [0]
            health = f"Memory {memory.get('used_percent', 0):g}%  ·  Load {float(load[0]):.2f}"
            if temperature is not None: health += f"  ·  {temperature:g}°C"
            health += f"\nController {'ready' if states.get('Roon controller') else 'offline'}  ·  Bridge {'ready' if states.get('Roon Bridge') else 'offline'}"
            self.touch_diagnostics.set_text(health)
            if not self.display_controls_loaded:
                profiles = {"original": 0, "touch2-5-7": 1, "touch2-10": 2}; orientations = {"normal": 0, "90": 1, "180": 2, "270": 3}
                self.touch_profile.set_selected(profiles.get(system.get("display_profile"), 0)); self.touch_orientation.set_selected(orientations.get(system.get("display_rotation"), 0)); self.display_controls_loaded = True
        self.render_touch_controls(device, self.system_data)
        self.render_home((device or {}).get("home") or {})
        brightness = int((device or {}).get("display_brightness", 100))
        if not self.brightness_updating and round(self.touch_brightness.get_value()) != brightness:
            self.brightness_updating = True; self.touch_brightness.set_value(brightness); self.brightness_updating = False
        if not self.brightness_applied:
            self.brightness_applied = True
            threading.Thread(target=post_json, args=(BUS + "/api/device/brightness", {"brightness": brightness}), daemon=True).start()
        config = self.settings_data; system = self.system_data
        bus_signature = json.dumps(status, sort_keys=True, separators=(",", ":"), default=str)
        if bus_signature != self.bus_signature:
            self.render_bus(status); self.bus_signature = bus_signature
        self.render_roon(roon)
        if not self.views_prewarmed:
            self.views_prewarmed = True; GLib.idle_add(self.prewarm_views)
        if self.settings_open:
            return False
        if target == "/sleep.html": desired = "sleep"; self.set_screen_power(bool(config.get("sleep_show_clock", False)))
        elif target == "/home": desired = "home"; self.set_screen_power(True); self.last_mode = "home"
        elif target == "/" or target.endswith(":8765/"): desired = "bus"; self.set_screen_power(True); self.last_mode = "bus"
        else: desired = "roon"; self.set_screen_power(True); self.last_mode = "roon"
        if self.stack.get_visible_child_name() != desired:
            self.stack.set_visible_child_name(desired)
        return False

    def apply_artwork(self, image_key, image):
        try:
            self.artwork.set_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(image))); self.image_key = image_key; self.image_misses = 0
        except GLib.Error:
            pass
        return False

    def prewarm_views(self):
        started = time.monotonic()
        for name in ("roon", "home"):
            child = self.stack.get_child_by_name(name)
            child.measure(Gtk.Orientation.HORIZONTAL, 800)
            child.measure(Gtk.Orientation.VERTICAL, 480)
        print(f"Pi Home views pre-measured in {(time.monotonic() - started) * 1000:.1f}ms", flush=True)
        return False

    def render_touch_controls(self, device, system):
        signature = json.dumps({"services": device.get("services", []), "bridge": (system or {}).get("roon_bridge")}, sort_keys=True)
        if signature == getattr(self, "touch_controls_signature", None): return
        self.touch_controls_signature = signature
        while child := self.touch_daily.get_last_child():
            if child == self.touch_daily.get_first_child(): break
            self.touch_daily.remove(child)
        bridge = Gtk.Box(spacing=8); bridge.add_css_class("setting-line"); bridge_check = Gtk.CheckButton(label="Roon Bridge"); bridge_check.set_active((system or {}).get("roon_bridge") == "active"); bridge_check.connect("toggled", self.toggle_bridge); bridge.append(bridge_check); self.touch_daily.append(bridge)
        services = Gtk.Box(spacing=12); services.add_css_class("setting-line"); services.append(self.label("Buses"))
        for item in device.get("services", []):
            button = Gtk.CheckButton(label=item.get("name", "")); button.set_active(bool(item.get("enabled"))); button.connect("toggled", self.toggle_service, item.get("name", "")); services.append(button)
        self.touch_daily.append(services)

    def render_home(self, home):
        signature = json.dumps({"status": home.get("status"), "entities": home.get("entities", [])}, sort_keys=True, default=str)
        if signature == self.home_signature: return
        self.home_signature = signature
        while child := self.home_grid.get_first_child(): self.home_grid.remove(child)
        entities = home.get("entities", [])[:8]
        self.home_status.set_text("Home Assistant offline" if home.get("status") == "offline" else ("Choose Home Assistant devices in web settings" if not entities else ""))
        for index, entity in enumerate(entities):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); box.add_css_class("home-tile"); box.set_vexpand(True)
            state = str(entity.get("state", "unknown")); detail = state.upper()
            if entity.get("percentage") is not None: detail += f" · {entity['percentage']}%"
            if state in {"on", "open", "playing"}: box.add_css_class("on")
            control_row = Gtk.Box(spacing=5); control_row.set_vexpand(True)
            domain = entity.get("domain", "switch"); icon_name = domain + ("-on" if state == "on" else "") + ".svg"
            icon = Gtk.Image.new_from_file(str(Path(__file__).with_name("icons") / icon_name)); icon.set_pixel_size(58); icon.add_css_class("home-icon")
            button = Gtk.Button(); button.add_css_class("home-device-button"); button.set_hexpand(True); button.set_vexpand(True); button.set_child(icon); button.connect("clicked", self.toggle_home, entity.get("entity_id", "")); control_row.append(button)
            if entity.get("supports_level"):
                level = entity.get("percentage")
                if level is None and entity.get("brightness") is not None: level = round(float(entity["brightness"]) * 100 / 255)
                scale = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, 0, 100, 1); scale.add_css_class("home-level"); scale.set_draw_value(False); scale.set_inverted(True); scale.set_value(float(level or 0)); scale.connect("value-changed", self.change_home_value, entity.get("entity_id", "")); control_row.append(scale)
            if domain in {"switch", "input_boolean"}:
                swipe = Gtk.GestureSwipe(); swipe.connect("swipe", self.swipe_home_switch, entity.get("entity_id", "")); button.add_controller(swipe)
            box.append(control_row)
            name = self.label(entity.get("name", "Device"), "home-name", .5); name.set_wrap(True); name.set_lines(2); box.append(name); box.append(self.label(detail, "home-state", .5))
            self.home_grid.attach(box, index % 4, index // 4, 1, 1)

    def render_bus(self, data):
        if not data: self.bus_status.set_text("Bus service unavailable"); return
        self.stop.set_text(data.get('stop_name', 'Bus times')); self.stop_code.set_text(data.get('stop_code', ''))
        while child := self.services.get_first_child(): self.services.remove(child)
        visible = data.get("services", [])[:4]
        colours = ("service-blue", "service-green", "service-violet", "service-amber")
        for index, service in enumerate(visible):
            row = Gtk.Box(spacing=12); row.add_css_class("service"); row.add_css_class(colours[index]); row.set_vexpand(True)
            if len(visible) == 3: row.add_css_class("compact")
            elif len(visible) >= 4: row.add_css_class("dense")
            number = self.label(str(service.get("service", "")), "service-no"); number.set_size_request(100 if len(visible) > 2 else 125, -1); number.set_valign(Gtk.Align.START); row.append(number)
            arrivals = Gtk.Box(spacing=8); arrivals.set_hexpand(True)
            for arrival in service.get("arrivals", [])[:3]:
                col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); col.set_valign(Gtk.Align.START); minutes = arrival.get("minutes"); col.append(self.label("Due" if minutes == 0 else str(minutes), "arrival", .5)); col.append(self.label("MIN · LIVE" if arrival.get("monitored") else "MIN · AFTER", "arrival-sub", .5)); col.set_hexpand(True); arrivals.append(col)
            row.append(arrivals); self.services.append(row)
        self.bus_status.set_text("Live from LTA DataMall" if data.get("status") == "ok" and not data.get("stale") else "Offline / last known arrivals")
        updated = data.get("updated_at"); self.updated.set_text("Updated " + updated[11:19] if updated else "")

    def render_roon(self, data):
        self.state = data; zone = (data or {}).get("zone")
        if not zone:
            self.zone.set_text(self.settings_data.get("roon_zone_name") or "ROON")
            if data is None:
                self.title.set_text("Controller unavailable"); self.artist.set_text("Check the controller service in web settings")
            elif not data.get("connected"):
                self.title.set_text("Authorise in Roon"); self.artist.set_text("Settings → Extensions → Pi Home Roon Controller")
            else:
                self.title.set_text("Nothing playing"); self.artist.set_text("No Roon zones are available")
            self.prev.set_sensitive(False); self.play.set_sensitive(False); self.next.set_sensitive(False); self.seek_updating = True; self.progress.set_value(0); self.progress.set_sensitive(False); self.seek_updating = False; self.volume.set_sensitive(False); self.note_missing_artwork(); return
        playing = zone.get("now_playing") or {}; lines = playing.get("three_line") or playing.get("two_line") or playing.get("one_line") or {}
        if not playing.get("image_key"):
            self.note_missing_artwork()
        else:
            self.image_misses = 0
        self.zone.set_text(zone.get("name") or "ROON"); self.title.set_text(lines.get("line1") or "Nothing playing"); self.artist.set_text(" · ".join(filter(None, (lines.get("line2"), lines.get("line3")))) or "Roon")
        self.play.set_child(Gtk.Image.new_from_icon_name("media-playback-pause-symbolic" if zone.get("state") == "playing" else "media-playback-start-symbolic")); self.prev.set_sensitive(bool(zone.get("can_previous"))); self.next.set_sensitive(bool(zone.get("can_next"))); self.play.set_sensitive(bool(zone.get("can_play") or zone.get("can_pause")))
        elapsed = int(zone.get("seek_position") or 0); length = int(playing.get("length") or 0); self.seek_updating = True; self.progress.set_range(0, max(1, length)); self.progress.set_value(min(elapsed, length) if length else 0); self.progress.set_sensitive(bool(zone.get("can_seek") and length)); self.seek_updating = False; self.elapsed.set_text(self.format_time(elapsed)); self.remaining.set_text("−" + self.format_time(max(0, length - elapsed)))
        output = zone.get("output") or {}; volume = output.get("volume") or {}; value = volume.get("value"); self.volume_updating = True; self.volume.set_sensitive(value is not None); self.volume.set_value(float(value or 0)); self.volume_value.set_text(str(value) if value is not None else "FIXED"); self.volume_updating = False

    def set_mode(self, mode):
        started = time.monotonic(); self.settings_open = False; self.last_mode = mode; self.stack.set_visible_child_name(mode); print(f"Pi Home switched to {mode} in {(time.monotonic() - started) * 1000:.1f}ms", flush=True); threading.Thread(target=post_json, args=(BUS + "/api/admin/display-mode", {"mode": mode}), daemon=True).start()

    def note_missing_artwork(self):
        self.image_misses += 1
        if self.image_misses >= 5:
            self.artwork.set_paintable(None)
            self.image_key = None

    def open_settings(self, *_): self.settings_open = True; self.last_system_fetch = 0; self.stack.set_visible_child_name("settings"); self.start_poll()
    def close_settings(self, *_): self.settings_open = False; self.stack.set_visible_child_name(self.last_mode)
    def sleep(self, *_): self.settings_open = False; self.stack.set_visible_child_name("sleep"); self.set_screen_power(bool(self.settings_data.get("sleep_show_clock", False))); threading.Thread(target=post_json, args=(BUS + "/api/admin/display-mode", {"mode": "sleep"}), daemon=True).start()
    def wake(self, *_):
        self.set_screen_power(True, force=True); self.stack.set_visible_child_name(self.last_mode or "bus")
        threading.Thread(target=post_json, args=(BUS + "/api/device/wake", {"view": self.last_mode or "bus"}), daemon=True).start()
    def control(self, action): threading.Thread(target=post_json, args=(ROON + "/api/control", {"action": action}), daemon=True).start()
    def toggle_bridge(self, button):
        threading.Thread(target=post_json, args=(BUS + "/api/device/roon-bridge", {"enabled": button.get_active()}), daemon=True).start()
    def toggle_service(self, button, service):
        threading.Thread(target=post_json, args=(BUS + "/api/device/service-visibility", {"service": service, "enabled": button.get_active()}), daemon=True).start()
    def toggle_home(self, _button, entity_id):
        if entity_id: threading.Thread(target=post_json, args=(BUS + "/api/device/home-toggle", {"entity_id": entity_id}), daemon=True).start()
    def swipe_home_switch(self, _gesture, velocity_x, _velocity_y, entity_id):
        if entity_id and abs(velocity_x) > 80:
            threading.Thread(target=post_json, args=(BUS + "/api/device/home-state", {"entity_id": entity_id, "enabled": velocity_x > 0}), daemon=True).start()
    def change_home_value(self, scale, entity_id):
        if not entity_id: return
        previous = self.home_value_timeouts.pop(entity_id, None)
        if previous is not None: GLib.source_remove(previous)
        self.home_value_timeouts[entity_id] = GLib.timeout_add(260, self.send_home_value, entity_id, round(scale.get_value()))
    def send_home_value(self, entity_id, value):
        self.home_value_timeouts.pop(entity_id, None)
        threading.Thread(target=post_json, args=(BUS + "/api/device/home-value", {"entity_id": entity_id, "value": value}), daemon=True).start()
        return False
    def change_brightness(self, scale):
        if self.brightness_updating: return
        if self.brightness_timeout is not None: GLib.source_remove(self.brightness_timeout)
        self.brightness_timeout = GLib.timeout_add(180, self.send_brightness, round(scale.get_value()))
    def send_brightness(self, value):
        self.brightness_timeout = None
        threading.Thread(target=post_json, args=(BUS + "/api/device/brightness", {"brightness": value}), daemon=True).start()
        return False
    def format_time(self, seconds): return f"{seconds // 60}:{seconds % 60:02d}"
    def change_volume(self, scale):
        if self.volume_updating or not self.state: return
        output = (self.state.get("zone") or {}).get("output") or {}; output_id = output.get("id")
        if output_id: threading.Thread(target=post_json, args=(ROON + "/api/volume", {"output_id": output_id, "value": round(scale.get_value())}), daemon=True).start()

    def change_seek(self, scale):
        if self.seek_updating or not self.state or not (self.state.get("zone") or {}).get("can_seek"):
            return
        if self.seek_timeout is not None:
            GLib.source_remove(self.seek_timeout)
        self.seek_timeout = GLib.timeout_add(220, self.send_seek, round(scale.get_value()))

    def send_seek(self, seconds):
        self.seek_timeout = None
        threading.Thread(target=post_json, args=(ROON + "/api/seek", {"seconds": seconds}), daemon=True).start()
        return False

    def set_screen_power(self, powered, force=False):
        if powered == self.screen_powered and not force:
            return
        self.screen_powered = powered
        threading.Thread(target=post_json, args=(BUS + "/api/device/screen-power", {"powered": powered}), daemon=True).start()
        GLib.timeout_add_seconds(1 if powered else 2, self.confirm_screen_power, powered)

    def confirm_screen_power(self, powered):
        if self.screen_powered is powered:
            threading.Thread(target=post_json, args=(BUS + "/api/device/screen-power", {"powered": powered}), daemon=True).start()
        return False

    def request_update(self, *_):
        self.update_button.set_sensitive(False); self.device_status.set_text("Update requested…")
        threading.Thread(target=self._request_update, daemon=True).start()

    def _request_update(self):
        result = post_json(BUS + "/api/device/update", {})
        GLib.idle_add(self.device_status.set_text, "Update started…" if result else "Could not start update")
        GLib.idle_add(self.update_button.set_sensitive, True)

    def request_display_settings(self, *_):
        profiles = ("original", "touch2-5-7", "touch2-10"); orientations = ("normal", "90", "180", "270")
        profile = profiles[min(self.touch_profile.get_selected(), len(profiles) - 1)]; transform = orientations[min(self.touch_orientation.get_selected(), len(orientations) - 1)]
        self.apply_display_button.set_sensitive(False); self.device_status.set_text("Applying display settings…")
        threading.Thread(target=self._request_display_settings, args=(profile, transform), daemon=True).start()

    def _request_display_settings(self, profile, transform):
        result = post_json(BUS + "/api/admin/system-action", {"action": "set_display", "profile": profile, "transform": transform})
        GLib.idle_add(self.device_status.set_text, "Rebooting…" if result else "Could not apply display settings")
        if not result: GLib.idle_add(self.apply_display_button.set_sensitive, True)


if __name__ == "__main__":
    Display().run(None)
