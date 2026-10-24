#include <assert.h>
#include <stdint.h>
#include <string.h>

static unsigned moves;
static uint32_t layer_state = 1;
void layer_move(uint8_t layer) {
    moves++;
    layer_state = (uint32_t)1 << layer;
}
void raw_hid_receive_kb(uint8_t *data, uint8_t length);
#ifdef TEST_VIA_DISPATCH
void raw_hid_receive(uint8_t *data, uint8_t length);
extern unsigned sends, vial_calls;
static void receive(uint8_t *data, uint8_t length) {
    unsigned before = sends;
    raw_hid_receive(data, length);
    assert(sends == before + 1);
}
#else
#define receive raw_hid_receive_kb
#endif

static void rejected(uint8_t *data, uint8_t length, uint8_t status) {
    uint32_t before = layer_state;
    unsigned calls = moves;
    if (length == 32) {
        receive(data, length);
    } else {
        // Upstream USB transport supplies only full reports to its dispatcher.
        raw_hid_receive_kb(data, length);
    }
    assert(layer_state == before && moves == calls);
    if (length >= 2) {
        assert(data[1] == status);
    }
}

int main(void) {
    for (uint8_t layer = 0; layer < 10; layer++) {
        uint8_t data[32] = {0x40, 1, layer};
        unsigned before = moves;
        receive(data, sizeof data);
        assert(moves == before + 1);
        assert(layer_state == ((uint32_t)1 << layer));
        assert(data[0] == 0x40 && data[1] == 0 && data[2] == layer);
    }
    for (unsigned layer = 10; layer <= 255; layer++) {
        uint8_t data[32] = {0x40, 1, layer};
        rejected(data, sizeof data, 2);
    }
    for (unsigned length = 0; length <= 255; length++) {
        if (length == 32) continue;
        uint8_t data[255] = {0x40, 1, 3};
        rejected(data, length, 1);
        if (length == 1) assert(data[0] == 0xFF);
    }
    for (unsigned version = 0; version <= 255; version++) {
        if (version == 1) continue;
        uint8_t data[32] = {0x40, version, 3};
        rejected(data, sizeof data, 1);
    }
    for (unsigned offset = 3; offset < 32; offset++) {
        uint8_t data[32] = {0x40, 1, 3};
        data[offset] = 1;
        rejected(data, sizeof data, 1);
    }
    uint8_t unknown[32] = {0x41, 1, 3};
    uint32_t before = layer_state;
    receive(unknown, sizeof unknown);
    assert(unknown[0] == 0xFF && layer_state == before);
#ifdef TEST_VIA_DISPATCH
    uint8_t protocol[32] = {0x01};
    receive(protocol, sizeof protocol);
    assert(protocol[0] == 0x01 && protocol[1] == 0 && protocol[2] == 9);
    uint8_t vial[32] = {0xFE};
    receive(vial, sizeof vial);
    assert(vial_calls == 1 && vial[1] == 0xA5);
    uint8_t unsupported_value[32] = {0x02, 0xF0};
    receive(unsupported_value, sizeof unsupported_value);
    assert(unsupported_value[0] == 0xFF && layer_state == before);
#endif
}
