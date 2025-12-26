#version 330 core

in vec2 v_texcoord;
in vec4 v_color;
in vec2 v_worldpos;

out vec4 fragColor;

uniform sampler2D u_texture;

// Lighting uniforms (optional)
uniform bool u_lighting_enabled;
uniform vec3 u_ambient;
uniform int u_num_lights;
uniform vec3 u_light_positions[16];  // xy = position, z = radius
uniform vec4 u_light_colors[16];     // rgb = color, a = intensity

void main() {
    vec4 tex_color = texture(u_texture, v_texcoord);

    if (tex_color.a < 0.01) {
        discard;
    }

    vec4 color = tex_color * v_color;

    if (u_lighting_enabled && u_num_lights > 0) {
        vec3 light = u_ambient;

        for (int i = 0; i < u_num_lights && i < 16; i++) {
            vec2 light_pos = u_light_positions[i].xy;
            float radius = u_light_positions[i].z;
            vec3 light_color = u_light_colors[i].rgb;
            float intensity = u_light_colors[i].a;

            float dist = distance(v_worldpos, light_pos);
            float attenuation = 1.0 - smoothstep(0.0, radius, dist);
            attenuation = attenuation * attenuation;

            light += light_color * intensity * attenuation;
        }

        color.rgb *= light;
    }

    fragColor = color;
}
