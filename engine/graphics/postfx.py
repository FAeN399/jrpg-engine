"""
Post-processing effects chain.

Applies screen-space effects like bloom, vignette, color grading,
and screen transitions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING
import struct

import moderngl
import numpy as np


# Fullscreen quad vertex shader (shared by all effects)
FULLSCREEN_VERTEX = """
#version 330 core

in vec2 in_pos;
in vec2 in_uv;

out vec2 v_uv;

void main() {
    gl_Position = vec4(in_pos, 0.0, 1.0);
    v_uv = in_uv;
}
"""

# Bloom effect shaders
BLOOM_BRIGHT_PASS = """
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
"""

BLOOM_BLUR = """
#version 330 core

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform vec2 u_direction;
uniform vec2 u_resolution;

const float weights[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);

void main() {
    vec2 texel = 1.0 / u_resolution;
    vec3 result = texture(u_texture, v_uv).rgb * weights[0];

    for (int i = 1; i < 5; i++) {
        vec2 offset = u_direction * texel * float(i) * 2.0;
        result += texture(u_texture, v_uv + offset).rgb * weights[i];
        result += texture(u_texture, v_uv - offset).rgb * weights[i];
    }

    fragColor = vec4(result, 1.0);
}
"""

BLOOM_COMBINE = """
#version 330 core

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_scene;
uniform sampler2D u_bloom;
uniform float u_intensity;

void main() {
    vec3 scene = texture(u_scene, v_uv).rgb;
    vec3 bloom = texture(u_bloom, v_uv).rgb;

    fragColor = vec4(scene + bloom * u_intensity, 1.0);
}
"""

# Vignette shader
VIGNETTE_FRAGMENT = """
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
"""

# Color grading shader
COLOR_GRADE_FRAGMENT = """
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
"""

# Screen transition shaders
FADE_FRAGMENT = """
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
"""


class PostEffect(ABC):
    """Base class for post-processing effects."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.enabled = True

    @abstractmethod
    def apply(
        self,
        source: moderngl.Texture,
        dest: moderngl.Framebuffer,
    ) -> None:
        """Apply the effect."""
        pass


