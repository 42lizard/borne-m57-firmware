#pragma once
// AUTO-GENERATED from borne_status.toml.
// Do not edit by hand - run scripts/borne_status_gen.py to regenerate.
//
// included once from rgb_matrix_user.inc inside the
// RGB_MATRIX_CUSTOM_EFFECT_IMPLS guard so symbols stay file-scoped.

#include "quantum.h"

#define BORNE_RAINBOW_SHIFT 4
#define BORNE_SAW_SHIFT     3
#define BORNE_PULSE_FAST    4
#define BORNE_PULSE_SLOW    16

// LED index -> {row, col}; inverse of m57.c g_led_config.
// REGENERATE (rerun this script) if g_led_config ever changes.
static const uint8_t borne_led_pos[58][2] = {
    {0,0}, {0,1}, {0,2}, {0,3}, {0,4}, {0,5}, {1,0}, {1,1}, {1,2}, {1,3}, {1,4}, {1,5}, {1,6}, {2,0}, {2,1}, {2,2}, {2,3}, {2,4}, {2,5}, {2,6}, {3,0}, {3,1}, {3,2}, {3,3}, {3,4}, {3,5}, {4,3}, {4,4}, {4,5}, {5,1}, {5,2}, {5,3}, {5,4}, {5,5}, {5,6}, {6,0}, {6,1}, {6,2}, {6,3}, {6,4}, {6,5}, {6,6}, {7,0}, {7,1}, {7,2}, {7,3}, {7,4}, {7,5}, {7,6}, {8,1}, {8,2}, {8,3}, {8,4}, {8,5}, {8,6}, {9,1}, {9,2}, {9,3}
};

static uint8_t borne_breath_v(void) {
    return scale8(
        abs8(sin8(scale16by8(g_rgb_timer, rgb_matrix_config.speed / 8)) - 128) * 2,
        rgb_matrix_config.hsv.v);
}

// pulse like borne_breath_v but with a tunable speed divisor (smaller = faster).
static uint8_t borne_pulse(uint8_t spd_div) {
    if (spd_div == 0) spd_div = 1;
    uint8_t s = sin8(scale16by8(g_rgb_timer, rgb_matrix_config.speed / spd_div));
    return scale8(abs8(s - 128) * 2, rgb_matrix_config.hsv.v);
}

static uint8_t borne_saw_up(void)   { return (uint8_t)(g_rgb_timer >> BORNE_SAW_SHIFT); }
static uint8_t borne_saw_down(void) { return (uint8_t)(255 - (uint8_t)(g_rgb_timer >> BORNE_SAW_SHIFT)); }

static void borne_rainbow(bool fwd, uint8_t *r, uint8_t *g, uint8_t *b) {
    uint8_t h = (uint8_t)(g_rgb_timer >> BORNE_RAINBOW_SHIFT);
    if (!fwd) h = (uint8_t)(-h);
    hsv_t hsv = { h, 255, 255 };
    rgb_t c = hsv_to_rgb(hsv);
    *r = c.r; *g = c.g; *b = c.b;
}

// chart-encoded modifier blend: shift->R, ctrl->G, alt->B,
// gui bumps base 0x00->0x55 and high 0xAA->0xFF. RGB(0,0,0) when no mods held.
static void borne_compute_mod_blend(uint8_t br, bool pulsate,
                                    uint8_t *out_r, uint8_t *out_g, uint8_t *out_b) {
    uint8_t mods = get_mods() | get_weak_mods() | get_oneshot_mods();
    bool sft = mods & MOD_MASK_SHIFT;
    bool alt = mods & MOD_MASK_ALT;
    bool ctl = mods & MOD_MASK_CTRL;
    bool gui = mods & MOD_MASK_GUI;
    uint8_t base = gui ? 0x55 : 0x00;
    uint8_t high = gui ? 0xFF : 0xAA;
    uint8_t r = sft ? high : base;
    uint8_t g = ctl ? high : base;
    uint8_t b = alt ? high : base;
    if (pulsate) { r = scale8(r, br); g = scale8(g, br); b = scale8(b, br); }
    *out_r = r; *out_g = g; *out_b = b;
}

static inline void borne_set(uint8_t led, uint8_t led_min, uint8_t led_max,
                              uint8_t r, uint8_t g, uint8_t b) {
    if (led >= led_min && led < led_max) rgb_matrix_set_color(led, r, g, b);
}

// resolve the effective keycode under an LED, walking the active layer stack
// the same way QMK's layer_switch_get_layer does (incl. default_layer_state,
// skip on KC_TRANSPARENT only, fall back to layer 0).
static uint16_t borne_effective_keycode(uint8_t led) {
    keypos_t pos = { .row = borne_led_pos[led][0], .col = borne_led_pos[led][1] };
    layer_state_t active = layer_state | default_layer_state;
    for (int8_t l = MAX_LAYER - 1; l >= 0; l--) {
        if (active & ((layer_state_t)1 << l)) {
            uint16_t kc = keymap_key_to_keycode(l, pos);
            if (kc != KC_TRANSPARENT) return kc;
        }
    }
    return keymap_key_to_keycode(0, pos);
}

