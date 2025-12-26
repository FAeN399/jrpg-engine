#version 330 core

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform float u_brightness;
uniform float u_contrast;
uniform float u_saturation;
uniform vec3 u_tint;

void main() {
    vec4 color = texture(u_texture, v_uv);

    // Brightness
    vec3 result = color.rgb + u_brightness;

    // Contrast
    result = (result - 0.5) * u_contrast + 0.5;

    // Saturation
    float gray = dot(result, vec3(0.299, 0.587, 0.114));
    result = mix(vec3(gray), result, u_saturation);

    // Tint
    result *= u_tint;

    fragColor = vec4(clamp(result, 0.0, 1.0), color.a);
}
