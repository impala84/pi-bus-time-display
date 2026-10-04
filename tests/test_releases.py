import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pi_bus_time_display.config import Config, load_config
from pi_bus_time_display.releases import ReleaseChecker, SemVer, select_release
from pi_bus_time_display.server import write_config


def release(tag, **fields):
    return {"tag_name": tag, **fields}


class ReleaseTests(unittest.TestCase):
    def test_semver_numeric_prerelease_order_and_final(self):
        values = ['1.1.0-beta.2', '1.1.0-beta.10', '1.1.0', '1.10.0', '2.0.0']
        self.assertEqual(sorted(values, key=SemVer), values)
        self.assertEqual(SemVer('1.0.0+build.5'), SemVer('v1.0.0'))
        for invalid in ('main', '1.0', '01.0.0', '1.0.0-beta.01', 'v1.0.0;reboot'):
            with self.assertRaises(ValueError): SemVer(invalid)

    def test_stable_excludes_beta_draft_and_invalid_tags(self):
        items = [release('v1.0.1'), release('v1.1.0-beta.1', prerelease=True), release('v9.0.0', draft=True), release('main'), release('v3.0.0', prerelease=True)]
        result = select_release(items, 'stable', '1.0.0')
        self.assertEqual(result['tag'], 'v1.0.1')
        self.assertTrue(result['update_available'])

    def test_beta_selects_highest_semver_not_publication_order(self):
        items = [release('v1.0.0'), release('v1.1.0-beta.10', prerelease=True), release('v1.1.0-beta.2', prerelease=True)]
        self.assertEqual(select_release(items, 'beta', '1.0.0')['tag'], 'v1.1.0-beta.10')
        items.append(release('v1.1.0'))
        self.assertEqual(select_release(items, 'beta', '1.1.0-beta.10')['tag'], 'v1.1.0')

    def test_return_to_stable_never_downgrades(self):
        result = select_release([release('v1.0.0')], 'stable', '1.1.0-beta.1')
        self.assertEqual(result['status'], 'ahead')
        self.assertFalse(result['update_available'])
        self.assertFalse(select_release([release('v1.0.0')], 'stable', '1.0.0')['update_available'])

    def test_empty_or_failed_catalogue_is_not_up_to_date(self):
        self.assertEqual(select_release([], 'stable', '1.0.0')['status'], 'unavailable')
        with patch('pi_bus_time_display.releases.published_releases', side_effect=OSError('offline')):
            self.assertEqual(ReleaseChecker().check('stable', '1.0.0')['status'], 'unavailable')

    def test_cache_refreshes_after_channel_change(self):
        with patch('pi_bus_time_display.releases.published_releases', return_value=[release('v1.0.0')]) as fetch:
            checker = ReleaseChecker()
            checker.check('stable', '1.0.0'); checker.check('stable', '1.0.0')
            self.assertEqual(fetch.call_count, 1)
            checker.check('beta', '1.0.0'); checker.check('beta', '1.0.0', refresh=True)
            self.assertEqual(fetch.call_count, 3)

    def test_channel_persists_and_rejects_invalid_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.toml'
            self.assertEqual(Config().release_channel, 'stable')
            write_config(path, Config(release_channel='beta'))
            self.assertEqual(load_config(path).release_channel, 'beta')
            write_config(path, Config(release_channel='main'))
            with self.assertRaises(ValueError): load_config(path)

    def test_updater_uses_exact_release_tag_not_main(self):
        script = (Path(__file__).parents[1] / 'scripts/pi-bus-update').read_text()
        self.assertIn('releases.py', script)
        self.assertIn('checkout --detach "refs/tags/${PI_HOME_UPDATE_TARGET}"', script)
        self.assertNotIn('checkout -B main origin/main', script)
        self.assertLess(script.index('if [[ -z ${release_tag} ]]'), script.index('stash push'))
        self.assertIn('|| -z ${PI_HOME_UPDATE_TARGET:-}', script)


if __name__ == '__main__': unittest.main()
