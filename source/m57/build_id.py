"""Stable EEPROM compatibility ID for BORNE m57 Vial builds.

Increment the version when the EEPROM layout or stored-value semantics change
(e.g. layer/encoder counts, Vial entry counts, storage allocation, or an
incompatible upstream update). RGB effects and default keymaps do not require
an increment. Version changes intentionally reset saved Vial settings.

Copy this file to vial-qmk/util/build_id.py before building, also for manual
builds. Vial stores only the low 24 bits; 0xFFFFFF is its invalid marker.
"""

EEPROM_SCHEMA_VERSION = 1

if __name__ == "__main__":
    if not 1 <= EEPROM_SCHEMA_VERSION <= 255:
        raise ValueError("EEPROM schema version must fit in one nonzero byte")
    print(f"#define BUILD_ID ((uint32_t)0x{0x4D5700 | EEPROM_SCHEMA_VERSION:08X})")
