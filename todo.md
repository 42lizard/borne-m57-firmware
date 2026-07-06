# todo

## done

### led_config rewrite [shipped, commit `8c3e666`]

vendor mapping had matrix rows in L/R/L/R alternating order instead of 0-4=left, 5-9=right. rewrote to match actual hardware chain after per-key verification on both halves via `solid_reactive_simple`. final state captured in `source/m57/m57.c` and verified working.

### bootloader_jump for QK_BOOT [shipped, commit `6ab532f`]

vendor set `BOOTLOADER=custom` in info.json but never wrote the implementation - QK_BOOT and vial reset were both no-ops. found PlumBL upstream at https://github.com/HaiMianBBao/PlumBL: magic `0xc220b134` at `0x2000fc00`, then `NVIC_SystemReset()`. now QK_BOOT triggers DFU mode, no tweezers needed.

### build pipeline + flash automation [shipped]

- vial-qmk source tree at `~/projects/vial-qmk` with `source/m57` symlinked into `keyboards/`, ld scripts in `platforms/chibios/boards/common/ld/`
- `nix-shell -p qmk --run "make m57:via"` builds cleanly
- `scripts/flash.sh` watches for `Adafruit PlumBootloader`, mounts the disk, copies uf2, syncs, polls for firmware reboot. one command, ~5 seconds end-to-end

### docs + github [shipped]

- README with hardware spec, patches, build, flash procedure, repo layout
- photo of reset pad location (`docs/reset-pads.png`)
- public repo at https://github.com/sophronesis/borne-m57-firmware

## open / future

### feature: per-key static color override

use `rgb_matrix_indicators_advanced_user` in `source/m57/keymaps/via/keymap.c` - paints on top of whatever animation is running, every frame.

decide first:
- which keys / which colors
- always on, or only on specific layer, or only when pressed

example shape (fill in matrix positions + rgb):

```c
bool rgb_matrix_indicators_advanced_user(uint8_t led_min, uint8_t led_max) {
    uint8_t led = g_led_config.matrix_co[row][col];
    if (led != NO_LED && led >= led_min && led < led_max) {
        rgb_matrix_set_color(led, R, G, B);
    }
    return false;
}
```

alt path for reactive-tint only: change default hue via `rgb_matrix_sethsv_noeeprom(h,s,v)` in `keyboard_post_init_user` - cheaper than indicators but affects all effects.

### feature: modifier-held highlighting

same hook (`rgb_matrix_indicators_advanced_user`), use `get_mods() | get_oneshot_mods()` to read current modifier state. recommended variant: highlight the mod key itself - catches stuck mods and one-shot state with low visual noise.

```c
uint8_t mods = get_mods() | get_oneshot_mods();
if (mods & MOD_MASK_SHIFT) { rgb_matrix_set_color(led_for_shift, R, G, B); }
// ... CTRL / ALT / GUI similarly
```

### feature: MO1+MO3 chord to reach a new layer

from layer 0, holding MO1 then MO3 should activate an extra layer (tri-layer style). standard qmk pattern is `update_tri_layer_state(state, 1, 3, N)` inside `layer_state_set_user` in `source/m57/keymaps/via/keymap.c`, where N is the new layer index.

decisions before coding:
- target layer index. 10 dynamic layers are already configured (`DYNAMIC_KEYMAP_LAYER_COUNT = 10`), so pick a free slot or bump the count (and check eeprom budget against the 4kb cap).
- what goes on the new layer. without a defined keymap it's just dead weight.
- whether to add it as a vial-editable dynamic layer or hardcode in source.

### feature: layer indicator

with 10 dynamic layers configured, a single LED (or zone) showing active layer pays off quickly. same hook + `get_highest_layer(layer_state)`. consider mapping each layer to a distinct hue.

### nice-to-have: fix info.json syntax

`source/m57/info.json` has a missing comma + trailing commas around the `[9, 2]` / `[9, 3]` block near the end of layout. qmk parses it anyway but `qmk lint -kb m57` complains. low priority - only matters if someone runs the linter as part of CI.

### nice-to-have: right half asymmetry doc

right half led_config doesn't perfectly mirror left - PCB chain order differs slightly (e.g., LED 48 is at home row inner extra physically but in chain order it's between home and Z rows). worth a short comment in `m57.c` explaining the asymmetry for future readers.

### bug: scroll lock indicator never lights on linux/wayland

`scroll_lock` rule in `source/m57/keymaps/via/borne_status.toml` never fires because linux (gnome/wayland in this case) sees the KC_SCROLLLOCK keypress in `wev` but doesn't toggle the host scroll-lock state - so no LED set output report comes back to the keyboard, so `host_keyboard_led_state().scroll_lock` stays 0 forever. caps + num lock both work via the same path, so the firmware side is fine; this is purely an OS quirk.

