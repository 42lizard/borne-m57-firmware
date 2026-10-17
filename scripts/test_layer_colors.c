// Run: cc -std=c11 -Wall -Wextra -Werror scripts/test_layer_colors.c -o /tmp/test_layer_colors && /tmp/test_layer_colors
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

typedef struct { uint8_t min, max; } effect_params_t;
static uint32_t layer_state, default_layer_state;
static struct { struct { uint8_t v; } hsv; } rgb_matrix_config;
static uint8_t pixels[58][3];
#define RGB_MATRIX_USE_LIMITS(lo, hi) uint8_t lo = params->min, hi = params->max
static uint8_t get_highest_layer(uint32_t state) {
    uint8_t layer = 0;
    while (state >>= 1) layer++;
    return layer;
}
static uint8_t scale8(uint8_t value, uint8_t scale) {
    return (uint16_t)value * (scale + 1) >> 8;
}
static void rgb_matrix_set_color(uint8_t i, uint8_t r, uint8_t g, uint8_t b) {
    pixels[i][0] = r; pixels[i][1] = g; pixels[i][2] = b;
}
static bool rgb_matrix_check_finished_leds(uint8_t max) { return max < 58; }
#include "../source/m57/keymaps/via/borne_layer_colors.h"

int main(void) {
    uint8_t palette[10][3];
    effect_params_t left = {0, 29}, right = {29, 58};
    rgb_matrix_config.hsv.v = 255;
    default_layer_state = 1;
    for (uint8_t layer = 0; layer < 10; layer++) {
        layer_state = 1u << layer;
        memset(pixels, 0, sizeof pixels);
        assert(borne_layer_colors(&left));
        assert(pixels[29][0] == 0 && pixels[29][1] == 0 && pixels[29][2] == 0);
        assert(!borne_layer_colors(&right));
        memcpy(palette[layer], pixels[0], 3);
        for (uint8_t i = 0; i < 58; i++) assert(!memcmp(pixels[i], palette[layer], 3));
        for (uint8_t prev = 0; prev < layer; prev++) assert(memcmp(palette[prev], palette[layer], 3));
    }
    // Highest layer wins; releasing a momentary layer restores the default.
    default_layer_state = 1u << 2;
    layer_state = (1u << 1) | (1u << 7);
    borne_layer_colors(&left);
    assert(!memcmp(pixels[0], palette[7], 3));
    layer_state = 0;
    borne_layer_colors(&left);
    assert(!memcmp(pixels[0], palette[2], 3));
    rgb_matrix_config.hsv.v = 64;
    borne_layer_colors(&left);
    assert(pixels[0][0] == 64 && pixels[0][1] < 80);
    rgb_matrix_config.hsv.v = 0;
    borne_layer_colors(&left);
    assert(pixels[0][0] == 0 && pixels[0][1] == 0 && pixels[0][2] == 0);
    rgb_matrix_config.hsv.v = 255;
    layer_state = 1u << 15;
    borne_layer_colors(&left);
    assert(!memcmp(pixels[0], palette[0], 3));
}
