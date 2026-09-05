"""Focused syntax/configuration contracts, not a whole-kernel build."""
import os
from pathlib import Path
import re
import unittest

ROOT = Path(os.environ.get('MODULES_ROOT', Path(__file__).resolve().parents[1]))
BATTERY = 'drivers/power/supply/battery_secrete/Kconfig'
HAPTIC = 'drivers/misc/mediatek/si_haptic/Kconfig'


class KconfigContracts(unittest.TestCase):
    def test_one_prompt_per_battery_symbol(self):
        text = (ROOT / BATTERY).read_text()
        blocks = re.split(r'(?m)^config ', text)[1:]
        expected = {'ONEWIRE_GPIO': 'y', 'BATT_VERIFY': 'y',
                    'BATT_VERIFY_BY_SLG': 'y', 'BATT_VERIFY_BY_ST': 'm',
                    'BATT_VERIFY_BY_DS28E30': 'y'}
        self.assertEqual({b.splitlines()[0] for b in blocks}, set(expected))
        for block in blocks:
            name = block.splitlines()[0]
            with self.subTest(symbol=name):
                self.assertEqual(len(re.findall(r'(?m)^\s*(?:prompt|tristate)\s+"', block)), 1)
                self.assertRegex(block, r'(?m)^\ttristate$')
                self.assertRegex(block, r'(?m)^\tdefault ' + expected[name] + r'$')
                self.assertNotRegex(block, r'(?m)^\s*(?:depends|select|imply)\b')

    def test_haptic_help_is_indented_and_default_retained(self):
        text = (ROOT / HAPTIC).read_text()
        self.assertEqual(text, 'config SIH_VIBRATOR\n    tristate "SI Vibrator driver"\n'
                         '    default y\n    help\n      SI Vibrator driver\n')

    def test_touched_kconfigs_have_unix_lines(self):
        for name in (BATTERY, HAPTIC):
            with self.subTest(path=name):
                data = (ROOT / name).read_bytes()
                self.assertNotIn(b'\r', data)
                self.assertTrue(data.endswith(b'\n'))
                self.assertTrue(all(line == line.rstrip() for line in data.splitlines()))


if __name__ == '__main__':
    unittest.main()
