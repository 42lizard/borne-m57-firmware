#include "quantum.h"
#include "via.h"

// Private command, unused by VIA/Vial at the revision pinned in Dockerfile.
// Request: 40 01 <layer> followed by 29 zero bytes.
// Reply echoes the request, replacing byte 1 with status: 0 OK, 1 malformed,
// 2 invalid layer. VIA owns transmission of the response buffer.
void raw_hid_receive_kb(uint8_t *data, uint8_t length) {
    if (length == 0) {
        return;
    }
    if (data[0] != 0x40 || length < 2) {
        data[0] = id_unhandled;
        return;
    }
    if (length != 32 || data[1] != 1) {
        data[1] = 1;
        return;
    }
    for (uint8_t i = 3; i < length; i++) {
        if (data[i] != 0) {
            data[1] = 1;
            return;
        }
    }
    if (data[2] >= DYNAMIC_KEYMAP_LAYER_COUNT) {
        data[1] = 2;
        return;
    }
    layer_move(data[2]);
    data[1] = 0;
}
