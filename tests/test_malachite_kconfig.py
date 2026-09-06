"""Guard the device-specific Kconfig cleanup, not complete kernel configuration."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(os.environ.get('MALACHITE_MODULES_ROOT', Path(__file__).resolve().parents[1]))
BATTERY = 'drivers/power/supply/battery_secrete/Kconfig'
HAPTIC = 'drivers/misc/mediatek/si_haptic/Kconfig'
EXPECTED = {'ONEWIRE_GPIO': 'y', 'BATT_VERIFY': 'y', 'BATT_VERIFY_BY_SLG': 'y',
            'BATT_VERIFY_BY_ST': 'm', 'BATT_VERIFY_BY_DS28E30': 'y', 'SIH_VIBRATOR': 'y'}


class KconfigContracts(unittest.TestCase):
    def test_one_prompt_per_symbol(self):
        for relative in (BATTERY, HAPTIC):
            entries = re.split(r'(?m)^config ', (ROOT / relative).read_text())[1:]
            self.assertTrue(entries)
            for entry in entries:
                with self.subTest(symbol=entry.splitlines()[0]):
                    prompts = re.findall(r'^\s*(?:tristate|prompt)\s+"', entry, re.M)
                    self.assertEqual(len(prompts), 1)

    def test_symbol_types_and_defaults_unchanged(self):
        actual = {}
        for relative in (BATTERY, HAPTIC):
            for entry in re.split(r'(?m)^config ', (ROOT / relative).read_text())[1:]:
                self.assertRegex(entry, r'(?m)^\s+tristate(?:\s|$)')
                actual[entry.splitlines()[0]] = re.search(r'(?m)^\s+default ([ymn])$', entry)[1]
        self.assertEqual(actual, EXPECTED)

    def test_lf_and_final_newline(self):
        for relative in (BATTERY, HAPTIC):
            data = (ROOT / relative).read_bytes()
            self.assertNotIn(b'\r', data)
            self.assertTrue(data.endswith(b'\n'))

    def test_haptic_help_is_indented(self):
        self.assertIn('    help\n      SI Vibrator driver\n', (ROOT / HAPTIC).read_text())

    def test_available_linux_conf(self):
        override = os.environ.get('KCONFIG_CONF')
        candidates = [Path(override)] if override else sorted(Path('/usr/lib').glob('linux-kbuild-*/scripts/kconfig/conf'))
        conf = next((p for p in candidates if p.is_file()), None)
        if conf is None:
            self.skipTest('Linux conf unavailable; exact pinned 6.1 configuration remains an integration gate')
        for mode in ('--alldefconfig', '--allnoconfig', '--allmodconfig', '--allyesconfig'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                work = Path(directory)
                (work / 'Kconfig').write_text('mainmenu "Malachite contract"\nconfig MODULES\n\tbool "Modules"\n\tmodules\n\tdefault y\n' +
                    ''.join(f'source "{(ROOT / p).resolve()}"\n' for p in (BATTERY, HAPTIC)))
                proc = subprocess.run([str(conf), mode, 'Kconfig'], cwd=work,
                    env=dict(os.environ, KCONFIG_CONFIG=str(work / '.config')),
                    text=True, capture_output=True, timeout=20)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stderr, '')
                configured = (work / '.config').read_text()
                for symbol, default in EXPECTED.items():
                    value = {'--alldefconfig': default, '--allnoconfig': 'n',
                             '--allmodconfig': 'm', '--allyesconfig': 'y'}[mode]
                    expected = f'# CONFIG_{symbol} is not set' if value == 'n' else f'CONFIG_{symbol}={value}'
                    self.assertIn(expected, configured)


if __name__ == '__main__':
    unittest.main()
