#pragma once

// One solid color per highest active layer, including the default layer.
static bool borne_layer_colors(effect_params_t* params) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);
    static const uint8_t colors[10][3] = {
        {255, 255, 255}, // 0: white
        {255,   0,   0}, // 1: red
        {255,  80,   0}, // 2: orange
        {255, 255,   0}, // 3: yellow
        {  0, 255,   0}, // 4: green
        {  0, 255, 128}, // 5: mint
        {  0, 255, 255}, // 6: cyan
        {  0,   0, 255}, // 7: blue
        {128,   0, 255}, // 8: violet
        {255,   0, 128}, // 9: pink
    };
    uint8_t layer = get_highest_layer(layer_state | default_layer_state);
    if (layer >= 10) layer = 0;
    const uint8_t *color = colors[layer];
    uint8_t brightness = rgb_matrix_config.hsv.v;
    for (uint8_t i = led_min; i < led_max; i++) {
        rgb_matrix_set_color(i, scale8(color[0], brightness),
                               scale8(color[1], brightness),
                               scale8(color[2], brightness));
    }
    return rgb_matrix_check_finished_leds(led_max);
}
