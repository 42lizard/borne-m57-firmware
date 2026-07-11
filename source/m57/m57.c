#include "m57.h"

#ifdef RGB_MATRIX_ENABLE

/*
led_config_t g_led_config = {
    {

         { 0,  1,  2,  3,  4  },
         { 5,  6,  7,  8,  9  },
         { 10, 11, 12, 13, 14 },
         { NO_LED,  NO_LED,  15, 16, 17 },
         { 18,  19,  20, 21, 22 },
         { 23,  24,  25, 26, 27 },
         { 28,  29,  30, 31, 32 },
         { 33,  34,  35, NO_LED,NO_LED }
    },

  {
        // LED Index to Physical Position
         {0,15},   {24,15}, {48,15}, {72,15}, {96,15},
         {0,30},   {24,30}, {48,30}, {72,30}, {96,30},
         {0,45},   {24,45}, {48,45}, {72,45}, {96,45},
                            {48,63}, {72,63}, {96,63},

         {120,15}, {144,15}, {168,15}, {192,15}, {223,15},
         {120,30}, {144,30}, {168,30}, {192,30}, {223,30},
         {120,45}, {144,45}, {168,45}, {192,45}, {223,45},
         {120,63}, {144,63}, {168,63},

     },

 {
      // LED Index to Flag
      4,4,4,4,4,\
      4,4,4,4,4,\
      4,4,4,4,4,\
          4,4,4,\
      4,4,4,4,4,\
      4,4,4,4,4,\
      4,4,4,4,4,\
      4,4,4,\
    }
};
*/
led_config_t g_led_config = {
    {

         // matrix rows 0-4 = left half, rows 5-9 = right half (sequential, not paired)
         // chain order (left): top(0-5) > Q row(6-11) > PgUp(12) > home row(13-18) > Mute(19) > Z row(20-25) > thumbs(26-28)
         // PgDn (matrix 2,6) has no under-key LED. right half mirrored.
         { 0,      1,      2,      3,      4,      5,      NO_LED },                // matrix row 0: L top row (Esc/1/2/3/4/5)
         { 6,      7,      8,      9,      10,     11,     12 },                    // matrix row 1: L Q row + PgUp (LED 12 at (1,6))
         { 13,     14,     15,     16,     17,     18,     19 },                    // matrix row 2: L home row + PgDn (LED 19 at (2,6))
         { 20,     21,     22,     23,     24,     25,     NO_LED },                // matrix row 3: L Z row, Mute no LED (no LED at (3,6))
         { NO_LED, NO_LED, NO_LED, 26,     27,     28,     NO_LED },                // matrix row 4: L thumbs - Del=26, MO(1)=27, Space=28
         { NO_LED, 29,     30,     31,     32,     33,     34 },                    // matrix row 5: R top row (cols ascending)
         { 35,     36,     37,     38,     39,     40,     41 },                    // matrix row 6: R Q row + "{[" (cols 0-6 ascending, all align matrix col)
         { 42,     43,     44,     45,     46,     47,     48 },                    // matrix row 7: R home row + MediaPlay (cols 0-6 ascending)
         { NO_LED, 49,     50,     51,     52,     53,     54 },                    // matrix row 8: R Z row, "}]" no LED (col 0 silent, cols 1-6 ascending)
         { NO_LED, 55,     56,     57,     NO_LED, NO_LED, NO_LED },                // matrix row 9: R thumbs - Enter=55, MO(3)=56, Bksp=57 (mirror)
   
    },

  {
        // LED Index to Physical Position
         {0,12},   {16,12}, {32,12}, {48,12}, {64,12},{80,12},              //             {128,12}, {144,12}, {160,12}, {178,12},{194,12}, {210,12},
         {0,25},   {16,25}, {32,25}, {48,25}, {64,25},{80,25},     {96,25}, // {112,25},   {128,25}, {144,25}, {160,25}, {178,25},{194,25}, {210,25},
         {0,38},   {16,38}, {32,38}, {48,38}, {64,38},{80,38},     {96,38}, // {112,38},   {128,38}, {144,38}, {160,38}, {178,38},{194,38}, {210,38},                           
         {0,51},   {16,51}, {32,51}, {48,51}, {64,51},{80,51},               //            {128,51}, {144,51}, {160,51}, {178,51},{194,51}, {210,51}, 
                            {32,63}, {48,63}, {64,63},              // {112,63},   {128,63}, {144,63}, {160,63}, {178,63},

                     {128,12}, {144,12}, {160,12}, {178,12},{194,12}, {210,12},
         {112,25},   {128,25}, {144,25}, {160,25}, {178,25},{194,25}, {210,25},
         {112,38},   {128,38}, {144,38}, {160,38}, {178,38},{194,38}, {210,38},
                     {128,51}, {144,51}, {160,51}, {178,51},{194,51}, {210,51},
                     {112,63}, {128,63}, {144,63}, 
     },

 {
      // LED Index to Flag
      4,4,4,4,4,4,\
      4,4,4,4,4,4,4,\
      4,4,4,4,4,4,4,\
      4,4,4,4,4,4,\
         4,4,4,\
        4,4,4,4,4,4,\
      4,4,4,4,4,4,4,\
      4,4,4,4,4,4,4,\
        4,4,4,4,4,4,\
     4,4,4,
    }
};