// keycode-class -> color. returns true if handled (caller keeps background
// otherwise). generated from the ordered [[keyrule]] table in borne_status.toml.
static bool borne_classify(uint16_t kc, uint8_t br,
                           uint8_t *out_r, uint8_t *out_g, uint8_t *out_b) {
    uint8_t r = 0, g = 0, b = 0;
    if ((kc >= QK_BOOTLOADER && kc <= QK_CLEAR_EEPROM)) {   // system_danger -> red_static
        r = 255; g = 0; b = 0;
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((IS_QK_MOMENTARY(kc) || IS_QK_TO(kc) || IS_QK_LAYER_TAP(kc) || IS_QK_TOGGLE_LAYER(kc) || IS_QK_LAYER_TAP_TOGGLE(kc) || IS_QK_DEF_LAYER(kc) || IS_QK_ONE_SHOT_LAYER(kc) || IS_QK_LAYER_MOD(kc))) {   // layer_switch -> yellow
        r = br; g = br; b = 0;
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if (IS_QK_MOD_TAP(kc)) {   // mod_tap -> mod_blend
        borne_compute_mod_blend(br, true, &r, &g, &b);
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if (IS_MODIFIER_KEYCODE(kc)) {   // modifier -> mod_static
        switch ((kc - KC_LEFT_CTRL) & 0x03) {
            case 0: r = 0; g = 255; b = 0; break;
            case 1: r = 255; g = 0; b = 0; break;
            case 2: r = 0; g = 0; b = 255; break;
            case 3: r = 255; g = 255; b = 255; break;
        }
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc == QK_UNDERGLOW_HUE_UP || kc == QK_RGB_MATRIX_HUE_UP)) {   // rgb_hue_up -> rainbow_fwd
        borne_rainbow(true, &r, &g, &b);
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc == QK_UNDERGLOW_HUE_DOWN || kc == QK_RGB_MATRIX_HUE_DOWN)) {   // rgb_hue_down -> rainbow_rev
        borne_rainbow(false, &r, &g, &b);
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc == QK_UNDERGLOW_VALUE_DOWN || kc == QK_RGB_MATRIX_VALUE_DOWN)) {   // rgb_val_down -> saw_down
        { uint8_t v = borne_saw_down(); r = v; g = v; b = v; }
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc == QK_UNDERGLOW_VALUE_UP || kc == QK_RGB_MATRIX_VALUE_UP)) {   // rgb_val_up -> saw_up
        { uint8_t v = borne_saw_up();   r = v; g = v; b = v; }
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc == QK_UNDERGLOW_SPEED_DOWN || kc == QK_RGB_MATRIX_SPEED_DOWN)) {   // rgb_speed_down -> pulse_slow
        { uint8_t v = borne_pulse(BORNE_PULSE_SLOW); r = v; g = v; b = v; }
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc == QK_UNDERGLOW_SPEED_UP || kc == QK_RGB_MATRIX_SPEED_UP)) {   // rgb_speed_up -> pulse_fast
        { uint8_t v = borne_pulse(BORNE_PULSE_FAST); r = v; g = v; b = v; }
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc == QK_UNDERGLOW_MODE_NEXT || kc == QK_UNDERGLOW_MODE_PREVIOUS || kc == QK_RGB_MATRIX_MODE_NEXT || kc == QK_RGB_MATRIX_MODE_PREVIOUS)) {   // rgb_mode -> mode
        r = 85; g = 85; b = 85;
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc >= QK_MOUSE_CURSOR_UP && kc <= QK_MOUSE_CURSOR_RIGHT)) {   // mouse_cursor -> yellow
        r = br; g = br; b = 0;
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc >= QK_MOUSE_BUTTON_1 && kc <= QK_MOUSE_BUTTON_8)) {   // mouse_button -> blue
        r = 0; g = 0; b = br;
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc >= QK_MOUSE_WHEEL_UP && kc <= QK_MOUSE_WHEEL_RIGHT)) {   // mouse_wheel -> green
        r = 0; g = br; b = 0;
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc >= KC_KP_1 && kc <= KC_KP_0)) {   // numpad_digit -> green
        r = 0; g = br; b = 0;
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if (((kc >= KC_KP_SLASH && kc <= KC_KP_ENTER) || kc == KC_KP_DOT || kc == KC_KP_EQUAL || kc == KC_KP_COMMA || kc == KC_KP_EQUAL_AS400)) {   // numpad_op -> blue
        r = 0; g = 0; b = br;
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc >= KC_AUDIO_MUTE && kc <= KC_MEDIA_PLAY_PAUSE)) {   // media -> cyan
        r = 0; g = br; b = br;
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if (IS_QK_MACRO(kc)) {   // macro -> magenta
        r = br; g = 0; b = br;
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc >= KC_F1 && kc <= KC_F12)) {   // fkeys -> yellow
        r = br; g = br; b = 0;
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    if ((kc >= KC_RIGHT && kc <= KC_UP)) {   // arrows -> yellow
        r = br; g = br; b = 0;
        *out_r = r; *out_g = g; *out_b = b; return true;
    }
    return false;
}

