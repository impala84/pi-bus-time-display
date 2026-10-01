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

    def test_wayland_uses_inverse_quarter_turn(self):
        script = (ROOT / "scripts" / "pi-bus-cage-launch").read_text(encoding="utf-8")
        self.assertIn("90) transform=270", script)
        self.assertIn("270) transform=90", script)

    def test_landscape_profile_has_dedicated_large_touch_layout(self):
        display = (ROOT / "native-display" / "pi_bus_native.py").read_text(encoding="utf-8")
        self.assertIn('self.window.add_css_class("touch-landscape")', display)
        self.assertIn(".touch-landscape .settings-title", display)
        self.assertIn(".touch-landscape .roon-subnav button", display)


if __name__ == "__main__":
    unittest.main()