workaround paths, in order of robustness:
1. **firmware-side toggle.** define a user keycode in `keymap.c` that flips a global `bool borne_user_indicator = !borne_user_indicator;` on press, bind it to LED 54 on layer 3 in vial. add a new gate (e.g., `gate = "user_flag_0"`) to the toml's scroll_lock rule and extend `GATE_C_EXPR` in `scripts/borne_status_gen.py` to recognize it. independent of OS behavior. ~10 lines plumbing total.
2. **repurpose the slot.** scroll lock is dead weight on modern linux anyway - bind LED 54 to a layer-toggle / mute / macro and drop the rule.
3. **switch the gate to compose / kana.** other HID lock bits that some compositors actually flip; `host_keyboard_led_state()` exposes them too.

option 1 is the right call since it survives any future OS shenanigans; do it next time the toml is touched.

### perf: shave cold-boot enumeration delay (~10s observed)

**RESOLVED 2026-07-06** (commit 033a2ab): the real culprit was none of the
below - `SPLIT_USB_DETECT`'s 2s window expired during FW16 POST silence and
the cabled half declared itself slave (enumerated but mute). Fixed with an
asymmetric `is_keyboard_master_impl` override + usb self-heal in m57.c.
PlumBL was measured innocent (cold path jumps immediately). Keyboard is
HID-ready 1.9s after kernel start at the LUKS prompt now. Estimates below
kept for history:

bcorne takes ~10s to enumerate after host USB hub powers on - causes LUKS keyboard not to register at unlock prompt on FW16, requires unplug/replug (see nixos repo `feedback_hyprland_tearing_edp.md` and FW16 hardware-configuration.nix `wait-for-bcorne` workaround).

breakdown of the 10s (estimated, would need scope/printf to confirm exact):
- PlumBL boot-mode-detect window: ~2-3s (UF2 bootloader waits for double-tap reset before jumping to user firmware)
- `SPLIT_USB_DETECT` poll loop: up to 2s (`SPLIT_USB_TIMEOUT 2000` in `config.h`)
- `SPLIT_WATCHDOG_TIMEOUT 3000` first-cycle wait
- USART init + split sync handshake: ~1s
- RGB matrix DMA init (WS2812 PWM driver): ~0.5s
- USB device descriptor enumeration: ~1s

two firmware-side fixes that are low risk and quick to test:

1. **drop `SPLIT_USB_DETECT`** in `source/m57/config.h:102`. you already have `MASTER_RIGHT` (role hardcoded) + `SPLIT_HAND_PIN C1` (hand detected by pin). USB-detect is redundant when role is fixed by define. saves ~2s. try first - cleanest change, just one line removed.

2. **reduce `SPLIT_USB_TIMEOUT` from 2000 to 500** in `config.h:103`. trades robustness for speed - if the split sync handshake fails fast it just retries on next cycle. saves another ~1.5s. do this only if #1 isn't enough.

won't get to <2s but should land in the 5-6s range, which combined with the nixos-side `wait-for-bcorne` initrd service (max 15s wait) gives plenty of margin for LUKS prompt.

**not** worth attempting:
- patching out PlumBL boot-mode-detect delay - bricks the kbd if the double-tap reset detection breaks. not worth the recovery hassle for ~2s.

### bug: left half keypresses register as right-half matrix coordinates

with `MASTER_RIGHT` + `SPLIT_HAND_PIN C1` + `SPLIT_HAND_PIN_LOW_IS_LEFT` in `source/m57/config.h`, each half decides which side it is at boot by reading pin C1: low = left (slave), high/floating = right (master). symptom "left keys appear as right-side input on the host, but right keys work fine" is the left half booting with C1 floating high - left half thinks it's right, fills the right-side rows with its own matrix state, and the actual left rows (0-4) never get populated. right side works because right's C1 is supposed to read high anyway.

fix paths in order of effort:

1. **switch to EE_HANDS.** uncomment `#define EE_HANDS` in `config.h:50` and remove (or guard) `SPLIT_HAND_PIN` / `SPLIT_HAND_PIN_LOW_IS_LEFT`. then reflash each half with matching handedness via the qmk cli (`-bl uf2-split-left` / `-bl uf2-split-right`) or two per-side build targets. hand state lives in eeprom, no pin reading involved - survives any C1 trace damage.
2. **fix the hardware.** put a multimeter on MCU pin C1 of the LEFT pcb when powered - should read 0V to GND. if it reads ~3.3V, the trace from C1 to GND (or the L / "left" jumper pad on the back of the pcb) is broken. resolder the bridge.

option 1 is the right call - one config change, two flashes, no soldering.