#endif


// PlumBL bootloader soft-entry: write magic 0xc220b134 to 0x2000fc00, reset.
// Spec from upstream https://github.com/HaiMianBBao/PlumBL (STM32F401 variant).
// Overrides the weak empty stub from platforms/chibios/bootloaders/custom.c.
void bootloader_jump(void) {
    *(volatile uint32_t *)0x2000FC00UL = 0xC220B134UL;
    NVIC_SystemReset();
}


// 2026-07-06 cold-boot USB self-heal. On true cold power-up the host sees
// D+ raised before the USB stack can answer control transfers; its
// enumeration attempts die with -71 errors and the port backs off/wedges
// (9-16s to a working keyboard at the LUKS prompt, or dead until physical
// replug behind some hubs). A device-side disconnect/reconnect once we are
// fully initialized is equivalent to that replug: measured 160ms to full
// enumeration against a live stack. Retry a few times for hosts whose USB
// comes up later than we do (early boot).
#include "usb_device_state.h"
#include "usb_main.h"
#include "split_util.h"

// 2026-07-11 (review finding): master-only. The slave half's USB is
// deliberately kept off (usb_disconnect() in is_keyboard_master_impl below);
// re-arming it here would let the host enumerate a mute half - the exact
// pre-saga symptom this file exists to prevent.
void housekeeping_task_kb(void) {
    static uint32_t next_check  = 1000; // first check ~1s after main loop starts
    static uint8_t  attempts    = 0;

    if (!is_keyboard_master()) return;
    if (attempts >= 3) return;
    if (timer_read32() < next_check) return;

    if (usb_device_state_get_configure_state() == USB_DEVICE_STATE_CONFIGURED) {
        attempts = 3; // enumerated - done forever
        return;
    }
    attempts++;
    next_check = timer_read32() + 3000;
    restart_usb_driver(&USB_DRIVER);
}


// 2026-07-06 asymmetric master detection (overrides QMK's weak
// is_keyboard_master_impl). ROOT CAUSE of the LUKS dead-keyboard saga: the
// FW16 powers the USB bay ~10s before the kernel brings USB up, so QMK's
// stock 2s SPLIT_USB_DETECT window always expired during POST silence and
// the cabled half declared itself SLAVE (enumerated, vial answered, but no
// matrix/RGB/keys; replug "fixed" it because a running host answers fast).
//   - LEFT half (the cable half at this desk): wait up to 60s for the host,
//     so cold boot survives POST and masters the moment initrd USB is up.
//   - RIGHT half: 3s check, then settle as slave quickly (a 60s wait here
//     kept the slave dark for the whole LUKS window).
// Tradeoff: cable into the RIGHT half only works when the host is already
// running (desk replug), not across a cold boot. That matches actual usage.
// 2026-07-11 (review finding): second cost - on a desk replug into the RIGHT
// half, the un-cabled LEFT half still burns its full 60s window dark before
// settling as slave (usb_connected_state() needs USB_ACTIVE, which never
// comes without a cable). Bench before shortening; see todo.md.
#include "usb_util.h"

bool is_keyboard_left_impl(void); // raw SPLIT_HAND_PIN read - safe pre-init

bool is_keyboard_master_impl(void) {
    const uint32_t timeout_ms = is_keyboard_left_impl() ? 60000 : 3000;
    bool is_master = false;
    for (uint32_t t = 0; t < timeout_ms; t += 10) {
        if (usb_connected_state()) {
            is_master = true;
            break;
        }
        wait_ms(10);
    }
    // mirror the stock impl: keep USB off on the slave half
    if (!is_master) {
        usb_disconnect();
    }
    return is_master;
}
