#!/usr/bin/env python3
"""Check our ID generator against pinned Vial's real EEPROM validity functions.

Run: python3 scripts/test_eeprom_schema.py /path/to/vial-qmk/quantum/via.c
Requires a host C compiler; does not touch the keyboard.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def check(via_source):
    generator = ROOT / 'source/m57/build_id.py'
    def run_generator(path):
        return subprocess.check_output([sys.executable, str(path)], text=True)
    first = run_generator(generator)
    assert first == run_generator(generator), 'Same schema must produce the same ID'
    assert first.strip() == '#define BUILD_ID ((uint32_t)0x004D5701)'
    # Compile upstream's actual reader/writer, rather than a reimplementation.
    start = via_source.index('bool via_eeprom_is_valid(void) {')
    end = via_source.index('// Override this at the keyboard code level', start)
    functions = via_source[start:end]
    harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#define VIAL_ENABLE
static uint8_t eeprom[16];
#define VIA_EEPROM_MAGIC_ADDR ((uintptr_t)eeprom)
static uint8_t eeprom_read_byte(const void *p) { return *(const uint8_t *)p; }
static void eeprom_update_byte(void *p, uint8_t v) { *(uint8_t *)p = v; }
'''
    main = r'''
int main(void) {
    // Existing schema-v1 saved data (including an unrelated user's setting).
    memset(eeprom, 0, sizeof eeprom);
    eeprom[0] = 0x01; eeprom[1] = 0x57; eeprom[2] = 0x4D;
    eeprom[8] = 123;
    assert(via_eeprom_is_valid() == (BUILD_ID == 0x4D5701));
    assert(eeprom[8] == 123);
    // Explicit factory reset still invalidates; initialization validates again.
    via_eeprom_set_valid(false);
    assert(!via_eeprom_is_valid());
    via_eeprom_set_valid(true);
    assert(via_eeprom_is_valid());
    assert(eeprom[8] == 123);
    // Erased storage, including first boot, is never accepted as valid.
    memset(eeprom, 0xFF, sizeof eeprom);
    assert(!via_eeprom_is_valid());
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        bumped = folder / 'build_id_v2.py'
        bumped.write_text(generator.read_text().replace('EEPROM_SCHEMA_VERSION = 1', 'EEPROM_SCHEMA_VERSION = 2'))
        second = run_generator(bumped)
        assert second != first
        for number, definition in enumerate((first, second)):
            value = int(re.search(r'0x([0-9A-F]+)', definition)[1], 16)
            assert 0 <= value < 0xFFFFFF
            source = folder / f'check{number}.c'
            binary = folder / f'check{number}'
            source.write_text(harness + definition + functions + main)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
    print('PASS: stable ID, preserved settings, schema bump, manual reset, erased storage')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('via_c', type=Path)
    check(parser.parse_args().via_c.read_text())
