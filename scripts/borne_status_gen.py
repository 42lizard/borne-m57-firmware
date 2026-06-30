#!/usr/bin/env python3
"""generate source/m57/keymaps/via/borne_status.h from borne_status.toml.

two config layers are lowered into the QMK rgb_matrix custom effect:

1. [[keyrule]] - keycode-driven AUTOCOLORING. every frame, each LED is colored
   by the class of the *live vial keycode* under it on the active layer
   (transparency resolved through the layer stack via keymap_key_to_keycode).
   declared order = match priority (first match wins). this is the bulk of the
   lighting and is independent of the physical layout.

2. [[override]] - per-layer absolute-LED overlays for cues that can't be
   derived from a keycode (active-layer trigger, finger maps, host lock state).
   applied after autocoloring; sorted by priority (higher wins).

precedence per frame (last writer wins):
    breathing-white background -> autocolor -> overrides

the keycode-class -> effect MAPPING lives in the toml; this script only owns
the vocabulary that turns a class name into a C predicate (MATCH_C_EXPR) and an
effect name into C color statements (effect_emit). add a new matcher/effect
primitive here; everything else is a toml edit.

usage:  scripts/borne_status_gen.py
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOML_PATH = ROOT / "source/m57/keymaps/via/borne_status.toml"
OUT_PATH = ROOT / "source/m57/keymaps/via/borne_status.h"

# host-LED-state gates for [[override]] rules.
GATE_C_EXPR = {
    "num_lock_on":    "leds.num_lock",
    "caps_lock_on":   "leds.caps_lock",
    "scroll_lock_on": "leds.scroll_lock",
}

# ---------------------------------------------------------------------------
# keycode-class matchers: name -> C boolean predicate over `kc`.
# uses QMK keycode ranges/macros from quantum/keycodes.h (verified against the
# vial-qmk tree). add a class here, then reference it from [[keyrule]].
# ---------------------------------------------------------------------------
MATCH_C_EXPR = {
    # bootloader / reboot / debug-toggle / clear-eeprom : 0x7C00..0x7C03
    "system_danger": "(kc >= QK_BOOTLOADER && kc <= QK_CLEAR_EEPROM)",
    # any layer-switch keycode
    "layer_switch": (
        "(IS_QK_MOMENTARY(kc) || IS_QK_TO(kc) || IS_QK_LAYER_TAP(kc) || "
        "IS_QK_TOGGLE_LAYER(kc) || IS_QK_LAYER_TAP_TOGGLE(kc) || "
        "IS_QK_DEF_LAYER(kc) || IS_QK_ONE_SHOT_LAYER(kc) || "
        "IS_QK_LAYER_MOD(kc) || kc == QK_LAYER_LOCK)"
    ),
    "mod_tap":  "IS_QK_MOD_TAP(kc)",
    "modifier": "IS_MODIFIER_KEYCODE(kc)",       # plain KC_LEFT_CTRL..KC_RIGHT_GUI
    # RGB control keys - handle both underglow (RGB_*) and rgb-matrix variants
    "rgb_hue_up":     "(kc == QK_UNDERGLOW_HUE_UP || kc == QK_RGB_MATRIX_HUE_UP)",
    "rgb_hue_down":   "(kc == QK_UNDERGLOW_HUE_DOWN || kc == QK_RGB_MATRIX_HUE_DOWN)",
    "rgb_val_up":     "(kc == QK_UNDERGLOW_VALUE_UP || kc == QK_RGB_MATRIX_VALUE_UP)",
    "rgb_val_down":   "(kc == QK_UNDERGLOW_VALUE_DOWN || kc == QK_RGB_MATRIX_VALUE_DOWN)",
    "rgb_speed_up":   "(kc == QK_UNDERGLOW_SPEED_UP || kc == QK_RGB_MATRIX_SPEED_UP)",
    "rgb_speed_down": "(kc == QK_UNDERGLOW_SPEED_DOWN || kc == QK_RGB_MATRIX_SPEED_DOWN)",
    "rgb_mode": (
        "(kc == QK_UNDERGLOW_MODE_NEXT || kc == QK_UNDERGLOW_MODE_PREVIOUS || "
        "kc == QK_RGB_MATRIX_MODE_NEXT || kc == QK_RGB_MATRIX_MODE_PREVIOUS)"
    ),
    "mouse_cursor": "(kc >= QK_MOUSE_CURSOR_UP && kc <= QK_MOUSE_CURSOR_RIGHT)",
    "mouse_button": "(kc >= QK_MOUSE_BUTTON_1 && kc <= QK_MOUSE_BUTTON_8)",
    "mouse_wheel":  "(kc >= QK_MOUSE_WHEEL_UP && kc <= QK_MOUSE_WHEEL_RIGHT)",
    "numpad": (
        "((kc >= KC_KP_SLASH && kc <= KC_KP_DOT) || kc == KC_KP_EQUAL || "
        "kc == KC_KP_COMMA || kc == KC_KP_EQUAL_AS400)"
    ),
    "media":  "(kc >= KC_AUDIO_MUTE && kc <= KC_MEDIA_PLAY_PAUSE)",  # 0xA8..0xAE
    "fkeys":  "(kc >= KC_F1 && kc <= KC_F12)",                       # 0x3A..0x45
    "arrows": "(kc >= KC_RIGHT && kc <= KC_UP)",                     # 0x4F..0x52
    "macro":  "IS_QK_MACRO(kc)",
}

# mod -> color name for the static `mod_static` effect (plain modifier keys).
# index = (kc - KC_LEFT_CTRL) & 0x03 : 0 ctrl, 1 shift, 2 alt, 3 gui.
MOD_STATIC_COLORS = ["green", "red", "blue", "white"]  # ctrl, shift, alt, gui


def color_components(rgb, pulsating):
    """lower an RGB triple to three C expressions, scaled by `br` if pulsating."""
    out = []
    for v in rgb:
        if not pulsating:
            out.append(str(v))
        elif v == 0:
            out.append("0")
        elif v == 255:
            out.append("br")
        else:
            out.append(f"scale8({v}, br)")
    return tuple(out)


def build_led_pos():
    """inverse of m57.c g_led_config matrix block: LED index -> (row, col).
    REGENERATE if m57.c g_led_config changes. None = matrix cell with no LED."""
    matrix = [
        [0,    1,    2,    3,    4,    5,    None],   # row 0  L top
        [6,    7,    8,    9,    10,   11,   12],     # row 1  L Q-row + PgUp
        [13,   14,   15,   16,   17,   18,   19],     # row 2  L home + PgDn
        [20,   21,   22,   23,   24,   25,   None],   # row 3  L Z-row
        [None, None, None, 26,   27,   28,   None],   # row 4  L thumbs
        [None, 29,   30,   31,   32,   33,   34],     # row 5  R top
        [35,   36,   37,   38,   39,   40,   41],     # row 6  R Q-row + [
        [42,   43,   44,   45,   46,   47,   48],     # row 7  R home + Play
        [None, 49,   50,   51,   52,   53,   54],     # row 8  R Z-row
        [None, 55,   56,   57,   None, None, None],   # row 9  R thumbs
    ]
    pos = [None] * 58
    for r, row in enumerate(matrix):
        for c, led in enumerate(row):
            if led is not None:
                pos[led] = (r, c)
    assert all(p is not None for p in pos), "led_pos has holes - check matrix"
    return pos


def effect_emit(effect, colors, anim):
    """C statements assigning local uint8_t r,g,b for a named effect."""
    if effect in colors:                       # plain pulsating color
        r, g, b = color_components(colors[effect], pulsating=True)
        return [f"r = {r}; g = {g}; b = {b};"]
    if effect == "red_static":
        r, g, b = color_components(colors["red"], pulsating=False)
        return [f"r = {r}; g = {g}; b = {b};"]
    if effect == "mode":
        r, g, b = color_components(colors[anim.get("mode_color", "grey")], pulsating=False)
        return [f"r = {r}; g = {g}; b = {b};"]
    if effect == "mod_blend":
        return ["borne_compute_mod_blend(br, true, &r, &g, &b);"]
    if effect == "mod_static":
        lines = ["switch ((kc - KC_LEFT_CTRL) & 0x03) {"]
        for idx, cname in enumerate(MOD_STATIC_COLORS):
            r, g, b = color_components(colors[cname], pulsating=False)
            tail = "break;" if idx < 3 else "break;"
            lines.append(f"    case {idx}: r = {r}; g = {g}; b = {b}; {tail}")
        lines.append("}")
        return lines
    if effect == "rainbow_fwd":
        return ["borne_rainbow(true, &r, &g, &b);"]
    if effect == "rainbow_rev":
        return ["borne_rainbow(false, &r, &g, &b);"]
    if effect == "saw_up":
        return ["{ uint8_t v = borne_saw_up();   r = v; g = v; b = v; }"]
    if effect == "saw_down":
        return ["{ uint8_t v = borne_saw_down(); r = v; g = v; b = v; }"]
    if effect == "pulse_fast":
        return ["{ uint8_t v = borne_pulse(BORNE_PULSE_FAST); r = v; g = v; b = v; }"]
    if effect == "pulse_slow":
        return ["{ uint8_t v = borne_pulse(BORNE_PULSE_SLOW); r = v; g = v; b = v; }"]
    raise SystemExit(f"unknown effect {effect!r}")


def emit_override(rule, colors, lines, indent):
    """emit one [[override]] rule (absolute LED list, optional host-state gate)."""
    leds_list = rule["leds"]
    gate = rule.get("gate")
    sub = indent
    if gate is not None:
        if gate not in GATE_C_EXPR:
            raise SystemExit(f"unknown gate {gate!r} on override {rule.get('id')!r}")
        lines.append(f"{indent}if ({GATE_C_EXPR[gate]}) {{")
        sub = indent + "    "
    color_field = rule["color"]
    if color_field not in colors:
        raise SystemExit(f"unknown color {color_field!r} on override {rule.get('id')!r}")
    r, g, b = color_components(colors[color_field], rule.get("pulsating", False))
    for led in leds_list:
        lines.append(f"{sub}borne_set({led}, led_min, led_max, {r}, {g}, {b});")
    if gate is not None:
        lines.append(f"{indent}}}")


def main():
    with TOML_PATH.open("rb") as f:
        cfg = tomllib.load(f)
    colors = cfg.get("colors", {})
    anim = cfg.get("anim", {})
    keyrules = cfg.get("keyrule", [])
    overrides = cfg.get("override", [])

    led_pos = build_led_pos()

    # validate keyrules up front
    for kr in keyrules:
        if kr["match"] not in MATCH_C_EXPR:
            raise SystemExit(f"unknown match {kr['match']!r} in [[keyrule]]")

    # layers that have any override
    used_layers = sorted({l for r in overrides for l in r["layers"]})

    def overrides_for_layer(layer):
        out = [r for r in overrides if layer in r["layers"]]
        out.sort(key=lambda r: (r["priority"], overrides.index(r)))
        return out

    L = []
    a = L.append
    a("#pragma once")
    a("// AUTO-GENERATED from borne_status.toml.")
    a("// Do not edit by hand - run scripts/borne_status_gen.py to regenerate.")
    a("//")
    a("// included once from rgb_matrix_user.inc inside the")
    a("// RGB_MATRIX_CUSTOM_EFFECT_IMPLS guard so symbols stay file-scoped.")
    a("")
    a('#include "quantum.h"')
    a("")
    a(f"#define BORNE_RAINBOW_SHIFT {anim.get('rainbow_shift', 4)}")
    a(f"#define BORNE_SAW_SHIFT     {anim.get('saw_shift', 3)}")
    a(f"#define BORNE_PULSE_FAST    {anim.get('pulse_fast', 4)}")
    a(f"#define BORNE_PULSE_SLOW    {anim.get('pulse_slow', 16)}")
    a("")
    # LED index -> {row, col}
    a("// LED index -> {row, col}; inverse of m57.c g_led_config.")
    a("// REGENERATE (rerun this script) if g_led_config ever changes.")
    a("static const uint8_t borne_led_pos[58][2] = {")
    row_str = ", ".join(f"{{{r},{c}}}" for (r, c) in led_pos)
    a(f"    {row_str}")
    a("};")
    a("")
    # base breathing wave (unchanged)
    a("static uint8_t borne_breath_v(void) {")
    a("    return scale8(")
    a("        abs8(sin8(scale16by8(g_rgb_timer, rgb_matrix_config.speed / 8)) - 128) * 2,")
    a("        rgb_matrix_config.hsv.v);")
    a("}")
    a("")
    # variable-speed pulse for RGB speed keys
    a("// pulse like borne_breath_v but with a tunable speed divisor (smaller = faster).")
    a("static uint8_t borne_pulse(uint8_t spd_div) {")
    a("    if (spd_div == 0) spd_div = 1;")
    a("    uint8_t s = sin8(scale16by8(g_rgb_timer, rgb_matrix_config.speed / spd_div));")
    a("    return scale8(abs8(s - 128) * 2, rgb_matrix_config.hsv.v);")
    a("}")
    a("")
    # sawtooth brightness for RGB value keys
    a("static uint8_t borne_saw_up(void)   { return (uint8_t)(g_rgb_timer >> BORNE_SAW_SHIFT); }")
    a("static uint8_t borne_saw_down(void) { return (uint8_t)(255 - (uint8_t)(g_rgb_timer >> BORNE_SAW_SHIFT)); }")
    a("")
    # rainbow cycle for RGB hue keys
    a("static void borne_rainbow(bool fwd, uint8_t *r, uint8_t *g, uint8_t *b) {")
    a("    uint8_t h = (uint8_t)(g_rgb_timer >> BORNE_RAINBOW_SHIFT);")
    a("    if (!fwd) h = (uint8_t)(-h);")
    a("    hsv_t hsv = { h, 255, 255 };")
    a("    rgb_t c = hsv_to_rgb(hsv);")
    a("    *r = c.r; *g = c.g; *b = c.b;")
    a("}")
    a("")
    # mod blend (unchanged) - used by mod-tap keys
    a("// chart-encoded modifier blend: shift->R, ctrl->G, alt->B,")
    a("// gui bumps base 0x00->0x55 and high 0xAA->0xFF. RGB(0,0,0) when no mods held.")
    a("static void borne_compute_mod_blend(uint8_t br, bool pulsate,")
    a("                                    uint8_t *out_r, uint8_t *out_g, uint8_t *out_b) {")
    a("    uint8_t mods = get_mods() | get_weak_mods() | get_oneshot_mods();")
    a("    bool sft = mods & MOD_MASK_SHIFT;")
    a("    bool alt = mods & MOD_MASK_ALT;")
    a("    bool ctl = mods & MOD_MASK_CTRL;")
    a("    bool gui = mods & MOD_MASK_GUI;")
    a("    uint8_t base = gui ? 0x55 : 0x00;")
    a("    uint8_t high = gui ? 0xFF : 0xAA;")
    a("    uint8_t r = sft ? high : base;")
    a("    uint8_t g = ctl ? high : base;")
    a("    uint8_t b = alt ? high : base;")
    a("    if (pulsate) { r = scale8(r, br); g = scale8(g, br); b = scale8(b, br); }")
    a("    *out_r = r; *out_g = g; *out_b = b;")
    a("}")
    a("")
    a("static inline void borne_set(uint8_t led, uint8_t led_min, uint8_t led_max,")
    a("                              uint8_t r, uint8_t g, uint8_t b) {")
    a("    if (led >= led_min && led < led_max) rgb_matrix_set_color(led, r, g, b);")
    a("}")
    a("")
    # effective keycode with transparency fall-through (mirrors layer_switch_get_layer)
    a("// resolve the effective keycode under an LED, walking the active layer stack")
    a("// the same way QMK's layer_switch_get_layer does (incl. default_layer_state,")
    a("// skip on KC_TRANSPARENT only, fall back to layer 0).")
    a("static uint16_t borne_effective_keycode(uint8_t led) {")
    a("    keypos_t pos = { .row = borne_led_pos[led][0], .col = borne_led_pos[led][1] };")
    a("    layer_state_t active = layer_state | default_layer_state;")
    a("    for (int8_t l = MAX_LAYER - 1; l >= 0; l--) {")
    a("        if (active & ((layer_state_t)1 << l)) {")
    a("            uint16_t kc = keymap_key_to_keycode(l, pos);")
    a("            if (kc != KC_TRANSPARENT) return kc;")
    a("        }")
    a("    }")
    a("    return keymap_key_to_keycode(0, pos);")
    a("}")
    a("")
    # the autocolor classifier, generated from [[keyrule]] order
    a("// keycode-class -> color. returns true if handled (caller keeps background")
    a("// otherwise). generated from the ordered [[keyrule]] table in borne_status.toml.")
    a("static bool borne_classify(uint16_t kc, uint8_t br,")
    a("                           uint8_t *out_r, uint8_t *out_g, uint8_t *out_b) {")
    a("    uint8_t r = 0, g = 0, b = 0;")
    for kr in keyrules:
        a(f"    if ({MATCH_C_EXPR[kr['match']]}) {{   // {kr['match']} -> {kr['effect']}")
        for line in effect_emit(kr["effect"], colors, anim):
            a(f"        {line}")
        a("        *out_r = r; *out_g = g; *out_b = b; return true;")
        a("    }")
    a("    return false;")
    a("}")
    a("")
    # main effect
    a("static bool borne_status(effect_params_t* params) {")
    a("    RGB_MATRIX_USE_LIMITS(led_min, led_max);")
    a("    uint8_t br = borne_breath_v();")
    a("    uint8_t layer = get_highest_layer(layer_state);")
    a("    led_t leds = host_keyboard_led_state();")
    a("    (void)leds;  // referenced only by gated overrides; silence -Wunused if none")
    a("")
    a("    // 1) breathing-white background + 2) keycode autocolor")
    a("    for (uint8_t i = led_min; i < led_max; i++) {")
    a("        rgb_matrix_set_color(i, br, br, br);")
    a("        uint8_t r, g, b;")
    a("        if (borne_classify(borne_effective_keycode(i), br, &r, &g, &b)) {")
    a("            rgb_matrix_set_color(i, r, g, b);")
    a("        }")
    a("    }")
    a("")
    a("    // 3) per-layer overrides (win over autocolor; higher priority emitted last)")
    a("    switch (layer) {")
    for layer in used_layers:
        applicable = overrides_for_layer(layer)
        if not applicable:
            continue
        a(f"        case {layer}:")
        for r in applicable:
            a(f"            // priority {r['priority']}: {r['id']}")
            emit_override(r, colors, L, "            ")
        a("            break;")
    a("        default: break;")
    a("    }")
    a("")
    a("    return rgb_matrix_check_finished_leds(led_max);")
    a("}")

    OUT_PATH.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT_PATH.relative_to(ROOT)} ({len(L)} lines)")
    print(f"  keyrules: {len(keyrules)}  overrides: {len(overrides)}  override-layers: {used_layers}")


if __name__ == "__main__":
    main()
