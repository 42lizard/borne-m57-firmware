#!/usr/bin/env python3
"""Compile hook checks, optionally with pinned VIA's real dispatcher.

Usage: python3 scripts/test_raw_hid_layer.py [path/to/quantum/via.c]
The optional integration check also reads via.h alongside via.c.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def check(via_path=None):
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        config = (ROOT / 'source/m57/config.h').read_text()
        count = re.search(r'^#define DYNAMIC_KEYMAP_LAYER_COUNT (\d+)$', config, re.M)[1]
        (folder / 'quantum.h').write_text(
            '#include <stdint.h>\n'
            f'#define DYNAMIC_KEYMAP_LAYER_COUNT {count}\n'
            'void layer_move(uint8_t layer);\n')
        (folder / 'via.h').write_text('#define id_unhandled 0xFF\n')
        command = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', f'-I{folder}',
                   str(ROOT / 'scripts/test_raw_hid_layer.c'),
                   str(ROOT / 'source/m57/keymaps/via/raw_hid_layer.c')]
        if via_path:
            source = via_path.read_text()
            header = via_path.with_suffix('.h').read_text()
            enums = '\n'.join(re.findall(r'enum via_\w+\s*\{.*?\};', header, re.S))
            receiver = source[source.index('void raw_hid_receive(uint8_t *data, uint8_t length) {'):]
            receiver = receiver[:receiver.index('\n}\n') + 3]
            # Other QMK subsystems are outside this host-side dispatch check.
            names = ['timer_read32', 'via_get_layout_options', 'via_set_layout_options',
                     'dynamic_keymap_get_keycode', 'dynamic_keymap_set_keycode',
                     'dynamic_keymap_reset', 'dynamic_keymap_macro_get_count',
                     'dynamic_keymap_macro_get_buffer_size', 'dynamic_keymap_macro_get_buffer',
                     'dynamic_keymap_macro_set_buffer', 'dynamic_keymap_macro_reset',
                     'dynamic_keymap_get_layer_count', 'dynamic_keymap_get_buffer',
                     'dynamic_keymap_set_buffer']
            stubs = '\n'.join(f'#define {name}(...) stub(__VA_ARGS__)' for name in names)
            harness = r'''
#include <stdbool.h>
#include <stdint.h>
#define VIAL_ENABLE
#define VIAL_INSECURE
#define MATRIX_ROWS 32
#define MATRIX_COLS 8
bool vial_unlock_in_progress = false, vial_unlocked = true;
enum { vial_get_keyboard_id, vial_get_size, vial_get_def, vial_get_unlock_status,
       vial_unlock_start, vial_unlock_poll };
unsigned sends, vial_calls;
uint32_t stub() { return 0; }
void raw_hid_receive_kb(uint8_t *data, uint8_t length);
void raw_hid_send(uint8_t *data, uint8_t length) { (void)data; (void)length; sends++; }
void vial_handle_cmd(uint8_t *data, uint8_t length) {
    (void)length; vial_calls++; data[1] = 0xA5;
}
'''
            version = re.search(r'^#define VIA_PROTOCOL_VERSION .*$', header, re.M)[0]
            dispatcher = folder / 'dispatcher.c'
            dispatcher.write_text(harness + enums + '\n' + version + '\n' + stubs + '\n' + receiver)
            command += ['-DTEST_VIA_DISPATCH', str(dispatcher)]
        binary = folder / 'check'
        subprocess.run(command + ['-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    print('PASS: Raw HID validation and layer selection' + (' with pinned VIA dispatch' if via_path else ''))


if __name__ == '__main__':
    check(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
