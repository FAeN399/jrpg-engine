#version 330 core

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform float u_intensity;
uniform float u_radius;

void main() {
    vec4 color = texture(u_texture, v_uv);

    vec2 center = v_uv - 0.5;
    float dist = length(center);
    float vignette = 1.0 - smoothstep(u_radius, u_radius + 0.5, dist * u_intensity);

    fragColor = vec4(color.rgb * vignette, color.a);
}
