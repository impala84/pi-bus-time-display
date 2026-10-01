import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class UpdateScriptTests(unittest.TestCase):
    def test_system_package_refresh_only_runs_for_missing_packages(self):
        script = (ROOT / "scripts" / "pi-bus-update").read_text(encoding="utf-8")
        self.assertIn("dpkg-query -W", script)
        self.assertIn('if ((${#missing_packages[@]})); then', script)
        self.assertIn('apt-get install -y "${missing_packages[@]}"', script)
        self.assertIn("--prefer-offline --no-audit --no-fund", script)


if __name__ == "__main__":
    unittest.main()
