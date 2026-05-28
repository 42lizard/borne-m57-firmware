VIAL_ENABLE = yes
VIALRGB_ENABLE     = yes
VIAL_INSECURE = yes
ENCODER_MAP_ENABLE = yes
VIA_ENABLE = yes
RGB_MATRIX_CUSTOM_USER = yes

# stenography uses plover's "Keyboard" machine (host-side hid intercept), not
# qmk's STENO_ENABLE/VIRTSER which won't fit on stm32f401's 3 usb endpoints
# alongside vial's raw_hid. layer 7 just sends regular hid keystrokes and
# plover hijacks them. NKRO is critical so simultaneous chord keys all reach
# the host. see ~/projects/keyboard_borne_steno.
NKRO_ENABLE = yes

# urob-style "timeless" home row mods on layer 0.
# CHORDAL_HOLD resolves cross-hand mod-tap holds instantly (no tapping-term wait).
# same-hand holds still need TAPPING_TERM. requires recent vial-qmk (post-2024
# qmk rebase). if build fails with "unknown CHORDAL_HOLD", drop this and rely
# on HOLD_ON_OTHER_KEY_PRESS only - it's worse but works on older trees.
CHORDAL_HOLD = yes
