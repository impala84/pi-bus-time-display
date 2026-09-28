#!/usr/bin/env python3
"""Native GTK4 touchscreen for Pi Bus Time Display."""
from __future__ import annotations

import json
import threading
import urllib.request
from datetime import datetime
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
.clock { font-size: 31px; font-weight: 600; }.stop { font-size: 25px; font-weight: 700; }
.header-hotspot { min-height: 42px; padding: 0; border: 0; box-shadow: none; background: transparent; background-image: none; }
.header-hotspot:hover, .header-hotspot:active { background: transparent; box-shadow: none; }
.header-title { padding-left: 0; }.header-clock { padding-right: 0; }
.utility { min-width: 92px; min-height: 38px; border-radius: 7px; background: #18211f; color: #d9dedb; font-size: 11px; font-weight: 750; }
.service { background: #131c1a; border: 1px solid #26312e; border-radius: 14px; padding: 5px 16px; }
.service-blue { border-color: #28566e; background: #112027; }.service-green { border-color: #285e43; background: #102219; }
.service-no, .arrival { font-size: 82px; font-weight: 720; font-variant-numeric: tabular-nums; }
.service-no { font-weight: 760; }.service-blue .service-no { color: #55a9d7; }.service-green .service-no { color: #61c68f; }
.arrival-sub { color: #7f8b87; font-size: 10px; font-weight: 650; }.muted { color: #78837f; font-size: 11px; font-weight: 400; }
.nav { padding-top: 5px; }.nav button { min-height: 46px; border-radius: 8px; background: #18211f; color: #9aa6a2; font-size: 15px; font-weight: 750; }
.nav button.active { background: #285f4d; color: #f4f0e6; }.artwork { border-radius: 12px; }.roon-title { font-size: 35px; font-weight: 620; }.roon-artist { color: #b6c0bc; font-size: 18px; }
.transport button { min-width: 54px; min-height: 54px; border-radius: 50%; padding: 0; background: #18211f; color: #e4e7e4; }.transport .play { min-width: 70px; min-height: 70px; border-radius: 50%; background: #285f4d; }
.progress trough, .volume trough { min-height: 7px; border: 0; box-shadow: none; border-radius: 4px; background: #303a37; }.progress progress, .volume highlight { border: 0; box-shadow: none; background: #6ed9ae; }.time { color: #87928e; font-size: 12px; }
.sleep { background: #000; }.sleep-clock { font-size: 112px; font-weight: 550; }.settings-title { font-size: 32px; font-weight: 650; }
.settings-card { background: #131c1a; border: 1px solid #26312e; border-radius: 14px; padding: 16px; }.settings-action { min-height: 54px; border-radius: 12px; background: #285f4d; color: #f4f0e6; font-weight: 750; }
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
        self.volume_updating = False

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
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.NONE, transition_duration=0)
        self.stack.add_named(self.build_bus(), "bus"); self.stack.add_named(self.build_roon(), "roon"); self.stack.add_named(self.build_settings(), "settings"); self.stack.add_named(self.build_sleep(), "sleep")
        self.window.set_child(self.stack); self.window.present()
        GLib.timeout_add_seconds(1, self.tick); GLib.timeout_add_seconds(2, self.start_poll); self.tick(); self.start_poll()

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
        (now if active == "roon" else bus).add_css_class("active")
        now.set_hexpand(True); bus.set_hexpand(True); row.append(now); row.append(bus)
        return row

    def build_bus(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); page.add_css_class("page")
        self.bus_clock = self.label("--:--", "clock", 1); page.append(self.header(self.label("PI BUS TIME DISPLAY", "eyebrow"), self.bus_clock))
        self.stop = self.label("Connecting…", "stop", .5); page.append(self.stop)
        self.services = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); self.services.set_vexpand(True); page.append(self.services)
        footer = Gtk.Box(); self.bus_status = self.label("Starting", "muted"); self.updated = self.label("", "muted", 1); self.updated.set_hexpand(True); footer.append(self.bus_status); footer.append(self.updated); page.append(footer)
        page.append(self.navigation("bus")); return page

    def build_roon(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); page.add_css_class("page")
        self.zone = self.label("ROON NOW PLAYING", "eyebrow"); self.roon_clock = self.label("--:--", "clock", 1); page.append(self.header(self.zone, self.roon_clock))
        content = Gtk.Box(spacing=18); content.set_vexpand(True)
        self.artwork = Gtk.Picture(); self.artwork.add_css_class("artwork"); self.artwork.set_size_request(275, 275); self.artwork.set_content_fit(Gtk.ContentFit.COVER); content.append(self.artwork)
        centre = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); centre.set_valign(Gtk.Align.CENTER); centre.set_hexpand(True)
        self.title = self.label("Waiting for Roon…", "roon-title", .5); self.title.set_wrap(True); self.title.set_lines(2); self.title.set_justify(Gtk.Justification.CENTER)
        self.artist = self.label("Enable Pi Bus Roon Controller in Roon", "roon-artist", .5); self.artist.set_wrap(True); self.artist.set_justify(Gtk.Justification.CENTER); centre.append(self.title); centre.append(self.artist)
        self.progress = Gtk.ProgressBar(); self.progress.add_css_class("progress"); centre.append(self.progress)
        times = Gtk.Box(); self.elapsed = self.label("0:00", "time"); self.remaining = self.label("−0:00", "time", 1); self.remaining.set_hexpand(True); times.append(self.elapsed); times.append(self.remaining); centre.append(times)
        self.controls = Gtk.Box(spacing=14); self.controls.set_halign(Gtk.Align.CENTER); self.controls.add_css_class("transport")
        self.prev = self.icon_button("media-skip-backward-symbolic", lambda *_: self.control("previous")); self.play = self.icon_button("media-playback-start-symbolic", lambda *_: self.control("playpause"), "play"); self.next = self.icon_button("media-skip-forward-symbolic", lambda *_: self.control("next"))
        self.controls.append(self.prev); self.controls.append(self.play); self.controls.append(self.next); centre.append(self.controls)
        volume_row = Gtk.Box(spacing=10); volume_row.append(self.label("VOL", "eyebrow")); self.volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1); self.volume.add_css_class("volume"); self.volume.set_hexpand(True); self.volume.set_draw_value(False); self.volume.connect("value-changed", self.change_volume); volume_row.append(self.volume); self.volume_value = self.label("—", "time", 1); volume_row.append(self.volume_value); centre.append(volume_row)
        content.append(centre); page.append(content); page.append(self.navigation("roon")); return page

    def build_settings(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); page.add_css_class("page")
        top = Gtk.Box(spacing=10); top.append(self.button("BACK", self.close_settings)); title = self.label("Touchscreen settings", "settings-title", .5); title.set_hexpand(True); top.append(title); top.append(self.button("SLEEP", self.sleep)); page.append(top)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9); card.add_css_class("settings-card"); card.set_vexpand(True); card.set_valign(Gtk.Align.CENTER)
        card.append(self.label("Safe controls only", "eyebrow", .5)); safe = self.label("Bus stop, schedules, Roon and network settings are protected in the web admin.", "muted", .5); safe.set_wrap(True); safe.set_justify(Gtk.Justification.CENTER); card.append(safe)
        self.device_status = self.label("Checking system…", "muted", .5); card.append(self.device_status)
        self.update_button = self.button("CHECK AND INSTALL UPDATE", self.request_update, "settings-action"); card.append(self.update_button); page.append(card)
        return page

    def build_sleep(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); box.add_css_class("sleep"); box.set_halign(Gtk.Align.FILL); box.set_valign(Gtk.Align.FILL); box.set_hexpand(True); box.set_vexpand(True)
        centre = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); centre.set_halign(Gtk.Align.CENTER); centre.set_valign(Gtk.Align.CENTER); centre.set_hexpand(True); centre.set_vexpand(True)
        self.sleep_clock = self.label("--:--", "sleep-clock", .5); centre.append(self.sleep_clock); self.sleep_hint = self.label("TAP ANYWHERE TO WAKE", "eyebrow", .5); centre.append(self.sleep_hint); box.append(centre)
        gesture = Gtk.GestureClick(); gesture.connect("released", self.wake); box.add_controller(gesture); return box

    def tick(self):
        now = datetime.now(TZ).strftime("%H:%M"); self.bus_clock.set_text(now); self.roon_clock.set_text(now); self.sleep_clock.set_text(now); return True

    def start_poll(self):
        if not self.polling:
            self.polling = True; threading.Thread(target=self.poll, daemon=True).start()
        return True

    def poll(self):
        target = get_json(BUS + "/api/display-target") or {}; status = get_json(BUS + "/api/status"); roon = get_json(ROON + "/api/state"); config = get_json(BUS + "/api/admin/config") or {}; system = get_json(BUS + "/api/admin/system") or {}
        zone = (roon or {}).get("zone") or {}; key = (zone.get("now_playing") or {}).get("image_key"); image = get_bytes(f"{ROON}/api/image?key={key}") if key and key != self.image_key else None
        GLib.idle_add(self.apply, target.get("target", "/"), status, roon, config, system, key, image); self.polling = False

    def apply(self, target, status, roon, config, system, image_key, image):
        self.settings_data = config
        self.controls.set_visible(config.get("roon_show_controls", True)); self.roon_clock.set_visible(config.get("roon_show_clock", True))
        show_sleep_clock = config.get("sleep_show_clock", False); self.sleep_clock.set_visible(show_sleep_clock); self.sleep_hint.set_visible(show_sleep_clock)
        self.device_status.set_text(f"v{system.get('app_version', '—')}  ·  {system.get('update_status', 'Ready')}")
        self.render_bus(status); self.render_roon(roon)
        if image:
            try:
                self.artwork.set_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(image))); self.image_key = image_key
            except GLib.Error:
                pass
        if self.settings_open:
            return False
        if target == "/sleep.html": self.stack.set_visible_child_name("sleep")
        elif target == "/" or target.endswith(":8765/"): self.last_mode = "bus"; self.stack.set_visible_child_name("bus")
        else: self.last_mode = "roon"; self.stack.set_visible_child_name("roon")
        return False

    def render_bus(self, data):
        if not data: self.bus_status.set_text("Bus service unavailable"); return
        self.stop.set_text(f"{data.get('stop_name', 'Bus times')}  ·  {data.get('stop_code', '')}")
        while child := self.services.get_first_child(): self.services.remove(child)
        for index, service in enumerate(data.get("services", [])[:2]):
            row = Gtk.Box(spacing=12); row.add_css_class("service"); row.add_css_class("service-blue" if index == 0 else "service-green"); row.set_vexpand(True)
            number = self.label(str(service.get("service", "")), "service-no"); number.set_size_request(125, -1); number.set_valign(Gtk.Align.START); row.append(number)
            arrivals = Gtk.Box(spacing=8); arrivals.set_hexpand(True)
            for arrival in service.get("arrivals", [])[:3]:
                col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); col.set_valign(Gtk.Align.START); minutes = arrival.get("minutes"); col.append(self.label("Due" if minutes == 0 else str(minutes), "arrival", .5)); col.append(self.label("MIN · LIVE" if arrival.get("monitored") else "MIN · AFTER", "arrival-sub", .5)); col.set_hexpand(True); arrivals.append(col)
            row.append(arrivals); self.services.append(row)
        self.bus_status.set_text("Live from LTA DataMall" if data.get("status") == "ok" and not data.get("stale") else "Offline / last known arrivals")
        updated = data.get("updated_at"); self.updated.set_text("Updated " + updated[11:19] if updated else "")

    def render_roon(self, data):
        self.state = data; zone = (data or {}).get("zone")
        if not zone:
            self.zone.set_text(self.settings_data.get("roon_zone_name") or "ROON"); self.title.set_text("Nothing playing" if (data or {}).get("connected") else "Roon unavailable"); self.artist.set_text(""); self.prev.set_sensitive(False); self.play.set_sensitive(False); self.next.set_sensitive(False); self.progress.set_fraction(0); self.volume.set_sensitive(False); self.artwork.set_paintable(None); return
        playing = zone.get("now_playing") or {}; lines = playing.get("three_line") or playing.get("two_line") or playing.get("one_line") or {}
        self.zone.set_text(zone.get("name") or "ROON"); self.title.set_text(lines.get("line1") or "Nothing playing"); self.artist.set_text(" · ".join(filter(None, (lines.get("line2"), lines.get("line3")))) or "Roon")
        self.play.set_child(Gtk.Image.new_from_icon_name("media-playback-pause-symbolic" if zone.get("state") == "playing" else "media-playback-start-symbolic")); self.prev.set_sensitive(bool(zone.get("can_previous"))); self.next.set_sensitive(bool(zone.get("can_next"))); self.play.set_sensitive(bool(zone.get("can_play") or zone.get("can_pause")))
        elapsed = int(zone.get("seek_position") or 0); length = int(playing.get("length") or 0); self.progress.set_fraction(min(1, elapsed / length) if length else 0); self.elapsed.set_text(self.format_time(elapsed)); self.remaining.set_text("−" + self.format_time(max(0, length - elapsed)))
        output = zone.get("output") or {}; volume = output.get("volume") or {}; value = volume.get("value"); self.volume_updating = True; self.volume.set_sensitive(value is not None); self.volume.set_value(float(value or 0)); self.volume_value.set_text(str(value) if value is not None else "FIXED"); self.volume_updating = False

    def set_mode(self, mode):
        self.settings_open = False; self.last_mode = mode; self.stack.set_visible_child_name(mode); threading.Thread(target=post_json, args=(BUS + "/api/admin/display-mode", {"mode": mode}), daemon=True).start()

    def open_settings(self, *_): self.settings_open = True; self.stack.set_visible_child_name("settings")
    def close_settings(self, *_): self.settings_open = False; self.stack.set_visible_child_name(self.last_mode)
    def sleep(self, *_): self.settings_open = False; self.stack.set_visible_child_name("sleep"); threading.Thread(target=post_json, args=(BUS + "/api/admin/display-mode", {"mode": "sleep"}), daemon=True).start()
    def wake(self, *_): self.set_mode(self.last_mode or "auto")
    def control(self, action): threading.Thread(target=post_json, args=(ROON + "/api/control", {"action": action}), daemon=True).start()
    def format_time(self, seconds): return f"{seconds // 60}:{seconds % 60:02d}"
    def change_volume(self, scale):
        if self.volume_updating or not self.state: return
        output = (self.state.get("zone") or {}).get("output") or {}; output_id = output.get("id")
        if output_id: threading.Thread(target=post_json, args=(ROON + "/api/volume", {"output_id": output_id, "value": round(scale.get_value())}), daemon=True).start()

    def request_update(self, *_):
        self.update_button.set_sensitive(False); self.device_status.set_text("Update requested…")
        threading.Thread(target=self._request_update, daemon=True).start()

    def _request_update(self):
        result = post_json(BUS + "/api/device/update", {})
        GLib.idle_add(self.device_status.set_text, "Update started…" if result else "Could not start update")
        GLib.idle_add(self.update_button.set_sensitive, True)


if __name__ == "__main__":
    Display().run(None)
