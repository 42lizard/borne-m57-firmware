#!/usr/bin/env python3
"""extract per-layer key data from a vial .vil keymap into docs/led_layers.json,
the data source for docs/led_layers.html (the LED-pattern visualizer).

for every layer, every physical key, emits: matrix position, LED index, the
bound keycode + the effective keycode after KC_TRNS fall-through to layer 0, a
human label, and the autocolor it lights as - derived from the SAME [[keyrule]]
/ [[override]] rules in borne_status.toml that drive the firmware, so the page
stays in sync with the real lighting. the .vil is NOT embedded in the html;
this json is the single reference the page fetches.

usage: scripts/led_layers_data.py [path-to .vil]   (default: vil_backups/current.vil)
"""
from __future__ import annotations
import json, re, sys, tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOML = ROOT / "source/m57/keymaps/via/borne_status.toml"
OUT = ROOT / "docs/led_layers.json"
VIL = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "vil_backups/current.vil"

# matrix (row,col) -> LED index (None = key/slot with no LED). from m57.c g_led_config.
LED_MATRIX = [
    [0,    1,    2,    3,    4,    5,    None],
    [6,    7,    8,    9,    10,   11,   12],
    [13,   14,   15,   16,   17,   18,   19],
    [20,   21,   22,   23,   24,   25,   None],
    [None, None, None, 26,   27,   28,   None],
    [None, 29,   30,   31,   32,   33,   34],
    [35,   36,   37,   38,   39,   40,   41],
    [42,   43,   44,   45,   46,   47,   48],
    [None, 49,   50,   51,   52,   53,   54],
    [None, 55,   56,   57,   None, None, None],
]

MEDIA = {"KC_MPLY", "KC_MUTE", "KC_MNXT", "KC_MPRV", "KC_MSTP",
         "KC_VOLU", "KC_VOLD", "KC_AUDIO_MUTE", "KC_AUDIO_VOL_UP",
         "KC_AUDIO_VOL_DOWN", "KC_MEDIA_PLAY_PAUSE", "KC_MEDIA_NEXT_TRACK",
         "KC_MEDIA_PREV_TRACK", "KC_MEDIA_STOP"}

# keycode -> [[keyrule]] match-class name (mirrors MATCH_C_EXPR in borne_status_gen.py)
def kc_class(kc: str):
    if kc in ("QK_BOOT", "QK_BOOTLOADER", "QK_REBOOT", "QK_RBT",
              "QK_CLEAR_EEPROM", "EE_CLR", "QK_DEBUG_TOGGLE", "DB_TOGG"):
        return "system_danger"
    if re.match(r"^(MO|TO|TG|TT|DF|OSL|LM)\(", kc) or re.match(r"^LT\d*\(", kc):
        return "layer_switch"                      # NB: QK_LAYER_LOCK intentionally excluded
    if re.match(r"^[A-Z][A-Z_]*_T\(", kc):
        return "mod_tap"
    if kc in ("KC_LCTRL", "KC_LCTL", "KC_RCTRL", "KC_RCTL", "KC_LSHIFT", "KC_LSFT",
              "KC_RSHIFT", "KC_RSFT", "KC_LALT", "KC_RALT", "KC_LGUI", "KC_RGUI"):
        return "modifier"
    if kc in ("RGB_HUI",): return "rgb_hue_up"
    if kc in ("RGB_HUD",): return "rgb_hue_down"
    if kc in ("RGB_VAI",): return "rgb_val_up"
    if kc in ("RGB_VAD",): return "rgb_val_down"
    if kc in ("RGB_SPI",): return "rgb_speed_up"
    if kc in ("RGB_SPD",): return "rgb_speed_down"
    if kc in ("RGB_MOD", "RGB_RMOD"): return "rgb_mode"
    if kc in ("KC_MS_U", "KC_MS_D", "KC_MS_L", "KC_MS_R"): return "mouse_cursor"
    if kc in ("KC_BTN1", "KC_BTN2", "KC_BTN3", "KC_BTN4", "KC_BTN5"): return "mouse_button"
    if kc in ("KC_WH_U", "KC_WH_D", "KC_WH_L", "KC_WH_R"): return "mouse_wheel"
    if re.match(r"^KC_KP_[0-9]$", kc): return "numpad_digit"
    if kc.startswith("KC_KP_"): return "numpad_op"
    if kc in MEDIA: return "media"
    if re.match(r"^M\d+$", kc): return "macro"
    if re.match(r"^KC_F([1-9]|1[0-2])$", kc): return "fkeys"
    if kc in ("KC_UP", "KC_DOWN", "KC_LEFT", "KC_RIGHT"): return "arrows"
    return None

