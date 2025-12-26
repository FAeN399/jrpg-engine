#version 330 core

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform float u_threshold;

void main() {
    vec4 color = texture(u_texture, v_uv);
    float brightness = dot(color.rgb, vec3(0.2126, 0.7152, 0.0722));

    if (brightness > u_threshold) {
        fragColor = color;
    } else {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
    }
}
