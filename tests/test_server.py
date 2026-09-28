import tempfile
import unittest
from pathlib import Path

from pi_bus_time_display.server import read_display_mode


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


if __name__ == "__main__":
    unittest.main()