# which modifier a key represents -> color name (for the mod_static effect)
def mod_color(kc: str):
    inner = kc[:-1] if not kc.startswith("KC_") else kc
    if "CTL" in kc or "CTRL" in kc: return "green"
    if "SFT" in kc or "SHIFT" in kc: return "red"
    if "ALT" in kc: return "blue"
    if "GUI" in kc: return "white"
    return "white"

# friendly label -> (main, sub)
BASIC = {
    "KC_ESCAPE": "Esc", "KC_BSPACE": "Bspc", "KC_SPACE": "Spc", "KC_ENTER": "Ent",
    "KC_TAB": "Tab", "KC_DELETE": "Del", "KC_GRAVE": "`", "KC_MINUS": "-",
    "KC_EQUAL": "=", "KC_LBRACKET": "[", "KC_RBRACKET": "]", "KC_BSLASH": "\\",
    "KC_SCOLON": ";", "KC_QUOTE": "'", "KC_COMMA": ",", "KC_DOT": ".", "KC_SLASH": "/",
    "KC_HOME": "Home", "KC_END": "End", "KC_INSERT": "Ins", "KC_PAUSE": "Pause",
    "KC_SCROLLLOCK": "ScrLk", "KC_NUMLOCK": "NumLk", "KC_CAPSLOCK": "Caps",
    "KC_PSCREEN": "PrSc", "KC_PGUP": "PgUp", "KC_PGDOWN": "PgDn",
    "KC_UP": "↑", "KC_DOWN": "↓", "KC_LEFT": "←", "KC_RIGHT": "→",
    "KC_MS_U": "Ms↑", "KC_MS_D": "Ms↓", "KC_MS_L": "Ms←", "KC_MS_R": "Ms→",
    "KC_WH_U": "Wh↑", "KC_WH_D": "Wh↓", "KC_WH_L": "Wh←", "KC_WH_R": "Wh→",
    "KC_BTN1": "Btn1", "KC_BTN2": "Btn2", "KC_BTN3": "Btn3",
    "KC_MPLY": "Play", "KC_MUTE": "Mute", "KC_MNXT": "Next", "KC_MPRV": "Prev",
    "KC_VOLU": "Vol+", "KC_VOLD": "Vol-",
    "RGB_HUI": "Hue+", "RGB_HUD": "Hue-", "RGB_SAI": "Sat+", "RGB_SAD": "Sat-",
    "RGB_VAI": "Val+", "RGB_VAD": "Val-", "RGB_SPI": "Spd+", "RGB_SPD": "Spd-",
    "RGB_MOD": "RGB+", "RGB_RMOD": "RGB-",
    "QK_BOOT": "BOOT", "QK_LAYER_LOCK": "LLck", "MAGIC_TOGGLE_NKRO": "NKRO",
    "KC_KP_ASTERISK": "KP*", "KC_KP_PLUS": "KP+", "KC_KP_MINUS": "KP-",
    "KC_KP_DOT": "KP.", "KC_KP_COMMA": "KP,", "KC_KP_EQUAL": "KP=", "KC_KP_SLASH": "KP/",
    "KC_KP_ENTER": "KPEnt",
}
MODSHORT = {"LGUI": "Win", "RGUI": "Win", "LCTL": "Ctl", "RCTL": "Ctl",
            "LSFT": "Sft", "RSFT": "Sft", "LALT": "Alt", "RALT": "Alt",
            "ALL": "Hyp", "MEH": "Meh", "HYPR": "Hyp", "SGUI": "W+S", "LCA": "LCA"}

