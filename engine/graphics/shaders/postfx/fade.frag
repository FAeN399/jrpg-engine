#version 330 core

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform float u_progress;
uniform vec3 u_color;

void main() {
    vec4 scene = texture(u_texture, v_uv);
    fragColor = mix(scene, vec4(u_color, 1.0), u_progress);
}
