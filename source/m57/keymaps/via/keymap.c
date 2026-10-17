#include QMK_KEYBOARD_H

#include "quantum.h"

#include "hal_pal.h"

void keyboard_post_init_user(void) {
    // Select the layer effect even with an older effect saved in EEPROM.
    // Keep the user's brightness and keymap; do not write EEPROM at boot.
    rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_borne_layer_colors);
}

#include "dynamic_keymap.h"
#include "qmk_settings.h"
#include "vil_defaults.h"

// Wrap Vial's reset, not normal startup: existing user settings stay untouched.
// The real function restores keymaps/encoders from flash and clears Vial extras.
void __real_dynamic_keymap_reset(void);
void __wrap_dynamic_keymap_reset(void) {
    __real_dynamic_keymap_reset();
    for (uint8_t i = 0; i < 32; i++) {
        dynamic_keymap_set_tap_dance(i, &borne_default_tap_dance[i]);
        dynamic_keymap_set_combo(i, &borne_default_combo[i]);
        dynamic_keymap_set_key_override(i, &borne_default_key_override[i]);
        dynamic_keymap_set_alt_repeat_key(i, &borne_default_alt_repeat_key[i]);
    }
    for (uint8_t i = 0; i < sizeof(borne_default_settings) / sizeof(borne_default_settings[0]); i++) {
        qmk_settings_set(borne_default_settings[i].id, &borne_default_settings[i].value,
                         sizeof(borne_default_settings[i].value));
    }
    // Refresh cached tap-dance/combos also for a reset issued while running.
    vial_init();
}

#if defined(CHORDAL_HOLD)
// handedness map for CHORDAL_HOLD - same shape as LAYOUT macro in m57.h.
// 'L' = left half, 'R' = right half. used to instantly resolve mod-tap holds
// when the next key is on the opposite hand.
const char chordal_hold_layout[MATRIX_ROWS][MATRIX_COLS] PROGMEM = LAYOUT(
    'L','L','L','L','L','L',                  'R','R','R','R','R','R',
    'L','L','L','L','L','L','L',      'R','R','R','R','R','R','R',
    'L','L','L','L','L','L','L',      'R','R','R','R','R','R','R',
    'L','L','L','L','L','L','L',      'R','R','R','R','R','R','R',
                'L','L','L',                'R','R','R'
);
#endif

