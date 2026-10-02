#!/usr/bin/env python3
"""Native GTK4 touchscreen for Pi Home."""
from __future__ import annotations

import json
import os
import select
import struct
import threading
import time
import urllib.request
from queue import Queue
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango

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
.artwork-button { padding: 0; border-radius: 12px; background: transparent; }.detail-takeover { padding: 18px; background: rgba(6, 10, 9, .96); }.detail-panel { padding: 0; }.detail-artwork-button { padding: 0; border-radius: 12px; background: transparent; }.detail-artwork { border-radius: 12px; }.detail-title { font-size: 31px; font-weight: 650; }.detail-artist { color: #b6c0bc; font-size: 20px; }.detail-subtitle { color: #84908c; font-size: 13px; }.detail-writeup { color: #d3d9d6; font-size: 15px; line-height: 1.35; }.detail-source { color: #68736f; font-size: 10px; font-weight: 700; }.detail-facts { padding: 8px 0 10px; }.detail-fact { color: #a8b3af; font-size: 14px; font-weight: 600; }.detail-tracks { padding-top: 5px; }.detail-track { min-height: 30px; padding: 3px 6px; border-top: 1px solid #26312e; }.detail-track-no { color: #78837f; font-size: 11px; }.detail-track-title { color: #f4f0e6; font-size: 13px; }
.roon-subnav { margin-top: 0; }.roon-subnav button { min-height: 29px; padding: 4px 13px 2px; border-radius: 0; border-top: 3px solid transparent; background: transparent; color: #68736f; font-size: 10px; font-weight: 750; letter-spacing: 1px; }.roon-subnav button.active { border-top-color: #5bcbd6; color: #f4f0e6; }
.source-view { padding: 8px; }.source-title { font-size: 25px; font-weight: 700; }.source-volume { font-size: 104px; font-weight: 620; font-variant-numeric: tabular-nums; }.source-step { min-width: 92px; min-height: 92px; border-radius: 46px; background: #18211f; color: #f4f0e6; font-size: 45px; }.source-mute { min-width: 92px; min-height: 38px; border-radius: 8px; background: #18211f; color: #dfe4e1; font-size: 11px; font-weight: 750; }
.queue-scroll { background: transparent; }.queue-scroll scrollbar { opacity: 0; min-width: 0; min-height: 0; }.queue-list { padding: 5px 8px 8px; }.queue-row { min-height: 66px; padding: 5px 9px; border-radius: 8px; background: transparent; color: #f4f0e6; }.queue-row:hover, .queue-row:active { background: #18211f; }.queue-row.current { background: #121e1c; border-left: 3px solid #5bcbd6; }.queue-row.previous { opacity: .5; }.queue-art { min-width: 56px; min-height: 56px; border-radius: 5px; background: #18211f; }.queue-title { color: #f4f0e6; font-size: 16px; font-weight: 650; }.queue-meta { color: #84908c; font-size: 12px; }.queue-duration { color: #84908c; font-size: 12px; font-variant-numeric: tabular-nums; }.queue-empty { color: #78837f; font-size: 15px; padding: 60px 0; }
.transport button { min-width: 50px; min-height: 50px; border-radius: 25px; padding: 0; background: #18211f; color: #e4e7e4; }.transport .play { min-width: 68px; min-height: 68px; border-radius: 34px; background: #285f4d; }
.progress trough, .volume trough { min-height: 7px; border: 0; box-shadow: none; border-radius: 4px; background: #303a37; }.progress highlight, .volume highlight { border: 0; box-shadow: none; background: #6ed9ae; }.time { color: #87928e; font-size: 12px; }
.sleep { background: #000; }.sleep-clock { font-size: 112px; font-weight: 550; }.settings-title { font-size: 32px; font-weight: 650; }
.settings-card { background: #131c1a; border: 1px solid #26312e; border-radius: 14px; padding: 16px; }.settings-action { min-height: 54px; border-radius: 12px; background: #285f4d; color: #f4f0e6; font-weight: 750; }
.settings-select { min-height: 48px; border-radius: 8px; background: #0d1412; color: #f4f0e6; }.settings-row { padding: 7px 0; }.settings-diagnostic { color: #aab4b0; font-size: 12px; }
.settings-controls { padding: 4px 0; }.settings-column { padding: 0 5px; }.setting-line { min-height: 52px; padding: 0 12px; border-radius: 8px; background: #0d1412; }.setting-line label { font-size: 14px; font-weight: 650; }.setting-line checkbutton { font-size: 14px; font-weight: 650; }.setting-line checkbutton label { margin-left: 12px; }.setting-line check { min-width: 22px; min-height: 22px; border-radius: 5px; border: 2px solid #61706b; background: #111a18; }.setting-line check:checked { background: #6ed9ae; border-color: #6ed9ae; color: #082018; }
.brightness-setting { padding-top: 7px; padding-bottom: 7px; }
.stop-row { margin-bottom: 4px; }.home-grid { padding: 9px 0; }.home-tile { min-height: 120px; border-radius: 12px; padding: 10px 11px 8px; background: #131c1a; border: 1px solid #293633; color: #aab4b0; }.home-tile.on { background: #173229; border-color: #35785f; color: #f4f0e6; }.home-device-button { min-height: 92px; padding: 0; background: transparent; color: #9aaba5; }.home-tile.on .home-device-button { color: #6ed9ae; }.home-icon { opacity: .72; }.home-name { font-size: 15px; font-weight: 700; }.home-state { color: #7f8b87; font-size: 11px; }.home-level { min-width: 28px; min-height: 94px; }.home-level trough { min-width: 7px; border-radius: 4px; background: #303a37; }.home-level highlight { background: #6ed9ae; border-radius: 4px; }.home-level slider { min-width: 20px; min-height: 20px; border-radius: 10px; background: #f4f0e6; }
.high-resolution .page { padding: 21px 30px 15px; }.high-resolution .stop, .high-resolution .stop-code { font-size: 38px; }.high-resolution .clock { font-size: 47px; }.high-resolution .eyebrow { font-size: 17px; }.high-resolution .service { border-radius: 20px; padding: 8px 24px; }.high-resolution .service-no, .high-resolution .arrival { font-size: 123px; }.high-resolution .service.compact .service-no, .high-resolution .service.compact .arrival { font-size: 89px; }.high-resolution .service.dense .service-no, .high-resolution .service.dense .arrival { font-size: 68px; }.high-resolution .arrival-sub { font-size: 15px; }.high-resolution .muted { font-size: 16px; }.high-resolution .artwork { min-width: 420px; min-height: 420px; }.high-resolution .roon-title { font-size: 52px; }.high-resolution .roon-artist { font-size: 27px; }.high-resolution .nav button { min-height: 60px; font-size: 21px; }
.high-resolution .roon-subnav button { min-height: 44px; font-size: 15px; }.high-resolution .transport button { min-width: 75px; min-height: 75px; border-radius: 38px; }.high-resolution .transport .play { min-width: 96px; min-height: 96px; border-radius: 48px; }.high-resolution .queue-row { min-height: 99px; }.high-resolution .queue-art { min-width: 84px; min-height: 84px; }.high-resolution .queue-title { font-size: 24px; }.high-resolution .queue-meta, .high-resolution .queue-duration { font-size: 18px; }.high-resolution .detail-title { font-size: 47px; }.high-resolution .detail-artist { font-size: 30px; }.high-resolution .detail-track-title { font-size: 20px; }
.touch-landscape .page { padding: 18px 28px 14px; }.touch-landscape .service-no, .touch-landscape .arrival { font-size: 138px; }.touch-landscape .service-no { min-width: 205px; }.touch-landscape .arrival-sub { font-size: 17px; }.touch-landscape .stop, .touch-landscape .stop-code { font-size: 42px; }.touch-landscape .clock { font-size: 50px; }.touch-landscape .nav button { min-height: 58px; font-size: 22px; }.touch-landscape .roon-subnav button { min-height: 54px; padding: 8px 18px 5px; font-size: 18px; }.touch-landscape .artwork { min-width: 324px; min-height: 324px; }.touch-landscape .roon-title { font-size: 46px; }.touch-landscape .roon-artist { font-size: 25px; }.touch-landscape .transport button { min-width: 70px; min-height: 70px; border-radius: 35px; }.touch-landscape .transport .play { min-width: 88px; min-height: 88px; border-radius: 44px; }.touch-landscape .settings-title { font-size: 43px; }.touch-landscape .settings-card { padding: 24px 28px; }.touch-landscape .settings-card .muted, .touch-landscape .settings-diagnostic { font-size: 17px; }.touch-landscape .settings-select { min-height: 70px; font-size: 19px; }.touch-landscape .setting-line { min-height: 78px; padding: 0 18px; }.touch-landscape .setting-line label, .touch-landscape .setting-line checkbutton { font-size: 19px; }.touch-landscape .setting-line check { min-width: 30px; min-height: 30px; }.touch-landscape .settings-action { min-height: 74px; font-size: 20px; }.touch-landscape .settings-controls { padding: 12px 0; }.touch-landscape .utility { min-width: 118px; min-height: 52px; font-size: 16px; }
.boot-splash { background: #000; }.boot-logo { color: #6ef0be; font-size: 62px; font-weight: 760; letter-spacing: 9px; }
.touch-landscape .header-title { transform: translateY(-5px); }
.touch-landscape .stop, .touch-landscape .stop-code { font-size: 34px; }
.touch-landscape .stop-row { margin-bottom: 14px; }
.touch-landscape .service { border-width: 2px; padding-top: 11px; padding-bottom: 11px; }
.touch-landscape .home-tile { border-width: 2px; }
.touch-landscape .bus-page { padding-top: 10px; }.touch-landscape .bus-footer .muted { color: #68736f; }.touch-landscape .service-no { opacity: .82; }
.touch-landscape .home-name { font-size: 24px; }.touch-landscape .home-state { font-size: 17px; }
.touch-landscape .home-page { padding-top: 10px; }
.touch-landscape .roon-page { padding-top: 8px; }
.touch-landscape .roon-subnav button { min-height: 42px; padding: 2px 14px 4px; }
.touch-landscape .source-volume { font-size: 220px; font-weight: 450; }.touch-landscape .source-step { min-width: 112px; min-height: 112px; border-radius: 56px; font-size: 58px; }.touch-landscape .source-mute { min-width: 160px; min-height: 62px; font-size: 20px; }
.touch-landscape .time { font-size: 20px; }.touch-landscape .volume-number { font-size: 26px; }
.touch-landscape .settings-page { padding-top: 18px; padding-bottom: 18px; }.touch-landscape .settings-page button { padding: 8px 20px; }
.touch-landscape .settings-page .settings-card { padding: 8px 10px; border: 0; background: transparent; }
.touch-landscape .settings-page .setting-line { min-height: 72px; padding: 5px 18px; }.touch-landscape .settings-page .setting-line checkbutton label { margin-left: 16px; }
.touch-landscape .settings-page .brightness-setting { padding-top: 6px; padding-bottom: 6px; }
.touch-landscape .settings-page .settings-select { min-height: 62px; padding: 5px 18px; }
.touch-landscape .settings-page .settings-diagnostic { line-height: 1.25; }
.touch-landscape .settings-page .settings-action { min-height: 62px; }
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
        self.roon_nav_buttons = []
        self.home_value_timeouts = {}
        self.brightness_updating = False
        self.brightness_timeout = None
        self.brightness_applied = False
        self.update_in_progress = False
        self.update_status_seen = False
        self.views_prewarmed = False
        self.started_at = time.monotonic()
        self.refresh_count = 0
        self.queue_signature = None
        self.queue_thumbnail_jobs = Queue()
        self.queue_thumbnail_pending = set()
        self.queue_thumbnail_cache = {}
        self.queue_thumbnail_order = []
        self.queue_pictures = {}
        self.queue_artwork_keys = []
        self.last_interaction = time.monotonic()
        self.inactivity_sleeping = False
        self.sleep_entered_at = 0.0
        self.requested_audio_view = "now"
        self.last_active_input = ""
        self.detail_image_key = None
        self.detail_signature = None
        self.bluos_source_buttons = {}

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
        image = Gtk.Image.new_from_icon_name(icon); image.set_pixel_size(34); widget.set_child(image)
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
        activity = Gtk.EventControllerLegacy(); activity.set_propagation_phase(Gtk.PropagationPhase.CAPTURE); activity.connect("event", self.note_activity); self.window.add_controller(activity)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.NONE, transition_duration=0)
        self.stack.set_hhomogeneous(False); self.stack.set_vhomogeneous(False)
        self.stack.add_named(self.build_boot_splash(), "boot"); self.stack.add_named(self.build_bus(), "bus"); self.stack.add_named(self.build_roon(), "roon"); self.stack.add_named(self.build_home(), "home"); self.stack.add_named(self.build_settings(), "settings"); self.stack.add_named(self.build_sleep(), "sleep")
        self.window.set_child(self.stack); self.window.present()
        threading.Thread(target=self.thumbnail_worker, daemon=True).start()
        threading.Thread(target=self.touchscreen_wake_worker, daemon=True).start()
        GLib.idle_add(self.adapt_display)
        GLib.timeout_add_seconds(1, self.tick); GLib.timeout_add_seconds(2, self.start_poll); self.tick(); self.start_poll()

    def adapt_display(self):
        monitors = Gdk.Display.get_default().get_monitors()
        monitor = monitors.get_item(0) if monitors.get_n_items() else None
        if monitor:
            geometry = monitor.get_geometry()
            self.detail_artwork.set_size_request(max(320, min(geometry.width, geometry.height) - 60), max(320, min(geometry.width, geometry.height) - 60))
            if max(geometry.width, geometry.height) >= 1200: self.window.add_css_class("high-resolution")
            if geometry.width >= 1200 and geometry.width > geometry.height:
                self.window.add_css_class("touch-landscape")
                # A CSS min-size still lets GTK stretch this child to its former
                # allocation. Constrain both the picture and its button so the
                # landscape artwork is genuinely ten percent smaller.
                self.artwork.set_size_request(324, 324)
                self.artwork_button.set_size_request(324, 324)
        return False

    def header(self, centre, clock):
        row = Gtk.Box(spacing=10)
        centre.set_xalign(0)
        title = Gtk.Button(); title.add_css_class("header-hotspot"); title.add_css_class("header-title"); title.set_child(centre); title.connect("clicked", self.open_settings); row.append(title)
        spacer = Gtk.Box(); spacer.set_hexpand(True); row.append(spacer)
        clock.set_xalign(1)
        clock_button = Gtk.Button(); clock_button.add_css_class("header-hotspot"); clock_button.add_css_class("header-clock"); clock_button.set_child(clock); clock_button.connect("clicked", self.sleep); row.append(clock_button)
        return row

    def navigation(self, active):
        row = Gtk.Box(spacing=8); row.add_css_class("nav")
        now = self.button("Roon", lambda *_: self.set_mode("roon"), ""); self.roon_nav_buttons.append(now)
        bus = self.button("Bus Times", lambda *_: self.set_mode("bus"), "")
        home = self.button("Home", lambda *_: self.set_mode("home"), ""); self.home_nav_buttons.append(home)
        {"roon": now, "bus": bus, "home": home}.get(active, bus).add_css_class("active")
        for button in (now, bus, home): button.set_hexpand(True); row.append(button)
        return row

    def build_boot_splash(self):
        page = Gtk.Box(); page.add_css_class("boot-splash"); page.set_hexpand(True); page.set_vexpand(True)
        logo = self.label("PI HOME", "boot-logo", .5); logo.set_halign(Gtk.Align.CENTER); logo.set_valign(Gtk.Align.CENTER); logo.set_hexpand(True); logo.set_vexpand(True); page.append(logo)
        return page

    def build_bus(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); page.add_css_class("page"); page.add_css_class("bus-page")
        self.bus_clock = self.label("--:--", "clock", 1); page.append(self.header(self.label("PI HOME", "eyebrow"), self.bus_clock))
        stop_row = Gtk.Box(spacing=8); stop_row.add_css_class("stop-row"); stop_row.set_halign(Gtk.Align.CENTER); self.stop = self.label("Connecting…", "stop"); self.stop_code = self.label("", "stop-code"); stop_row.append(self.stop); stop_row.append(self.stop_code); page.append(stop_row)
        self.services = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14); self.services.set_vexpand(True); page.append(self.services)
        footer = Gtk.Box(); footer.add_css_class("bus-footer"); self.bus_status = self.label("Starting", "muted"); self.updated = self.label("", "muted", 1); self.updated.set_hexpand(True); footer.append(self.bus_status); footer.append(self.updated); page.append(footer)
        page.append(self.navigation("bus")); return page

    def build_roon(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); page.add_css_class("page"); page.add_css_class("roon-page")
        self.zone = self.label("ROON NOW PLAYING", "eyebrow"); self.roon_clock = self.label("--:--", "clock", 1)
        header_overlay = Gtk.Overlay(); header_overlay.set_child(self.header(self.zone, self.roon_clock))
        subnav = Gtk.Box(spacing=12); subnav.add_css_class("roon-subnav"); subnav.set_halign(Gtk.Align.CENTER); subnav.set_valign(Gtk.Align.START); self.roon_subnav = subnav
        self.now_playing_tab = self.button("NOW PLAYING", self.show_roon_now, ""); self.now_playing_tab.add_css_class("active")
        self.queue_tab = self.button("QUEUE", lambda *_: self.set_roon_view("queue"), ""); subnav.append(self.now_playing_tab); subnav.append(self.queue_tab)
        header_overlay.add_overlay(subnav); page.append(header_overlay)
        self.roon_views = Gtk.Stack(transition_type=Gtk.StackTransitionType.NONE, transition_duration=0); self.roon_views.set_vexpand(True)
        self.roon_views.set_hhomogeneous(False); self.roon_views.set_vhomogeneous(False)
        content = Gtk.Box(spacing=26); content.set_vexpand(True); content.set_margin_start(8); content.set_margin_end(8); content.set_margin_top(8); content.set_margin_bottom(8)
        self.artwork = Gtk.Picture(); self.artwork.add_css_class("artwork"); self.artwork.set_size_request(280, 280); self.artwork.set_valign(Gtk.Align.CENTER); self.artwork.set_content_fit(Gtk.ContentFit.COVER)
        artwork_button = Gtk.Button(); artwork_button.add_css_class("artwork-button"); artwork_button.set_halign(Gtk.Align.CENTER); artwork_button.set_valign(Gtk.Align.CENTER); artwork_button.set_child(self.artwork); artwork_button.connect("clicked", lambda *_: self.set_roon_view("details")); content.append(artwork_button); self.artwork_button = artwork_button
        centre = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); centre.set_valign(Gtk.Align.CENTER); centre.set_hexpand(True)
        self.title = self.label("Waiting for Roon…", "roon-title", .5); self.title.set_wrap(True); self.title.set_lines(2); self.title.set_justify(Gtk.Justification.CENTER)
        self.artist = self.label("Enable Pi Home Roon Controller in Roon", "roon-artist", .5); self.artist.set_wrap(True); self.artist.set_justify(Gtk.Justification.CENTER); centre.append(self.title); centre.append(self.artist)
        self.progress = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1); self.progress.add_css_class("progress"); self.progress.set_draw_value(False); self.progress.set_sensitive(False); self.progress.connect("value-changed", self.change_seek); centre.append(self.progress)
        times = Gtk.Box(); self.elapsed = self.label("0:00", "time"); self.remaining = self.label("−0:00", "time", 1); self.remaining.set_hexpand(True); times.append(self.elapsed); times.append(self.remaining); centre.append(times); self.roon_times = times
        self.controls = Gtk.Box(spacing=14); self.controls.set_halign(Gtk.Align.CENTER); self.controls.add_css_class("transport")
        self.controls.set_margin_top(6); self.controls.set_margin_bottom(16)
        self.prev = self.icon_button("media-skip-backward-symbolic", lambda *_: self.control("previous")); self.play = self.icon_button("media-playback-start-symbolic", lambda *_: self.control("playpause"), "play"); self.play.get_child().set_pixel_size(42); self.next = self.icon_button("media-skip-forward-symbolic", lambda *_: self.control("next"))
        self.prev.set_size_request(50, 50); self.prev.set_valign(Gtk.Align.CENTER); self.play.set_size_request(68, 68); self.play.set_valign(Gtk.Align.CENTER); self.next.set_size_request(50, 50); self.next.set_valign(Gtk.Align.CENTER)
        self.controls.append(self.prev); self.controls.append(self.play); self.controls.append(self.next); centre.append(self.controls)
        volume_row = Gtk.Box(spacing=10); self.mute = self.button("MUTE", self.toggle_audio_mute, "utility"); self.mute.set_size_request(62, 38); volume_row.append(self.mute); self.volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1); self.volume.add_css_class("volume"); self.volume.set_hexpand(True); self.volume.set_draw_value(False); self.volume.connect("value-changed", self.change_volume); volume_row.append(self.volume); self.volume_value = self.label("—", "time", 1); self.volume_value.add_css_class("volume-number"); volume_row.append(self.volume_value); centre.append(volume_row)
        content.append(centre); self.roon_views.add_named(content, "now")
        source = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); source.add_css_class("source-view"); source.set_halign(Gtk.Align.CENTER); source.set_valign(Gtk.Align.CENTER); source.set_hexpand(True); source.set_vexpand(True)
        self.source_title = self.label("EXTERNAL INPUT", "source-title", .5); source.append(self.source_title)
        source_volume = Gtk.Box(spacing=28); source_volume.set_halign(Gtk.Align.CENTER); source_volume.set_valign(Gtk.Align.CENTER)
        source_down = self.button("−", lambda *_: self.step_bluos_volume(-2), "source-step"); source_down.set_size_request(112, 112); source_down.set_halign(Gtk.Align.CENTER); source_down.set_valign(Gtk.Align.CENTER); source_volume.append(source_down)
        self.source_volume = self.label("—", "source-volume", .5); self.source_volume.set_size_request(230, -1); source_volume.append(self.source_volume)
        source_up = self.button("+", lambda *_: self.step_bluos_volume(2), "source-step"); source_up.set_size_request(112, 112); source_up.set_halign(Gtk.Align.CENTER); source_up.set_valign(Gtk.Align.CENTER); source_volume.append(source_up); source.append(source_volume)
        self.source_mute = self.button("MUTE", self.toggle_audio_mute, "source-mute"); self.source_mute.set_halign(Gtk.Align.CENTER); source.append(self.source_mute); self.roon_views.add_named(source, "source")
        self.queue_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2); self.queue_list.add_css_class("queue-list")
        queue_scroll = Gtk.ScrolledWindow(); queue_scroll.add_css_class("queue-scroll"); queue_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); queue_scroll.set_kinetic_scrolling(True); queue_scroll.set_overlay_scrolling(True); queue_scroll.set_propagate_natural_height(False); queue_scroll.set_propagate_natural_width(False); queue_scroll.set_min_content_height(1); queue_scroll.set_size_request(-1, 1); queue_scroll.set_vexpand(True); queue_scroll.set_hexpand(True); queue_scroll.set_child(self.queue_list); self.queue_scroll = queue_scroll
        queue_scroll.get_vadjustment().connect("value-changed", self.load_visible_queue_artwork)
        self.roon_views.add_named(queue_scroll, "queue")
        detail_panel = Gtk.Box(spacing=24); detail_panel.add_css_class("detail-panel"); detail_panel.set_hexpand(True); detail_panel.set_vexpand(True)
        self.detail_artwork = Gtk.Picture(); self.detail_artwork.add_css_class("detail-artwork"); self.detail_artwork.set_size_request(420, 420); self.detail_artwork.set_content_fit(Gtk.ContentFit.COVER); self.detail_artwork.set_valign(Gtk.Align.CENTER)
        detail_artwork_button = Gtk.Button(); detail_artwork_button.add_css_class("detail-artwork-button"); detail_artwork_button.set_halign(Gtk.Align.CENTER); detail_artwork_button.set_valign(Gtk.Align.CENTER); detail_artwork_button.set_child(self.detail_artwork); detail_artwork_button.connect("clicked", lambda *_: self.set_roon_view("now")); detail_panel.append(detail_artwork_button)
        detail_copy = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6); detail_copy.set_hexpand(True); detail_copy.set_vexpand(True); detail_copy.set_valign(Gtk.Align.FILL)
        detail_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6); detail_content.set_valign(Gtk.Align.CENTER); detail_content.set_vexpand(True)
        detail_content.append(self.label("ALBUM & ARTIST", "eyebrow"))
        self.detail_title = self.label("Nothing playing", "detail-title"); self.detail_title.set_wrap(True); self.detail_title.set_lines(2); self.detail_title.set_ellipsize(Pango.EllipsizeMode.END); detail_content.append(self.detail_title)
        self.detail_artist = self.label("", "detail-artist"); self.detail_artist.set_wrap(True); detail_content.append(self.detail_artist)
        self.detail_subtitle = self.label("", "detail-subtitle"); self.detail_subtitle.set_wrap(True); detail_content.append(self.detail_subtitle)
        self.detail_writeup = self.label("", "detail-writeup"); self.detail_writeup.set_wrap(True); self.detail_writeup.set_lines(5); self.detail_writeup.set_ellipsize(Pango.EllipsizeMode.END); detail_content.append(self.detail_writeup)
        self.detail_source = self.label("", "detail-source"); detail_content.append(self.detail_source)
        self.detail_facts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); self.detail_facts.add_css_class("detail-facts"); detail_content.append(self.detail_facts)
        self.detail_tracks = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); self.detail_tracks.add_css_class("detail-tracks")
        detail_scroll = Gtk.ScrolledWindow(); detail_scroll.add_css_class("queue-scroll"); detail_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); detail_scroll.set_kinetic_scrolling(True); detail_scroll.set_overlay_scrolling(True); detail_scroll.set_propagate_natural_height(True); detail_scroll.set_max_content_height(210); detail_scroll.set_child(self.detail_tracks); detail_content.append(detail_scroll)
        detail_copy.append(detail_content)
        detail_panel.append(detail_copy); page.append(self.roon_views); page.append(self.navigation("roon"))
        takeover = Gtk.Box(); takeover.add_css_class("detail-takeover"); takeover.set_hexpand(True); takeover.set_vexpand(True)
        takeover.append(detail_panel); takeover.set_visible(False); self.detail_takeover = takeover
        root = Gtk.Overlay(); root.set_child(page); root.add_overlay(takeover); return root

    def build_home(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); page.add_css_class("page"); page.add_css_class("home-page")
        self.home_clock = self.label("--:--", "clock", 1); page.append(self.header(self.label("PI HOME", "eyebrow"), self.home_clock))
        self.home_status = self.label("Connecting to Home Assistant…", "muted", .5); page.append(self.home_status)
        self.home_grid = Gtk.Grid(column_spacing=11, row_spacing=11); self.home_grid.add_css_class("home-grid"); self.home_grid.set_column_homogeneous(True); self.home_grid.set_row_homogeneous(True); self.home_grid.set_vexpand(True); page.append(self.home_grid)
        page.append(self.navigation("home")); return page

    def build_settings(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); page.add_css_class("page"); page.add_css_class("settings-page")
        top = Gtk.Box(spacing=10); top.append(self.button("BACK", self.close_settings)); title = self.label("Settings", "settings-title", .5); title.set_hexpand(True); top.append(title); top.append(self.button("SLEEP", self.sleep)); page.append(top)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14); card.add_css_class("settings-card"); card.set_vexpand(True)
        self.device_status = self.label("Checking system…", "muted", .5); card.append(self.device_status)
        self.touch_diagnostics = self.label("Loading diagnostics…", "settings-diagnostic", .5); self.touch_diagnostics.set_wrap(True); self.touch_diagnostics.set_justify(Gtk.Justification.CENTER); self.touch_diagnostics.set_margin_top(8); self.touch_diagnostics.set_margin_bottom(14); card.append(self.touch_diagnostics)
        controls = Gtk.Box(spacing=28); controls.add_css_class("settings-controls"); controls.set_vexpand(True); controls.set_valign(Gtk.Align.CENTER)
        daily = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16); daily.add_css_class("settings-column"); daily.set_size_request(430, -1); daily.append(self.label("DAILY CONTROLS", "eyebrow")); self.touch_daily = daily; controls.append(daily)
        display_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16); display_column.add_css_class("settings-column"); display_column.set_hexpand(True); display_column.append(self.label("DISPLAY", "eyebrow"))
        self.touch_profile = Gtk.DropDown.new_from_strings(["Profile · Original 800×480", "Profile · Touch 2 5-inch", "Profile · Touch 2 7-inch", "Profile · Touch 2 10-inch"]); self.touch_profile.add_css_class("settings-select"); display_column.append(self.touch_profile)
        self.touch_orientation = Gtk.DropDown.new_from_strings(["Orientation · Normal", "Orientation · 90°", "Orientation · 180°", "Orientation · 270°"]); self.touch_orientation.add_css_class("settings-select"); display_column.append(self.touch_orientation); controls.append(display_column); card.append(controls)
        brightness_row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3); brightness_row.add_css_class("setting-line"); brightness_row.add_css_class("brightness-setting"); brightness_row.append(self.label("Display brightness", "muted")); self.touch_brightness = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 100, 1); self.touch_brightness.set_draw_value(True); self.touch_brightness.set_value_pos(Gtk.PositionType.RIGHT); self.touch_brightness.connect("value-changed", self.change_brightness); brightness_row.append(self.touch_brightness); display_column.append(brightness_row)
        actions = Gtk.Box(spacing=12); actions.set_valign(Gtk.Align.END); self.apply_display_button = self.button("APPLY DISPLAY", self.request_display_settings, "settings-action"); self.apply_display_button.set_hexpand(True); actions.append(self.apply_display_button); self.update_button = self.button("INSTALL UPDATE", self.request_update, "settings-action"); self.update_button.set_hexpand(True); actions.append(self.update_button); card.append(actions); page.append(card)
        return page

    def build_sleep(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); box.add_css_class("sleep"); box.set_halign(Gtk.Align.FILL); box.set_valign(Gtk.Align.FILL); box.set_hexpand(True); box.set_vexpand(True)
        centre = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); centre.set_halign(Gtk.Align.CENTER); centre.set_valign(Gtk.Align.CENTER); centre.set_hexpand(True); centre.set_vexpand(True)
        self.sleep_clock = self.label("--:--", "sleep-clock", .5); centre.append(self.sleep_clock); self.sleep_hint = self.label("TAP ANYWHERE TO WAKE", "eyebrow", .5); centre.append(self.sleep_hint); box.append(centre)
        wake_gesture = Gtk.GestureClick(); wake_gesture.set_button(0); wake_gesture.connect("pressed", self.sleep_gesture_pressed); box.add_controller(wake_gesture)
        return box

    def sleep_gesture_pressed(self, _gesture, _count, _x, _y):
        if time.monotonic() - self.sleep_entered_at >= .45: self.wake("sleep gesture")

    def touchscreen_devices(self):
        devices = []
        for event_path in sorted(Path("/sys/class/input").glob("event*")):
            try: name = (event_path / "device/name").read_text(encoding="utf-8").strip().lower()
            except OSError: continue
            if any(token in name for token in ("touchscreen", "touch display", "raspberrypi-ts", "dsi touch", "ft5406", "edt-ft", "goodix")):
                device = Path("/dev/input") / event_path.name
                if device.exists(): devices.append((device, name))
        return devices

    def touchscreen_wake_worker(self):
        event_struct = struct.Struct("llHHI")
        while True:
            handles = []
            try:
                for device, name in self.touchscreen_devices():
                    try:
                        handle = os.open(device, os.O_RDONLY | os.O_NONBLOCK); handles.append((handle, name))
                    except OSError: continue
                if not handles:
                    time.sleep(5); continue
                print("Pi Home low-level wake listening on " + ", ".join(name for _, name in handles), flush=True)
                while True:
                    readable, _, _ = select.select([handle for handle, _ in handles], [], [], 30)
                    for handle in readable:
                        try: packet = os.read(handle, event_struct.size * 32)
                        except OSError: continue
                        for offset in range(0, len(packet) - event_struct.size + 1, event_struct.size):
                            _sec, _usec, event_type, code, value = event_struct.unpack_from(packet, offset)
                            # Goodix panels can announce a new contact as
                            # BTN_TOUCH or as an MT tracking id. Accept either
                            # real contact start, but ignore coordinate motion.
                            button_touch = event_type == 1 and code == 330 and value == 1
                            tracking_start = event_type == 3 and code == 57 and value != 0xFFFFFFFF
                            if button_touch or tracking_start:
                                GLib.idle_add(self.low_level_touch_wake)
            finally:
                for handle, _name in handles:
                    try: os.close(handle)
                    except OSError: pass
            time.sleep(1)

    def low_level_touch_wake(self):
        if self.inactivity_sleeping or (self.stack.get_visible_child_name() == "sleep" and time.monotonic() - self.sleep_entered_at >= .45): self.wake("Linux touchscreen event")
        return False

    def tick(self):
        now = datetime.now(TZ).strftime("%H:%M"); self.bus_clock.set_text(now); self.roon_clock.set_text(now); self.home_clock.set_text(now); self.sleep_clock.set_text(now); return True

    def start_poll(self):
        if not self.polling:
            self.polling = True; threading.Thread(target=self.poll, daemon=True).start()
        return True

    def poll(self):
        started = time.monotonic()
        target_response = get_json(BUS + "/api/display-target"); status = get_json(BUS + "/api/status"); roon = get_json(ROON + "/api/state"); device = get_json(BUS + "/api/device/controls") or {}
        now = time.monotonic(); config = None; system = None
        if not self.settings_data or now - self.last_config_fetch >= 60:
            config = get_json(BUS + "/api/admin/config") or {}; self.last_config_fetch = now
        if self.settings_open and (not self.system_data or self.update_in_progress or now - self.last_system_fetch >= 15):
            system = get_json(BUS + "/api/admin/system?diagnostics=1") or {}; self.last_system_fetch = now
        zone = (roon or {}).get("zone") or {}; key = (zone.get("now_playing") or {}).get("image_key")
        details = (roon or {}).get("details") or {}; detail_key = details.get("artist_image_key") or details.get("album_image_key") or details.get("image_key")
        target = target_response.get("target") if isinstance(target_response, dict) else None
        GLib.idle_add(self.apply, target, status, roon, config, system, device, key, None)
        self.polling = False
        image = get_bytes(f"{ROON}/api/image?key={quote(key, safe='')}") if key and key != self.image_key else None
        if image:
            GLib.idle_add(self.apply_artwork, key, image)
        detail_image = get_bytes(f"{ROON}/api/image?key={quote(detail_key, safe='')}&size=600") if detail_key and detail_key != self.detail_image_key else None
        if detail_image:
            GLib.idle_add(self.apply_detail_artwork, detail_key, detail_image)
        elapsed = time.monotonic() - started; self.refresh_count += 1
        if self.refresh_count <= 5 and elapsed > .25:
            print(f"Pi Home core refresh completed in {elapsed:.3f}s", flush=True)

    def apply(self, target, status, roon, config, system, device, image_key, image):
        if config is not None:
            self.settings_data = config
            for button in self.roon_nav_buttons: button.set_label(config.get("roon_display_name") or "Roon")
            self.now_playing_tab.set_label((config.get("roon_now_playing_name") or "Now Playing").upper())
            self.queue_tab.set_label((config.get("roon_queue_name") or "Queue").upper())
            self.controls.set_visible(config.get("roon_show_controls", True)); self.roon_clock.set_visible(config.get("roon_show_clock", True))
            self.roon_subnav.set_visible(True); self.queue_tab.set_visible(config.get("roon_show_queue", True))
            if not config.get("roon_show_queue", True) and self.roon_views.get_visible_child_name() == "queue": self.set_roon_view("now")
            show_sleep_clock = config.get("sleep_show_clock", False); self.sleep_clock.set_visible(show_sleep_clock); self.sleep_hint.set_visible(show_sleep_clock)
            for button in self.home_nav_buttons: button.set_visible(bool(config.get("home_assistant_enabled") and config.get("home_assistant_entities")))
        if system is not None:
            self.system_data = system
            update_status = str(system.get("update_status", "Ready"))
            self.device_status.set_text(f"v{system.get('app_version', '—')}  ·  {update_status}")
            if update_status.startswith("Update ·"):
                self.update_status_seen = True
            elif self.update_in_progress and self.update_status_seen:
                self.update_in_progress = False
                self.update_button.set_sensitive(True)
            if update_status.startswith("Failed:"):
                self.update_button.set_sensitive(True)
            diagnostics = system.get("diagnostics") or {}; memory = diagnostics.get("memory") or {}; processes = diagnostics.get("processes") or []
            states = {item.get("label"): item.get("active", bool(item.get("pids"))) for item in processes}
            temperature = diagnostics.get("temperature_c"); load = diagnostics.get("load") or [0]
            health = f"Memory {memory.get('used_percent', 0):g}%  ·  Load {float(load[0]):.2f}"
            if temperature is not None: health += f"  ·  {temperature:g}°C"
            health += f"  ·  Controller {'ready' if states.get('Roon controller') else 'offline'}  ·  Bridge {'ready' if states.get('Roon Bridge') else 'offline'}"
            self.touch_diagnostics.set_text(health)
            if not self.display_controls_loaded:
                profiles = {"original": 0, "touch2-5": 1, "touch2-7": 2, "touch2-5-7": 2, "touch2-10": 3}; orientations = {"normal": 0, "90": 1, "180": 2, "270": 3}
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
        scheduled_wake = bool(
            target is not None
            and target != "/sleep.html"
            and self.stack.get_visible_child_name() == "sleep"
            and not self.inactivity_sleeping
        )
        if scheduled_wake:
            # Overnight time must not count towards daytime inactivity. Without
            # this reset, the wake boundary and inactivity sleep happen in the
            # same refresh and the panel appears never to wake.
            self.last_interaction = time.monotonic()
            print("Pi Home resuming at the scheduled wake boundary", flush=True)
        inactivity_seconds = max(0, int(config.get("daytime_inactivity_seconds", 0) or 0))
        inactivity_due = bool(inactivity_seconds and time.monotonic() - self.last_interaction >= inactivity_seconds and target != "/sleep.html")
        if inactivity_due and not self.inactivity_sleeping:
            self.inactivity_sleeping = True
            print(f"Pi Home sleeping after {inactivity_seconds}s without a touch", flush=True)
        if self.settings_open and target != "/sleep.html" and not self.inactivity_sleeping:
            return False
        if target is None and not self.inactivity_sleeping:
            # A transient backend timeout must not wake a sleeping panel or force Bus Times.
            return False
        if target == "/sleep.html":
            self.settings_open = False; self.inactivity_sleeping = False; desired = "sleep"
            if self.stack.get_visible_child_name() != "sleep": self.prepare_sleep_wake()
            self.set_screen_power(bool(config.get("sleep_show_clock", False)))
        elif self.inactivity_sleeping: self.settings_open = False; desired = "sleep"; self.set_screen_power(False)
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

    def apply_detail_artwork(self, image_key, image):
        try:
            self.detail_artwork.set_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(image))); self.detail_image_key = image_key
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
            icon_path = Path(__file__).with_name("icons") / icon_name
            icon_size = 108 if self.window.has_css_class("high-resolution") else 72
            icon = Gtk.Image.new_from_gicon(Gio.FileIcon.new(Gio.File.new_for_path(str(icon_path)))); icon.set_pixel_size(icon_size); icon.set_size_request(icon_size, icon_size); icon.set_halign(Gtk.Align.CENTER); icon.set_valign(Gtk.Align.CENTER); icon.add_css_class("home-icon")
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
            number = self.label(str(service.get("service", "")), "service-no"); number.set_size_request((150 if len(visible) > 2 else 188) if self.window.has_css_class("high-resolution") else (100 if len(visible) > 2 else 125), -1); number.set_valign(Gtk.Align.CENTER); row.append(number)
            arrivals = Gtk.Box(spacing=8); arrivals.set_hexpand(True)
            for arrival in service.get("arrivals", [])[:3]:
                col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); col.set_valign(Gtk.Align.CENTER); minutes = arrival.get("minutes"); col.append(self.label("Due" if minutes == 0 else str(minutes), "arrival", .5)); col.append(self.label("MIN · LIVE" if arrival.get("monitored") else "MIN · AFTER", "arrival-sub", .5)); col.set_hexpand(True); arrivals.append(col)
            row.append(arrivals); self.services.append(row)
        self.bus_status.set_text("Live from LTA DataMall" if data.get("status") == "ok" and not data.get("stale") else "Offline / last known arrivals")
        updated = data.get("updated_at"); self.updated.set_text("Updated " + updated[11:19] if updated else "")

    def render_roon(self, data):
        self.state = data; self.render_queue((data or {}).get("queue") or {}); self.render_details((data or {}).get("details") or {}); zone = (data or {}).get("zone")
        amplifier = (data or {}).get("amplifier") or {}; active_input = amplifier.get("active_input")
        active_id = str((active_input or {}).get("id") or "")
        if active_id != self.last_active_input:
            if active_id: self.requested_audio_view = "source"
            elif self.last_active_input and self.requested_audio_view == "source": self.requested_audio_view = "now"
            self.last_active_input = active_id
        self.render_bluos_inputs(amplifier, bool(zone))
        external = bool(amplifier.get("connected") and active_input)
        external_view = external and self.requested_audio_view == "source"
        self.artwork_button.set_visible(not external_view); self.controls.set_visible(not external_view and self.settings_data.get("roon_show_controls", True)); self.progress.set_visible(not external_view); self.roon_times.set_visible(not external_view); self.roon_subnav.set_sensitive(True); self.queue_tab.set_sensitive(True)
        if external_view:
            player = amplifier.get("player") or {}; volume = amplifier.get("volume") or {}; value = volume.get("value")
            self.zone.set_text(player.get("name") or player.get("model") or "BLUOS"); self.source_title.set_text((active_input.get("name") or "External input").upper()); self.source_volume.set_text(str(round(value)) if value is not None else "—"); self.source_mute.set_sensitive(value is not None); self.source_mute.set_label("UNMUTE" if volume.get("muted") else "MUTE")
            self.set_roon_view("source")
            return
        if self.roon_views.get_visible_child_name() == "source": self.set_roon_view(self.requested_audio_view if self.requested_audio_view != "source" else "now")
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
        play_icon = Gtk.Image.new_from_icon_name("media-playback-start-symbolic" if external else ("media-playback-pause-symbolic" if zone.get("state") == "playing" else "media-playback-start-symbolic")); play_icon.set_pixel_size(42); self.play.set_child(play_icon); self.prev.set_sensitive(not external and bool(zone.get("can_previous"))); self.next.set_sensitive(not external and bool(zone.get("can_next"))); self.play.set_sensitive(bool(zone.get("can_play") or zone.get("can_pause")))
        elapsed = int(zone.get("seek_position") or 0); length = int(playing.get("length") or 0); self.seek_updating = True; self.progress.set_range(0, max(1, length)); self.progress.set_value(min(elapsed, length) if length else 0); self.progress.set_sensitive(bool(zone.get("can_seek") and length)); self.seek_updating = False; self.elapsed.set_text(self.format_time(elapsed)); self.remaining.set_text("−" + self.format_time(max(0, length - elapsed)))
        output = zone.get("output") or {}; volume = output.get("volume") or {}; value = volume.get("value"); self.volume_updating = True; self.volume.set_sensitive(value is not None); self.volume.set_value(float(value or 0)); self.volume_value.set_text(str(value) if value is not None else "FIXED"); self.mute.set_sensitive(value is not None); self.mute.set_label("UNMUTE" if volume.get("is_muted") else "MUTE"); self.volume_updating = False

    def render_bluos_inputs(self, amplifier, have_roon):
        inputs = list(amplifier.get("inputs") or [])
        signature = [(str(item.get("id")), item.get("name") or "Input") for item in inputs]
        if signature != getattr(self, "bluos_input_signature", None):
            self.bluos_input_signature = signature
            while child := self.roon_subnav.get_first_child(): self.roon_subnav.remove(child)
            self.bluos_source_buttons = {}
            for input_id, name in signature:
                button = self.button(name.upper(), lambda _button, value=input_id: self.select_bluos_input(value), ""); self.bluos_source_buttons[input_id] = button; self.roon_subnav.append(button)
            self.roon_subnav.append(self.now_playing_tab); self.roon_subnav.append(self.queue_tab)
        active_id = str((amplifier.get("active_input") or {}).get("id") or "")
        for input_id, button in self.bluos_source_buttons.items():
            if self.requested_audio_view == "source" and input_id == active_id: button.add_css_class("active")
            else: button.remove_css_class("active")

    def select_bluos_input(self, input_id):
        self.requested_audio_view = "source"; self.set_roon_view("source")
        threading.Thread(target=post_json, args=(ROON + "/api/bluos/input", {"input_id": input_id}), daemon=True).start()

    def step_bluos_volume(self, amount):
        value = ((((self.state or {}).get("amplifier") or {}).get("volume")) or {}).get("value")
        if value is not None: threading.Thread(target=post_json, args=(ROON + "/api/bluos/volume", {"value": round(float(value) + amount)}), daemon=True).start()

    def set_roon_view(self, name):
        if name in {"now", "queue", "source"}: self.requested_audio_view = name
        self.detail_takeover.set_visible(name == "details")
        if name != "details": self.roon_views.set_visible_child_name(name)
        self.now_playing_tab.remove_css_class("active"); self.queue_tab.remove_css_class("active")
        if name == "queue": self.queue_tab.add_css_class("active")
        elif name == "now": self.now_playing_tab.add_css_class("active")
        if name == "queue": GLib.idle_add(self.scroll_queue_to_current)

    def show_roon_now(self, *_):
        self.set_roon_view("now")

    def render_details(self, details):
        signature = json.dumps(details, sort_keys=True, separators=(",", ":"), default=str)
        if signature == self.detail_signature: return
        self.detail_signature = signature
        self.detail_title.set_text(details.get("album") or details.get("track") or "Nothing playing")
        self.detail_artist.set_text(details.get("artist") or "")
        self.detail_subtitle.set_text("Loading available Roon information…" if details.get("status") == "loading" else (details.get("subtitle") or ""))
        metadata = details.get("metadata") or {}
        writeup = metadata.get("writeup") or ""; self.detail_writeup.set_text(writeup); self.detail_writeup.set_visible(bool(writeup))
        source = metadata.get("writeup_source") or ""; self.detail_source.set_text(f"SOURCE  {source.upper()}" if source else ""); self.detail_source.set_visible(bool(source))
        while child := self.detail_facts.get_first_child(): self.detail_facts.remove(child)
        facts = []
        if metadata.get("release_date") or metadata.get("year"): facts.append(f"RELEASED  {metadata.get('release_date') or metadata.get('year')}")
        if metadata.get("genres"): facts.append(f"GENRE  {' · '.join(metadata['genres'])}")
        if metadata.get("type"): facts.append(f"TYPE  {metadata['type']}")
        if metadata.get("label"): facts.append(f"LABEL  {metadata['label']}")
        if metadata.get("format"): facts.append(f"FORMAT  {metadata['format']}")
        summary = []
        if metadata.get("track_count"): summary.append(f"{metadata['track_count']} TRACKS")
        if metadata.get("country"): summary.append(str(metadata["country"]))
        if metadata.get("edition_count", 0) > 1: summary.append(f"{metadata['edition_count']} EDITIONS")
        if summary: facts.append("  ·  ".join(summary))
        for fact in facts:
            label = self.label(fact, "detail-fact"); label.set_wrap(True); self.detail_facts.append(label)
        while child := self.detail_tracks.get_first_child(): self.detail_tracks.remove(child)
        for index, track in enumerate((details.get("tracks") or [])[:30], 1):
            row = Gtk.Box(spacing=8); row.add_css_class("detail-track"); row.append(self.label(str(index), "detail-track-no")); title = self.label(track.get("title") or "Untitled track", "detail-track-title"); title.set_ellipsize(Pango.EllipsizeMode.END); title.set_hexpand(True); row.append(title); self.detail_tracks.append(row)

    def render_queue(self, queue):
        items = queue.get("items") or []
        signature = json.dumps(items, sort_keys=True, separators=(",", ":"), default=str)
        if signature == self.queue_signature: return
        self.queue_signature = signature; self.queue_pictures = {}; self.queue_artwork_keys = []
        while child := self.queue_list.get_first_child(): self.queue_list.remove(child)
        if not items:
            message = "Queue is loading…" if queue.get("status") == "loading" else "Nothing is queued"
            self.queue_list.append(self.label(message, "queue-empty", .5)); return
        self.queue_current_index = 0
        for index, item in enumerate(items):
            row = Gtk.Box(spacing=12); row.set_hexpand(True)
            picture = Gtk.Picture(); picture.add_css_class("queue-art"); picture.set_size_request(56, 56); picture.set_content_fit(Gtk.ContentFit.COVER); row.append(picture)
            key = item.get("image_key")
            self.queue_artwork_keys.append(key)
            if key:
                self.queue_pictures.setdefault(key, []).append(picture)
                texture = self.queue_thumbnail_cache.get(key)
                if texture: picture.set_paintable(texture)
            detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2); detail.set_valign(Gtk.Align.CENTER); detail.set_hexpand(True)
            title = self.label(item.get("title") or "Untitled track", "queue-title"); title.set_ellipsize(Pango.EllipsizeMode.END); detail.append(title)
            meta = " · ".join(filter(None, (item.get("artist"), item.get("album"))))
            metadata = self.label(meta or "Roon", "queue-meta"); metadata.set_ellipsize(Pango.EllipsizeMode.END); detail.append(metadata); row.append(detail)
            length = item.get("length"); row.append(self.label(self.format_time(int(length)) if length else "", "queue-duration", 1))
            button = Gtk.Button(); button.add_css_class("queue-row"); button.set_child(row)
            if item.get("is_current"): button.add_css_class("current"); self.queue_current_index = index
            elif item.get("is_previous"): button.add_css_class("previous"); button.connect("clicked", self.play_queue_item, item.get("queue_item_id"))
            else: button.connect("clicked", self.play_queue_item, item.get("queue_item_id"))
            self.queue_list.append(button)
        GLib.idle_add(self.load_visible_queue_artwork)

    def scroll_queue_to_current(self):
        row_height = 88 if self.window.has_css_class("high-resolution") else 68
        self.queue_scroll.get_vadjustment().set_value(max(0, getattr(self, "queue_current_index", 0) * row_height))
        return False

    def load_visible_queue_artwork(self, *_):
        adjustment = self.queue_scroll.get_vadjustment()
        row_height = 88 if self.window.has_css_class("high-resolution") else 68
        start = max(0, int(adjustment.get_value() / row_height) - 2)
        count = max(8, int(adjustment.get_page_size() / row_height) + 5)
        for key in self.queue_artwork_keys[start:start + count]:
            if key and key not in self.queue_thumbnail_cache and key not in self.queue_thumbnail_pending:
                self.queue_thumbnail_pending.add(key); self.queue_thumbnail_jobs.put(key)
        return False

    def thumbnail_worker(self):
        while True:
            key = self.queue_thumbnail_jobs.get()
            image = get_bytes(f"{ROON}/api/image?key={quote(key, safe='')}&size=96", timeout=2.0)
            GLib.idle_add(self.apply_queue_thumbnail, key, image)

    def apply_queue_thumbnail(self, key, image):
        self.queue_thumbnail_pending.discard(key)
        if not image: return False
        try: texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(image))
        except GLib.Error: return False
        self.queue_thumbnail_cache[key] = texture
        if key in self.queue_thumbnail_order: self.queue_thumbnail_order.remove(key)
        self.queue_thumbnail_order.append(key)
        while len(self.queue_thumbnail_order) > 64:
            old = self.queue_thumbnail_order.pop(0); self.queue_thumbnail_cache.pop(old, None)
        for picture in self.queue_pictures.get(key, []): picture.set_paintable(texture)
        return False

    def play_queue_item(self, _button, queue_item_id):
        if queue_item_id is not None:
            threading.Thread(target=post_json, args=(ROON + "/api/queue/play", {"queue_item_id": queue_item_id}), daemon=True).start()

    def set_mode(self, mode):
        started = time.monotonic(); self.settings_open = False; self.last_mode = mode; self.stack.set_visible_child_name(mode); print(f"Pi Home switched to {mode} in {(time.monotonic() - started) * 1000:.1f}ms", flush=True); threading.Thread(target=post_json, args=(BUS + "/api/admin/display-mode", {"mode": mode}), daemon=True).start()

    def note_missing_artwork(self):
        self.image_misses += 1
        if self.image_misses >= 5:
            self.artwork.set_paintable(None)
            self.image_key = None

    def open_settings(self, *_): self.settings_open = True; self.last_system_fetch = 0; self.stack.set_visible_child_name("settings"); self.start_poll()
    def close_settings(self, *_): self.settings_open = False; self.stack.set_visible_child_name(self.last_mode)
    def note_activity(self, _controller, event):
        # Legacy controllers also receive pointer motion, enter/leave and window
        # events. A powered-down panel can consume the beginning of the first
        # contact, so accept its release as a wake gesture as well.
        event_type = event.get_event_type()
        contact_started = event_type in {Gdk.EventType.BUTTON_PRESS, Gdk.EventType.TOUCH_BEGIN, Gdk.EventType.KEY_PRESS}
        contact_finished = event_type in {Gdk.EventType.BUTTON_RELEASE, Gdk.EventType.TOUCH_END}
        if not contact_started and not contact_finished:
            return False
        self.last_interaction = time.monotonic()
        if self.inactivity_sleeping:
            source = getattr(event_type, "value_nick", str(event_type))
            self.inactivity_sleeping = False; print(f"Pi Home waking after touchscreen {source}", flush=True); self.set_screen_power(True, force=True); self.stack.set_visible_child_name(self.last_mode or "bus")
        elif self.stack.get_visible_child_name() == "sleep" and time.monotonic() - self.sleep_entered_at >= .45:
            self.wake(getattr(event_type, "value_nick", str(event_type)))
        return False

    def prepare_sleep_wake(self):
        # Ignore only the short tail of the gesture that pressed Sleep. Using a
        # timestamp avoids depending on a delayed GLib arming callback, which
        # could leave manual sleep permanently unable to accept a wake touch.
        self.sleep_entered_at = time.monotonic()

    def sleep(self, *_): self.inactivity_sleeping = False; self.settings_open = False; self.prepare_sleep_wake(); self.stack.set_visible_child_name("sleep"); self.set_screen_power(bool(self.settings_data.get("sleep_show_clock", False))); threading.Thread(target=post_json, args=(BUS + "/api/admin/display-mode", {"mode": "sleep"}), daemon=True).start()
    def wake(self, *_):
        now = time.monotonic()
        source = _[0] if _ else "input"
        self.sleep_entered_at = 0.0; self.last_interaction = now; self.inactivity_sleeping = False; print(f"Pi Home waking after fresh touchscreen {source}", flush=True); self.set_screen_power(True, force=True); self.stack.set_visible_child_name(self.last_mode or "bus")
        threading.Thread(target=post_json, args=(BUS + "/api/device/wake", {"view": self.last_mode or "bus"}), daemon=True).start()
    def control(self, action):
        if action == "playpause" and (((self.state or {}).get("amplifier") or {}).get("active_input")): action = "resume"
        threading.Thread(target=post_json, args=(ROON + "/api/control", {"action": action}), daemon=True).start()
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
        amplifier = self.state.get("amplifier") or {}
        if amplifier.get("connected"):
            threading.Thread(target=post_json, args=(ROON + "/api/bluos/volume", {"value": round(scale.get_value())}), daemon=True).start(); return
        output = (self.state.get("zone") or {}).get("output") or {}; output_id = output.get("id")
        if output_id: threading.Thread(target=post_json, args=(ROON + "/api/volume", {"output_id": output_id, "value": round(scale.get_value())}), daemon=True).start()

    def toggle_audio_mute(self, *_):
        if not self.state: return
        amplifier = self.state.get("amplifier") or {}
        if amplifier.get("connected"): threading.Thread(target=post_json, args=(ROON + "/api/bluos/mute", {}), daemon=True).start(); return
        output = (self.state.get("zone") or {}).get("output") or {}; output_id = output.get("id")
        if output_id: threading.Thread(target=post_json, args=(ROON + "/api/mute", {"output_id": output_id}), daemon=True).start()

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
        self.update_in_progress = True; self.update_status_seen = False; self.update_button.set_sensitive(False); self.device_status.set_text("Update · Requesting installation…")
        threading.Thread(target=self._request_update, daemon=True).start()

    def _request_update(self):
        result = post_json(BUS + "/api/device/update", {})
        GLib.idle_add(self.device_status.set_text, "Update · Queued…" if result else "Could not start update")
        if result:
            self.last_system_fetch = 0
            GLib.idle_add(self.start_poll)
        else:
            self.update_in_progress = False
            GLib.idle_add(self.update_button.set_sensitive, True)

    def request_display_settings(self, *_):
        profiles = ("original", "touch2-5", "touch2-7", "touch2-10"); orientations = ("normal", "90", "180", "270")
        profile = profiles[min(self.touch_profile.get_selected(), len(profiles) - 1)]; transform = orientations[min(self.touch_orientation.get_selected(), len(orientations) - 1)]
        self.apply_display_button.set_sensitive(False); self.device_status.set_text("Applying display settings…")
        threading.Thread(target=self._request_display_settings, args=(profile, transform), daemon=True).start()

    def _request_display_settings(self, profile, transform):
        result = post_json(BUS + "/api/admin/system-action", {"action": "set_display", "profile": profile, "transform": transform})
        GLib.idle_add(self.device_status.set_text, "Applying display settings…" if result else "Could not apply display settings")
        if not result: GLib.idle_add(self.apply_display_button.set_sensitive, True)


if __name__ == "__main__":
    Display().run(None)