static bool borne_status(effect_params_t* params) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);
    uint8_t br = borne_breath_v();
    uint8_t layer = get_highest_layer(layer_state);
    led_t leds = host_keyboard_led_state();
    (void)leds;  // referenced only by gated overrides; silence -Wunused if none

    // 1) breathing-white background + 2) keycode autocolor
    for (uint8_t i = led_min; i < led_max; i++) {
        rgb_matrix_set_color(i, br, br, br);
        uint8_t r, g, b;
        if (borne_classify(borne_effective_keycode(i), br, &r, &g, &b)) {
            rgb_matrix_set_color(i, r, g, b);
        }
    }

    // 3) per-layer overrides (win over autocolor; higher priority emitted last)
    switch (layer) {
        case 0:
            // priority 3: num_lock
            if (leds.num_lock) {
                borne_set(35, led_min, led_max, 0, br, 0);
            }
            // priority 3: caps_lock
            if (leds.caps_lock) {
                borne_set(42, led_min, led_max, 0, br, 0);
            }
            break;
        case 1:
            // priority 2: l1_active_trigger
            borne_set(27, led_min, led_max, br, 0, br);
            // priority 2: l1_l3_trigger_hints
            borne_set(13, led_min, led_max, br, br, 0);
            borne_set(48, led_min, led_max, br, br, 0);
            // priority 3: num_lock
            if (leds.num_lock) {
                borne_set(35, led_min, led_max, 0, br, 0);
            }
            // priority 3: caps_lock
            if (leds.caps_lock) {
                borne_set(42, led_min, led_max, 0, br, 0);
            }
            break;
        case 2:
            // priority 2: l2_active_trigger
            borne_set(13, led_min, led_max, br, 0, br);
            // priority 2: l2_trigger_hints
            borne_set(48, led_min, led_max, br, br, 0);
            // priority 2: l2_lock_base
            borne_set(35, led_min, led_max, 0, br, br);
            borne_set(42, led_min, led_max, 0, br, br);
            // priority 3: num_lock
            if (leds.num_lock) {
                borne_set(35, led_min, led_max, 0, br, 0);
            }
            // priority 3: caps_lock
            if (leds.caps_lock) {
                borne_set(42, led_min, led_max, 0, br, 0);
            }
            break;
        case 3:
            // priority 2: l3_active_trigger
            borne_set(56, led_min, led_max, br, 0, br);
            // priority 2: l1_l3_trigger_hints
            borne_set(13, led_min, led_max, br, br, 0);
            borne_set(48, led_min, led_max, br, br, 0);
            break;
        case 4:
            // priority 2: l4_active_triggers
            borne_set(27, led_min, led_max, br, 0, br);
            borne_set(57, led_min, led_max, br, 0, br);
            break;
        case 5:
            // priority 2: l5_l6_back_indicator
            borne_set(48, led_min, led_max, br, 0, br);
            // priority 2: l5_tab_indicator
            borne_set(13, led_min, led_max, br, br, 0);
            break;
        case 6:
            // priority 2: l5_l6_back_indicator
            borne_set(48, led_min, led_max, br, 0, br);
            // priority 2: l6_tab_indicator
            borne_set(13, led_min, led_max, br, 0, br);
            break;
        case 7:
            // priority 2: l7_finger_hint_green
            borne_set(6, led_min, led_max, 0, br, 0);
            // priority 2: l7_finger_hint_yellow
            borne_set(7, led_min, led_max, br, br, 0);
            borne_set(8, led_min, led_max, br, br, 0);
            borne_set(9, led_min, led_max, br, br, 0);
            borne_set(10, led_min, led_max, br, br, 0);
            borne_set(14, led_min, led_max, br, br, 0);
            borne_set(15, led_min, led_max, br, br, 0);
            borne_set(16, led_min, led_max, br, br, 0);
            borne_set(17, led_min, led_max, br, br, 0);
            borne_set(27, led_min, led_max, br, br, 0);
            borne_set(28, led_min, led_max, br, br, 0);
            borne_set(37, led_min, led_max, br, br, 0);
            borne_set(38, led_min, led_max, br, br, 0);
            borne_set(39, led_min, led_max, br, br, 0);
            borne_set(40, led_min, led_max, br, br, 0);
            borne_set(44, led_min, led_max, br, br, 0);
            borne_set(45, led_min, led_max, br, br, 0);
            borne_set(46, led_min, led_max, br, br, 0);
            borne_set(47, led_min, led_max, br, br, 0);
            borne_set(55, led_min, led_max, br, br, 0);
            borne_set(56, led_min, led_max, br, br, 0);
            break;
        default: break;
    }

    return rgb_matrix_check_finished_leds(led_max);
}
