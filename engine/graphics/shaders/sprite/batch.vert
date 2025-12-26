#version 330 core

in vec2 in_position;
in vec2 in_texcoord;
in vec4 in_color;

out vec2 v_texcoord;
out vec4 v_color;
out vec2 v_worldpos;

uniform mat4 u_projection;
uniform vec2 u_camera;

void main() {
    vec2 world_pos = in_position;
    v_worldpos = world_pos;

    // Apply camera offset
    vec2 view_pos = world_pos - u_camera;

    gl_Position = u_projection * vec4(view_pos, 0.0, 1.0);
    v_texcoord = in_texcoord;
    v_color = in_color;
}