def label_for(kc: str):
    if kc in BASIC:
        return BASIC[kc], None
    if re.match(r"^KC_KP_[0-9]$", kc):
        return "KP" + kc[-1], None
    m = re.match(r"^KC_([A-Z0-9])$", kc)               # letters/digits
    if m:
        return m.group(1), None
    m = re.match(r"^([A-Z][A-Z_]*)_T\(KC_([A-Z0-9]+)\)$", kc)   # mod-tap
    if m:
        key = m.group(2)
        return (key if len(key) == 1 else BASIC.get("KC_" + key, key)), MODSHORT.get(m.group(1), m.group(1))
    m = re.match(r"^LT(\d*)\(KC_([A-Z0-9]+)\)$", kc)   # layer-tap
    if m:
        key = m.group(2)
        lab = key if len(key) == 1 else BASIC.get("KC_" + key, key)
        return lab, "L" + (m.group(1) or "?")
    m = re.match(r"^(MO|TO|TG|TT|DF|OSL)\((\d+)\)$", kc)
    if m:
        return m.group(1) + m.group(2), None
    m = re.match(r"^(LGUI|RGUI|LCTL|RCTL|LSFT|RSFT|LALT|RALT|ALL|MEH|HYPR|SGUI|LCA)\(KC_([A-Z0-9]+)\)$", kc)
    if m:                                              # modded tap (e.g. LGUI(A))
        key = m.group(2)
        return (key if len(key) == 1 else BASIC.get("KC_" + key, key)), MODSHORT.get(m.group(1), m.group(1))
    if re.match(r"^M\d+$", kc):
        return kc, "macro"
    return kc.replace("KC_", "").replace("_", " ").title()[:6], None


def main():
    with TOML.open("rb") as f:
        cfg = tomllib.load(f)
    colors = cfg["colors"]
    keyrules = {kr["match"]: kr["effect"] for kr in cfg.get("keyrule", [])}
    # overrides: {layer: {led: [override,...]}}. a key may have a non-gated base
    # color AND gated (lock-state) overlays; keep them all so both survive.
    overrides = {}
    for ov in cfg.get("override", []):
        for layer in ov["layers"]:
            d = overrides.setdefault(layer, {})
            for led in ov["leds"]:
                d.setdefault(led, []).append({
                    "color": ov["color"], "pulse": ov.get("pulsating", False),
                    "gate": ov.get("gate"), "priority": ov["priority"]})

    vil = json.loads(VIL.read_text())
    layout = vil["layout"]

    # effect name -> (color_token, pulsating). special tokens kept as-is for the page.
    def effect_color(effect, kc):
        if effect in colors:
            return effect, True                       # plain pulsating color name
        if effect == "red_static":   return "red", False
        if effect == "mode":         return "grey", False
        if effect == "mod_static":   return mod_color(kc), False
        if effect == "mod_blend":    return "modblend", True
        if effect == "rainbow_fwd":  return "rainbow", True
        if effect == "rainbow_rev":  return "rainbow", True
        if effect in ("saw_up", "saw_down"):     return "saw", True
        if effect in ("pulse_fast", "pulse_slow"): return "pulse", True
        return "bg", True

    out_layers = []
    for li, layer in enumerate(layout):
        keys = []
        for r in range(10):
            for c in range(7):
                raw = layer[r][c]
                if raw == -1:
                    continue                          # no physical key
                led = LED_MATRIX[r][c]
                # resolve transparency -> layer 0 (the always-active default base)
                trns = (raw == "KC_TRNS")
                eff = layout[0][r][c] if (trns and li != 0) else raw
                if eff in ("KC_TRNS", "KC_NO", -1):
                    color, pulse, note = "bg", True, None
                    label, sub = ("", None)
                else:
                    label, sub = label_for(eff)
                    cls = kc_class(eff)
                    if cls and cls in keyrules:
                        color, pulse = effect_color(keyrules[cls], eff)
                    else:
                        color, pulse = "bg", True
                    note = None
                # apply layer overrides. highest-priority NON-gated override sets
                # the base color (wins over autocolor); gated ones add a note.
                ovs = overrides.get(li, {}).get(led, []) if led is not None else []
                base = sorted([o for o in ovs if not o["gate"]], key=lambda o: o["priority"])
                if base:
                    color, pulse = base[-1]["color"], base[-1]["pulse"]
                gated = [o for o in ovs if o["gate"]]
                if gated:
                    note = "; ".join(
                        f"→ {o['color']} when {o['gate'].replace('_on','').replace('_',' ')} on"
                        for o in gated)
                keys.append({
                    "r": r, "c": c, "led": led,
                    "kc": raw, "eff": eff, "label": label, "sub": sub,
                    "trns": trns, "color": color, "pulse": pulse, "note": note,
                })
        out_layers.append({"layer": li, "keys": keys})

    palette = {k: v for k, v in colors.items()}
    data = {
        "meta": {"source": VIL.name, "leds": 58, "layers": len(layout),
                 "note": "generated by scripts/led_layers_data.py - do not hand-edit"},
        "palette": palette,
        "layers": out_layers,
    }
    OUT.write_text(json.dumps(data, indent=1) + "\n")
    nk = sum(len(l["keys"]) for l in out_layers)
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(out_layers)} layers, {nk} keys)  from {VIL}")


if __name__ == "__main__":
    main()
