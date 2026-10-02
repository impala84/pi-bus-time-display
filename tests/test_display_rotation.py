import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class DisplayRotationTests(unittest.TestCase):
    def test_touch_uses_inverse_wayland_quarter_turn(self):
        script = (ROOT / "scripts" / "pi-bus-appliance-mode").read_text(encoding="utf-8")
        self.assertIn("90) matrix='0 1 0 -1 0 1'", script)
        self.assertIn("270) matrix='0 -1 1 1 0 0'", script)

    def test_touch_rotation_is_not_applied_twice(self):
        script = (ROOT / "scripts" / "pi-bus-appliance-mode").read_text(encoding="utf-8")
        self.assertNotIn('ENV{WL_OUTPUT}', script)
        self.assertIn("[[ ${profile} == touch2-* ]] && matrix='1 0 0 0 1 0'", script)

    def test_touch_display_2_uses_supported_device_tree_rotation(self):
        script = (ROOT / "scripts" / "pi-bus-appliance-mode").read_text(encoding="utf-8")
        self.assertIn("90) flags=',swapxy,invx'", script)
        self.assertIn("180) flags=',invx,invy'", script)
        self.assertIn("270) flags=',swapxy,invy'", script)
        self.assertIn("vc4-kms-dsi-ili9881-7inch", script)
        self.assertIn('cmp -s "${boot_config}.tmp" "${boot_config}"', script)

    def test_goodix_multitouch_contact_can_wake_the_display(self):
        display = (ROOT / "native-display" / "pi_bus_native.py").read_text(encoding="utf-8")
        service = (ROOT / "systemd" / "pi-bus-native.service.in").read_text(encoding="utf-8")
        self.assertIn("event_type == 3 and code == 57", display)
        self.assertIn("value != 0xFFFFFFFF", display)
        self.assertIn("Environment=PYTHONUNBUFFERED=1", service)

    def test_sleep_button_touch_cannot_replay_as_a_wake(self):
        display = (ROOT / "native-display" / "pi_bus_native.py").read_text(encoding="utf-8")
        self.assertIn("GLib.idle_add(self.low_level_touch_wake, contact_at)", display)
        self.assertIn("contact_at <= self.sleep_entered_at", display)
        self.assertIn("self.inactivity_sleeping = True\n            self.prepare_sleep_wake()", display)

    def test_wayland_uses_inverse_quarter_turn(self):
        script = (ROOT / "scripts" / "pi-bus-cage-launch").read_text(encoding="utf-8")
        self.assertIn("90) transform=270", script)
        self.assertIn("270) transform=90", script)

    def test_landscape_profile_has_dedicated_large_touch_layout(self):
        display = (ROOT / "native-display" / "pi_bus_native.py").read_text(encoding="utf-8")
        self.assertIn('self.window.add_css_class("touch-landscape")', display)
        self.assertIn(".touch-landscape .settings-title", display)
        self.assertIn(".touch-landscape .roon-subnav button", display)
        self.assertIn('self.stack.add_named(self.build_boot_splash(), "boot")', display)
        self.assertIn('.boot-logo { color: #6ef0be', display)

    def test_landscape_artwork_is_fixed_smaller_and_detail_art_can_close(self):
        display = (ROOT / "native-display" / "pi_bus_native.py").read_text(encoding="utf-8")
        web_html = (ROOT / "roon-controller" / "static" / "index.html").read_text(encoding="utf-8")
        web_js = (ROOT / "roon-controller" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("self.artwork.set_size_request(324, 324)", display)
        self.assertIn("self.artwork_button.set_size_request(324, 324)", display)
        self.assertIn('detail_artwork_button.connect("clicked", lambda *_: self.set_roon_view("now"))', display)
        self.assertIn('id="details-artwork-close"', web_html)
        self.assertIn("$('details-artwork-close').onclick = () => setMusicView('now')", web_js)
        self.assertNotIn('id="details-close"', web_html)
        self.assertNotIn('"detail-back"', display)

    def test_touchscreen_settings_title_and_checkbox_spacing(self):
        display = (ROOT / "native-display" / "pi_bus_native.py").read_text(encoding="utf-8")
        self.assertIn('title = self.label("Settings", "settings-title", .5)', display)
        self.assertIn(".setting-line checkbutton label { margin-left: 12px;", display)

    def test_mobile_roon_navigation_uses_compact_uppercase_labels(self):
        app = (ROOT / "roon-controller" / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "roon-controller" / "static" / "refinements.css").read_text(encoding="utf-8")
        self.assertIn("function compactLabel(label)", app)
        self.assertIn("words[words.length - 1]", app)
        self.assertIn(".nav-label-compact { display: inline; }", css)
        self.assertIn("text-transform: uppercase", css)

    def test_long_now_playing_copy_pauses_and_scrolls_without_polling(self):
        app = (ROOT / "roon-controller" / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "roon-controller" / "static" / "refinements.css").read_text(encoding="utf-8")
        self.assertIn("function setScrollingText(element, text)", app)
        self.assertIn("const startPause = 10000", app)
        self.assertIn("entry.content.animate", app)
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertNotIn("setInterval(() => refreshScrollingText", app)

    def test_web_update_control_is_fixed_and_reloads_after_install(self):
        html = (ROOT / "src" / "pi_bus_time_display" / "static" / "admin.html").read_text(encoding="utf-8")
        css = (ROOT / "src" / "pi_bus_time_display" / "static" / "admin.css").read_text(encoding="utf-8")
        script = (ROOT / "src" / "pi_bus_time_display" / "static" / "admin.js").read_text(encoding="utf-8")
        self.assertIn('class="global-update"', html)
        self.assertIn(".global-update{position:fixed", css)
        self.assertIn("setTimeout(()=>location.reload(),1200)", script)
        self.assertIn("const updateButtons=[...document.querySelectorAll", script)

    def test_appliance_boot_is_quiet_and_splash_free(self):
        script = (ROOT / "scripts" / "pi-bus-appliance-mode").read_text(encoding="utf-8")
        self.assertIn("disable_splash=1", script)
        self.assertIn("quiet loglevel=3 logo.nologo vt.global_cursor_default=0 systemd.show_status=false", script)
        self.assertIn("^touch2-(5|7|5-7)$", script)


if __name__ == "__main__":
    unittest.main()
