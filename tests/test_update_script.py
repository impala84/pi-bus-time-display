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

    def test_update_has_lock_timeouts_and_dependency_stamp(self):
        script = (ROOT / "scripts" / "pi-bus-update").read_text(encoding="utf-8")
        service = (ROOT / "systemd" / "pi-bus-system-action.service").read_text(encoding="utf-8")
        self.assertIn("flock -n 9", script)
        self.assertIn("timeout --signal=TERM --kill-after=10s 2m git", script)
        self.assertIn("roon-package-lock.sha256", script)
        self.assertIn('npm --prefix "${app_dir}/roon-controller" ci', script)
        self.assertIn("CPUQuota=100%", service)
        self.assertIn("TimeoutStartSec=15min", service)


if __name__ == "__main__":
    unittest.main()
