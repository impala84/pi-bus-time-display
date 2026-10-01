import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class DisplayRotationTests(unittest.TestCase):
    def test_touch_uses_documented_clockwise_calibration(self):
        script = (ROOT / "scripts" / "pi-bus-appliance-mode").read_text(encoding="utf-8")
        self.assertIn("90) matrix='0 -1 1 1 0 0'", script)
        self.assertIn("270) matrix='0 1 0 -1 0 1'", script)

    def test_touch_rotation_is_not_applied_twice(self):
        script = (ROOT / "scripts" / "pi-bus-appliance-mode").read_text(encoding="utf-8")
        self.assertNotIn('ENV{WL_OUTPUT}', script)

    def test_wayland_uses_inverse_quarter_turn(self):
        script = (ROOT / "scripts" / "pi-bus-cage-launch").read_text(encoding="utf-8")
        self.assertIn("90) transform=270", script)
        self.assertIn("270) transform=90", script)


if __name__ == "__main__":
    unittest.main()
