import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pi_bus_time_display.config import Config
from pi_bus_time_display.server import display_target, read_display_mode, within_sleep_window


class DisplayModeTests(unittest.TestCase):
    def test_missing_mode_defaults_to_auto(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_display_mode(Path(directory) / "display-mode"), "auto")

    def test_valid_mode_is_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "display-mode"
            path.write_text("bus\n", encoding="utf-8")
            self.assertEqual(read_display_mode(path), "bus")

    def test_sleep_mode_is_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "display-mode"
            path.write_text("sleep\n", encoding="utf-8")
            self.assertEqual(read_display_mode(path), "sleep")

    def test_unknown_mode_defaults_to_auto(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "display-mode"
            path.write_text("surprise\n", encoding="utf-8")
            self.assertEqual(read_display_mode(path), "auto")

    def test_roon_mode_targets_custom_controller(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "display-mode"
            path.write_text("roon\n", encoding="utf-8")
            self.assertEqual(display_target(Config(), path), "http://127.0.0.1:8766/")

    def test_sleep_mode_targets_black_screen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "display-mode"
            path.write_text("sleep\n", encoding="utf-8")
            self.assertEqual(display_target(Config(), path), "/sleep.html")

    def test_overnight_sleep_window_crosses_midnight(self):
        config = Config(sleep_start="23:00", sleep_end="06:00")
        timezone = ZoneInfo("Asia/Singapore")
        self.assertTrue(within_sleep_window(config, datetime(2026, 9, 28, 23, 30, tzinfo=timezone)))
        self.assertTrue(within_sleep_window(config, datetime(2026, 9, 29, 5, 59, tzinfo=timezone)))
        self.assertFalse(within_sleep_window(config, datetime(2026, 9, 29, 6, 0, tzinfo=timezone)))


if __name__ == "__main__":
    unittest.main()
