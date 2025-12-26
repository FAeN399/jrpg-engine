"""
ModernGL context management.

Handles OpenGL context setup and provides utilities for
creating shaders, textures, and framebuffers.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import moderngl

if TYPE_CHECKING:
    import pygame


class GraphicsContext:
    """
    Wrapper around ModernGL context with utilities.

    Provides:
    - Shader compilation with error handling
    - Shader file loading
    - Common uniform management
    - Framebuffer helpers
    """

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self._shader_cache: dict[str, moderngl.Program] = {}
        self._shader_path = Path("engine/graphics/shaders")

    @property
    def screen(self) -> moderngl.Framebuffer:
        """Get the default framebuffer (screen)."""
        return self.ctx.screen

    def create_program(
        self,
        vertex_shader: str,
        fragment_shader: str,
        geometry_shader: str | None = None,
    ) -> moderngl.Program:
        """
        Create a shader program from source strings.

        Args:
            vertex_shader: Vertex shader GLSL source
            fragment_shader: Fragment shader GLSL source
            geometry_shader: Optional geometry shader source

        Returns:
            Compiled shader program
        """
        return self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader,
            geometry_shader=geometry_shader,
        )

    def load_program(
        self,
        name: str,
        vertex_file: str | None = None,
        fragment_file: str | None = None,
        geometry_file: str | None = None,
    ) -> moderngl.Program:
        """
        Load shader program from files.

        Args:
            name: Cache key for the program
            vertex_file: Path to vertex shader (default: {name}.vert)
            fragment_file: Path to fragment shader (default: {name}.frag)
            geometry_file: Optional geometry shader path

        Returns:
            Compiled shader program
        """
        if name in self._shader_cache:
            return self._shader_cache[name]

        # Default file names
        if vertex_file is None:
            vertex_file = f"{name}.vert"
        if fragment_file is None:
            fragment_file = f"{name}.frag"

        # Load shader sources
        vertex_src = self._load_shader_file(vertex_file)
        fragment_src = self._load_shader_file(fragment_file)

        geometry_src = None
        if geometry_file:
            geometry_src = self._load_shader_file(geometry_file)

        program = self.create_program(vertex_src, fragment_src, geometry_src)
        self._shader_cache[name] = program
        return program

    def _load_shader_file(self, filename: str) -> str:
        """Load shader source from file."""
        path = self._shader_path / filename
        if not path.exists():
            raise FileNotFoundError(f"Shader not found: {path}")
        return path.read_text()

    def create_texture(
        self,
        size: tuple[int, int],
        components: int = 4,
        data: bytes | None = None,
        filter: tuple[int, int] = (moderngl.NEAREST, moderngl.NEAREST),
    ) -> moderngl.Texture:
        """
        Create a texture.

        Args:
            size: (width, height)
            components: Number of components (1-4)
            data: Optional initial data
            filter: (min_filter, mag_filter)

        Returns:
            New texture
        """
        texture = self.ctx.texture(size, components, data)
        texture.filter = filter
        return texture

    def create_framebuffer(
        self,
        size: tuple[int, int],
        components: int = 4,
    ) -> tuple[moderngl.Framebuffer, moderngl.Texture]:
        """
        Create a framebuffer with color attachment.

        Args:
            size: (width, height)
            components: Number of color components

        Returns:
            (framebuffer, color_texture)
        """
        texture = self.create_texture(size, components)
        fbo = self.ctx.framebuffer(color_attachments=[texture])
        return fbo, texture

    def create_buffer(self, data: bytes, dynamic: bool = False) -> moderngl.Buffer:
        """
        Create a vertex/index buffer.

        Args:
            data: Buffer data
            dynamic: If True, buffer will be updated frequently

        Returns:
            New buffer
        """
        return self.ctx.buffer(data, dynamic=dynamic)

    def clear(
        self,
        r: float = 0.0,
        g: float = 0.0,
        b: float = 0.0,
        a: float = 1.0,
    ) -> None:
        """Clear the current framebuffer."""
        self.ctx.clear(r, g, b, a)


# Common vertex formats
VERTEX_FORMAT_2D = "2f"  # position only
VERTEX_FORMAT_2D_UV = "2f 2f"  # position + texcoord
VERTEX_FORMAT_2D_UV_COLOR = "2f 2f 4f"  # position + texcoord + color


def create_fullscreen_quad(ctx: moderngl.Context, program: moderngl.Program) -> moderngl.VertexArray:
    """
    Create a fullscreen quad for post-processing.

    Returns a VAO that renders a quad covering the entire screen.
    """
    import struct

    vertices = struct.pack('24f',
        # pos      uv
        -1, -1,    0, 0,
         1, -1,    1, 0,
         1,  1,    1, 1,
        -1, -1,    0, 0,
         1,  1,    1, 1,
        -1,  1,    0, 1,
    )

    vbo = ctx.buffer(vertices)
    vao = ctx.vertex_array(program, [(vbo, '2f 2f', 'in_pos', 'in_uv')])
    return vao
