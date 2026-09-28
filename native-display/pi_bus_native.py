#!/usr/bin/env python3
"""Native 800x480 touchscreen for Pi Bus Time Display."""
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
window { background: #0b1110; color: #f4f0e6; font-family: sans-serif; }
.page { padding: 22px 28px; }
.eyebrow { color: #97a39f; font-size: 12px; font-weight: 700; letter-spacing: 2px; }
.clock { font-size: 34px; font-weight: 600; }
.stop { font-size: 26px; font-weight: 700; }
.service { background: #131c1a; border: 1px solid #26312e; border-radius: 18px; padding: 10px 18px; }
.service-no { color: #6ef0be; font-size: 48px; font-weight: 800; }
.arrival { font-size: 36px; font-weight: 700; }
.arrival-sub { color: #97a39f; font-size: 10px; }
.muted { color: #97a39f; font-size: 12px; }
.roon-title { font-size: 32px; font-weight: 700; }
.roon-artist { color: #b6c0bc; font-size: 18px; }
.transport button { min-width: 74px; min-height: 58px; border-radius: 29px; font-size: 24px; }
.play { min-width: 92px; }
.sleep-clock { font-size: 112px; font-weight: 600; }
"""

def get_json(url: str, timeout: float = .7):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.load(response)
    except Exception:
        return None

def post_json(url: str, data: dict):
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=.8).read()
    except Exception:
        pass

class Display(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="uk.co.dallabs.PiBusNative")
        self.polling = False
        self.state = None

    def label(self, text="", css=None, x=0):
        widget = Gtk.Label(label=text, xalign=x)
        if css:
            widget.add_css_class(css)
        return widget

    def do_activate(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_decorated(False)
        self.window.set_default_size(800, 480)
        self.window.fullscreen()

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=180)
        self.stack.add_named(self.build_bus(), "bus")
        self.stack.add_named(self.build_roon(), "roon")
        self.stack.add_named(self.build_sleep(), "sleep")
        self.window.set_child(self.stack)
        self.window.present()

        GLib.timeout_add_seconds(1, self.tick)
        GLib.timeout_add_seconds(2, self.start_poll)
        self.tick()
        self.start_poll()

    def build_bus(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.add_css_class("page")
        top = Gtk.Box(spacing=12)
        heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        heading.set_hexpand(True)
        heading.append(self.label("PI BUS TIME DISPLAY", "eyebrow"))
        self.stop = self.label("Connecting...", "stop")
        heading.append(self.stop)
        self.bus_clock = self.label("--:--", "clock", 1)
        top.append(heading); top.append(self.bus_clock)
        page.append(top)
        self.services = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.services.set_vexpand(True)
        page.append(self.services)
        footer = Gtk.Box()
        self.bus_status = self.label("Starting", "muted")
        self.updated = self.label("", "muted", 1); self.updated.set_hexpand(True)
        footer.append(self.bus_status); footer.append(self.updated)
        page.append(footer)
        return page

    def build_roon(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.add_css_class("page")
        top = Gtk.Box()
        self.zone = self.label("ROON NOW PLAYING", "eyebrow")
        self.roon_clock = self.label("--:--", "clock", 1); self.roon_clock.set_hexpand(True)
        top.append(self.zone); top.append(self.roon_clock)
        page.append(top)
        centre = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        centre.set_valign(Gtk.Align.CENTER); centre.set_vexpand(True)
        self.title = self.label("Waiting for Roon...", "roon-title", .5)
        self.title.set_wrap(True); self.title.set_justify(Gtk.Justification.CENTER)
        self.artist = self.label("Enable Pi Bus Roon Controller in Roon", "roon-artist", .5)
        self.artist.set_wrap(True); self.artist.set_justify(Gtk.Justification.CENTER)
        centre.append(self.title); centre.append(self.artist)
        page.append(centre)
        controls = Gtk.Box(spacing=16)
        controls.set_halign(Gtk.Align.CENTER); controls.add_css_class("transport")
        self.prev = Gtk.Button(label="|<"); self.play = Gtk.Button(label="▶"); self.next = Gtk.Button(label=">|")
        self.play.add_css_class("play")
        self.prev.connect("clicked", lambda *_: self.control("previous"))
        self.play.connect("clicked", lambda *_: self.control("playpause"))
        self.next.connect("clicked", lambda *_: self.control("next"))
        controls.append(self.prev); controls.append(self.play); controls.append(self.next)
        page.append(controls)
        return page

    def build_sleep(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_halign(Gtk.Align.CENTER); box.set_valign(Gtk.Align.CENTER)
        self.sleep_clock = self.label("--:--", "sleep-clock", .5)
        box.append(self.sleep_clock)
        box.append(self.label("PI BUS", "eyebrow", .5))
        return box

    def tick(self):
        now = datetime.now(TZ).strftime("%H:%M")
        self.bus_clock.set_text(now); self.roon_clock.set_text(now); self.sleep_clock.set_text(now)
        return True

    def start_poll(self):
        if not self.polling:
            self.polling = True
            threading.Thread(target=self.poll, daemon=True).start()
        return True

    def poll(self):
        target = get_json(BUS + "/api/display-target") or {}
        status = get_json(BUS + "/api/status")
        roon = get_json(ROON + "/api/state")
        GLib.idle_add(self.apply, target.get("target", "/"), status, roon)
        self.polling = False

    def apply(self, target, status, roon):
        if target == "/sleep.html":
            self.stack.set_visible_child_name("sleep")
        elif target == "/" or target.endswith(":8765/"):
            self.render_bus(status)
            self.stack.set_visible_child_name("bus")
        else:
            self.render_roon(roon)
            self.stack.set_visible_child_name("roon")
        return False

    def render_bus(self, data):
        if not data:
            self.bus_status.set_text("Bus service unavailable")
            return
        self.stop.set_text(f"{data.get('stop_name', 'Bus times')}  ·  {data.get('stop_code', '')}")
        while child := self.services.get_first_child():
            self.services.remove(child)
        services = data.get("services", [])
        if not services:
            self.services.append(self.label("No services are currently reporting.", "muted", .5))
        for service in services[:4]:
            row = Gtk.Box(spacing=18); row.add_css_class("service")
            number = self.label(str(service.get("service", "")), "service-no"); number.set_size_request(105, -1)
            row.append(number)
            arrivals = Gtk.Box(spacing=24); arrivals.set_hexpand(True)
            for i, arrival in enumerate(service.get("arrivals", [])[:3]):
                col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                minutes = arrival.get("minutes")
                col.append(self.label("Due" if minutes == 0 else f"{minutes} min", "arrival", .5))
                col.append(self.label("LIVE" if arrival.get("monitored") else "SCHEDULED", "arrival-sub", .5))
                col.set_hexpand(True); arrivals.append(col)
            row.append(arrivals); self.services.append(row)
        stale = data.get("stale")
        self.bus_status.set_text("Live from LTA DataMall" if data.get("status") == "ok" and not stale else "Offline / last known arrivals")
        updated = data.get("updated_at")
        self.updated.set_text("Updated " + updated[11:19] if updated else "")

    def render_roon(self, data):
        self.state = data
        zone = (data or {}).get("zone")
        if not zone:
            self.zone.set_text("ROON")
            self.title.set_text("Waiting for Roon")
            self.artist.set_text("Start playback in Roon")
            self.prev.set_sensitive(False); self.play.set_sensitive(False); self.next.set_sensitive(False)
            return
        playing = zone.get("now_playing") or {}
        lines = playing.get("three_line") or playing.get("two_line") or playing.get("one_line") or {}
        self.zone.set_text(zone.get("name") or "ROON")
        self.title.set_text(lines.get("line1") or "Nothing playing")
        self.artist.set_text(" · ".join(filter(None, (lines.get("line2"), lines.get("line3")))) or "Roon")
        self.play.set_label("Ⅱ" if zone.get("state") == "playing" else "▶")
        self.prev.set_sensitive(bool(zone.get("can_previous")))
        self.next.set_sensitive(bool(zone.get("can_next")))
        self.play.set_sensitive(bool(zone.get("can_play") or zone.get("can_pause")))

    def control(self, action):
        threading.Thread(target=post_json, args=(ROON + "/api/control", {"action": action}), daemon=True).start()

if __name__ == "__main__":
    Display().run(None)
