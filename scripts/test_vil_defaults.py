#!/usr/bin/env python3
"""Run from the repository root: python3 scripts/test_vil_defaults.py."""
import copy
import json
from pathlib import Path
import re
import unittest

from vil_defaults_gen import generate, keycode

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / 'vil_backups/default.vil').read_bytes()
DATA = json.loads(RAW)


class DefaultsTest(unittest.TestCase):
    def test_checked_in_defaults_match_backup(self):
        self.assertEqual(generate(RAW), (ROOT / 'source/m57/keymaps/via/vil_defaults.h').read_text())

    def test_vial_keycode_translation(self):
        self.assertEqual(keycode('LT3(KC_TAB)'), 'LT(3, KC_TAB)')
        self.assertEqual(keycode('RCAG_T(KC_SCOLON)'), 'RCAG_T(KC_SCLN)')
        self.assertEqual(keycode('0x154c'), '0x154c')
        self.assertEqual(keycode(-1), 'KC_NO')
        with self.assertRaises(ValueError):
            keycode('KC_A; invalid')

    def test_every_backup_entry_is_emitted_in_order(self):
        rendered = generate(RAW)
        # Read C initializer rows independently of the generator's structure.
        def rows(name):
            body = rendered.split(name, 1)[1].split('= {', 1)[1].split('\n};', 1)[0]
            return [line.strip().removesuffix(',') for line in body.splitlines() if line.strip().startswith('{')]
        self.assertEqual(rows('keymaps[]'), [
            '{' + ', '.join(keycode(k) for k in row) + '}'
            for layer in DATA['layout'] for row in layer
        ])
        encoder_body = rendered.split('encoder_map[]', 1)[1].split('\n};', 1)[0]
        encoders = re.findall(r'ENCODER_CCW_CW\(([^)]+)\)', encoder_body)
        self.assertEqual(encoders, [', '.join(keycode(k) for k in pair)
                                   for layer in DATA['encoder_layout'] for pair in layer])
        self.assertEqual(rows('borne_default_tap_dance[]'), [
            '{' + ', '.join([*(keycode(k) for k in row[:4]), str(row[4])]) + '}'
            for row in DATA['tap_dance']
        ])
        self.assertEqual(rows('borne_default_combo[]'), [
            '{{' + ', '.join(keycode(k) for k in row[:4]) + '}, ' + keycode(row[4]) + '}'
            for row in DATA['combo']
        ])
        for name in ('key_override', 'alt_repeat_key'):
            parsed = [dict(re.findall(r'\.(\w+) = ([^,}]+)', row)) for row in rows('borne_default_' + name + '[]')]
            expected = [{k: keycode(v) if isinstance(v, str) else str(v) for k, v in row.items()} for row in DATA[name]]
            self.assertEqual(parsed, expected)
        settings = [tuple(map(int, re.findall(r'\d+', row))) for row in rows('borne_default_settings[]')]
        self.assertEqual(dict(settings), {int(k): v for k, v in DATA['settings'].items()})

    def test_unsupported_data_is_not_silently_lost(self):
        changes = [('macro', [['text', 'hello']] + [[] for _ in range(14)]),
                   ('uid', 0), ('layout_options', 1), ('layout', DATA['layout'][:9]),
                   ('settings', {'999': 0}), ('unexpected_field', True)]
        for name, value in changes:
            with self.subTest(name=name):
                changed = copy.deepcopy(DATA)
                changed[name] = value
                with self.assertRaises(ValueError):
                    generate(json.dumps(changed).encode())


if __name__ == '__main__':
    unittest.main()