class PostProcessingChain:
    """
    Chain of post-processing effects.

    Applies effects in sequence using ping-pong buffers.
    """

    def __init__(self, ctx: moderngl.Context, width: int, height: int):
        self.ctx = ctx
        self.width = width
        self.height = height

        # Ping-pong framebuffers
        self._fbo_a, self._tex_a = self._create_fbo(width, height)
        self._fbo_b, self._tex_b = self._create_fbo(width, height)

        # Fullscreen quad
        self._quad_vbo = self._create_quad_vbo()

        # Effects chain
        self.effects: list[PostEffect] = []

        # Built-in effects
        self.bloom: BloomEffect | None = None
        self.vignette: VignetteEffect | None = None
        self.color_grade: ColorGradeEffect | None = None
        self.fade: FadeEffect | None = None

    def _create_fbo(
        self,
        width: int,
        height: int,
    ) -> tuple[moderngl.Framebuffer, moderngl.Texture]:
        """Create a framebuffer with color texture."""
        texture = self.ctx.texture((width, height), 4)
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        fbo = self.ctx.framebuffer(color_attachments=[texture])
        return fbo, texture

    def _create_quad_vbo(self) -> moderngl.Buffer:
        """Create fullscreen quad vertex buffer."""
        vertices = struct.pack('24f',
            -1, -1, 0, 0,
             1, -1, 1, 0,
             1,  1, 1, 1,
            -1, -1, 0, 0,
             1,  1, 1, 1,
            -1,  1, 0, 1,
        )
        return self.ctx.buffer(vertices)

    def resize(self, width: int, height: int) -> None:
        """Resize internal buffers."""
        if width == self.width and height == self.height:
            return

        self.width = width
        self.height = height

        # Recreate framebuffers
        self._fbo_a.release()
        self._tex_a.release()
        self._fbo_b.release()
        self._tex_b.release()

        self._fbo_a, self._tex_a = self._create_fbo(width, height)
        self._fbo_b, self._tex_b = self._create_fbo(width, height)

    def enable_bloom(
        self,
        threshold: float = 0.8,
        intensity: float = 0.5,
        blur_passes: int = 3,
    ) -> BloomEffect:
        """Enable bloom effect."""
        self.bloom = BloomEffect(
            self.ctx,
            self.width,
            self.height,
            threshold,
            intensity,
            blur_passes,
        )
        return self.bloom

    def enable_vignette(
        self,
        intensity: float = 1.5,
        radius: float = 0.5,
    ) -> VignetteEffect:
        """Enable vignette effect."""
        self.vignette = VignetteEffect(self.ctx, intensity, radius)
        return self.vignette

    def enable_color_grade(
        self,
        brightness: float = 0.0,
        contrast: float = 1.0,
        saturation: float = 1.0,
        tint: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> ColorGradeEffect:
        """Enable color grading."""
        self.color_grade = ColorGradeEffect(
            self.ctx, brightness, contrast, saturation, tint
        )
        return self.color_grade

    def enable_fade(self) -> FadeEffect:
        """Enable screen fade effect."""
        self.fade = FadeEffect(self.ctx)
        return self.fade

    def process(
        self,
        source: moderngl.Texture,
        dest: moderngl.Framebuffer,
    ) -> None:
        """
        Apply all effects in chain.

        Args:
            source: Input texture (scene render)
            dest: Output framebuffer (usually screen)
        """
        # Collect active effects
        active_effects: list[PostEffect] = []

        if self.bloom and self.bloom.enabled:
            active_effects.append(self.bloom)
        if self.vignette and self.vignette.enabled:
            active_effects.append(self.vignette)
        if self.color_grade and self.color_grade.enabled:
            active_effects.append(self.color_grade)
        if self.fade and self.fade.enabled:
            active_effects.append(self.fade)

        active_effects.extend(e for e in self.effects if e.enabled)

        if not active_effects:
            # No effects - just copy to dest
            self._blit(source, dest)
            return

        # Ping-pong processing
        current_tex = source
        use_a = True

        for i, effect in enumerate(active_effects):
            is_last = (i == len(active_effects) - 1)

            if is_last:
                # Last effect outputs to dest
                effect.apply(current_tex, dest)
            else:
                # Output to ping-pong buffer
                target_fbo = self._fbo_a if use_a else self._fbo_b
                effect.apply(current_tex, target_fbo)
                current_tex = self._tex_a if use_a else self._tex_b
                use_a = not use_a

    def _blit(
        self,
        source: moderngl.Texture,
        dest: moderngl.Framebuffer,
    ) -> None:
        """Copy texture to framebuffer."""
        # Simple pass-through would need a blit shader
        # For now, just use the context's copy
        pass  # TODO: Implement blit


class BloomEffect(PostEffect):
    """
    Bloom (glow) effect.

    Extracts bright pixels, blurs them, and adds back to scene.
    """

    def __init__(
        self,
        ctx: moderngl.Context,
        width: int,
        height: int,
        threshold: float = 0.8,
        intensity: float = 0.5,
        blur_passes: int = 3,
    ):
        super().__init__(ctx)

        self.threshold = threshold
        self.intensity = intensity
        self.blur_passes = blur_passes

        # Half-resolution for blur (performance)
        blur_width = width // 2
        blur_height = height // 2

        # Framebuffers
        self._bright_fbo, self._bright_tex = self._create_fbo(blur_width, blur_height)
        self._blur_a_fbo, self._blur_a_tex = self._create_fbo(blur_width, blur_height)
        self._blur_b_fbo, self._blur_b_tex = self._create_fbo(blur_width, blur_height)

        # Shaders
        self._bright_prog = ctx.program(
            vertex_shader=FULLSCREEN_VERTEX,
            fragment_shader=BLOOM_BRIGHT_PASS,
        )
        self._blur_prog = ctx.program(
            vertex_shader=FULLSCREEN_VERTEX,
            fragment_shader=BLOOM_BLUR,
        )
        self._combine_prog = ctx.program(
            vertex_shader=FULLSCREEN_VERTEX,
            fragment_shader=BLOOM_COMBINE,
        )

        # Quad
        self._quad = self._create_quad()
        self._blur_width = blur_width
        self._blur_height = blur_height

    def _create_fbo(self, w: int, h: int):
        tex = self.ctx.texture((w, h), 4)
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        fbo = self.ctx.framebuffer(color_attachments=[tex])
        return fbo, tex

    def _create_quad(self):
        vertices = struct.pack('24f',
            -1, -1, 0, 0,
             1, -1, 1, 0,
             1,  1, 1, 1,
            -1, -1, 0, 0,
             1,  1, 1, 1,
            -1,  1, 0, 1,
        )
        vbo = self.ctx.buffer(vertices)
        return {
            'bright': self.ctx.vertex_array(
                self._bright_prog, [(vbo, '2f 2f', 'in_pos', 'in_uv')]
            ),
            'blur': self.ctx.vertex_array(
                self._blur_prog, [(vbo, '2f 2f', 'in_pos', 'in_uv')]
            ),
            'combine': self.ctx.vertex_array(
                self._combine_prog, [(vbo, '2f 2f', 'in_pos', 'in_uv')]
            ),
        }

    def apply(
        self,
        source: moderngl.Texture,
        dest: moderngl.Framebuffer,
    ) -> None:
        # 1. Extract bright pixels
        self._bright_fbo.use()
        source.use(0)
        self._bright_prog['u_texture'].value = 0
        self._bright_prog['u_threshold'].value = self.threshold
        self._quad['bright'].render()

        # 2. Blur passes
        current = self._bright_tex
        for i in range(self.blur_passes):
            # Horizontal
            self._blur_a_fbo.use()
            current.use(0)
            self._blur_prog['u_texture'].value = 0
            self._blur_prog['u_direction'].value = (1.0, 0.0)
            self._blur_prog['u_resolution'].value = (self._blur_width, self._blur_height)
            self._quad['blur'].render()

            # Vertical
            self._blur_b_fbo.use()
            self._blur_a_tex.use(0)
            self._blur_prog['u_direction'].value = (0.0, 1.0)
            self._quad['blur'].render()

            current = self._blur_b_tex

        # 3. Combine
        dest.use()
        source.use(0)
        self._blur_b_tex.use(1)
        self._combine_prog['u_scene'].value = 0
        self._combine_prog['u_bloom'].value = 1
        self._combine_prog['u_intensity'].value = self.intensity
        self._quad['combine'].render()


class VignetteEffect(PostEffect):
    """Darkens screen edges."""

    def __init__(
        self,
        ctx: moderngl.Context,
        intensity: float = 1.5,
        radius: float = 0.5,
    ):
        super().__init__(ctx)
        self.intensity = intensity
        self.radius = radius

        self._prog = ctx.program(
            vertex_shader=FULLSCREEN_VERTEX,
            fragment_shader=VIGNETTE_FRAGMENT,
        )
        self._quad = self._create_quad()

    def _create_quad(self):
        vertices = struct.pack('24f',
            -1, -1, 0, 0, 1, -1, 1, 0, 1, 1, 1, 1,
            -1, -1, 0, 0, 1, 1, 1, 1, -1, 1, 0, 1,
        )
        vbo = self.ctx.buffer(vertices)
        return self.ctx.vertex_array(self._prog, [(vbo, '2f 2f', 'in_pos', 'in_uv')])

    def apply(self, source: moderngl.Texture, dest: moderngl.Framebuffer) -> None:
        dest.use()
        source.use(0)
        self._prog['u_texture'].value = 0
        self._prog['u_intensity'].value = self.intensity
        self._prog['u_radius'].value = self.radius
        self._quad.render()


class ColorGradeEffect(PostEffect):
    """Color grading (brightness, contrast, saturation, tint)."""

    def __init__(
        self,
        ctx: moderngl.Context,
        brightness: float = 0.0,
        contrast: float = 1.0,
        saturation: float = 1.0,
        tint: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ):
        super().__init__(ctx)
        self.brightness = brightness
        self.contrast = contrast
        self.saturation = saturation
        self.tint = tint

        self._prog = ctx.program(
            vertex_shader=FULLSCREEN_VERTEX,
            fragment_shader=COLOR_GRADE_FRAGMENT,
        )
        self._quad = self._create_quad()

    def _create_quad(self):
        vertices = struct.pack('24f',
            -1, -1, 0, 0, 1, -1, 1, 0, 1, 1, 1, 1,
            -1, -1, 0, 0, 1, 1, 1, 1, -1, 1, 0, 1,
        )
        vbo = self.ctx.buffer(vertices)
        return self.ctx.vertex_array(self._prog, [(vbo, '2f 2f', 'in_pos', 'in_uv')])

    def apply(self, source: moderngl.Texture, dest: moderngl.Framebuffer) -> None:
        dest.use()
        source.use(0)
        self._prog['u_texture'].value = 0
        self._prog['u_brightness'].value = self.brightness
        self._prog['u_contrast'].value = self.contrast
        self._prog['u_saturation'].value = self.saturation
        self._prog['u_tint'].value = self.tint
        self._quad.render()


class FadeEffect(PostEffect):
    """Screen fade for transitions."""

    def __init__(self, ctx: moderngl.Context):
        super().__init__(ctx)
        self.progress = 0.0  # 0 = no fade, 1 = fully faded
        self.color = (0.0, 0.0, 0.0)

        self._prog = ctx.program(
            vertex_shader=FULLSCREEN_VERTEX,
            fragment_shader=FADE_FRAGMENT,
        )
        self._quad = self._create_quad()

    def _create_quad(self):
        vertices = struct.pack('24f',
            -1, -1, 0, 0, 1, -1, 1, 0, 1, 1, 1, 1,
            -1, -1, 0, 0, 1, 1, 1, 1, -1, 1, 0, 1,
        )
        vbo = self.ctx.buffer(vertices)
        return self.ctx.vertex_array(self._prog, [(vbo, '2f 2f', 'in_pos', 'in_uv')])

    def fade_in(self, duration: float, dt: float) -> bool:
        """Fade from black to scene. Returns True when complete."""
        self.progress = max(0, self.progress - dt / duration)
        return self.progress <= 0

    def fade_out(self, duration: float, dt: float) -> bool:
        """Fade from scene to black. Returns True when complete."""
        self.progress = min(1, self.progress + dt / duration)
        return self.progress >= 1

    def apply(self, source: moderngl.Texture, dest: moderngl.Framebuffer) -> None:
        dest.use()
        source.use(0)
        self._prog['u_texture'].value = 0
        self._prog['u_progress'].value = self.progress
        self._prog['u_color'].value = self.color
        self._quad.render()
