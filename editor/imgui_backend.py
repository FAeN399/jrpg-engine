"""
ImGui backend for Pygame + ModernGL.

Integrates Dear ImGui with our rendering pipeline using imgui-bundle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import ctypes

import pygame
import moderngl

# imgui-bundle provides imgui + backends
from imgui_bundle import imgui, immapp
from imgui_bundle.python_backends import compute_fb_scale

if TYPE_CHECKING:
    pass


class ImGuiRenderer:
    """
    ImGui renderer for ModernGL.

    Handles:
    - ImGui context initialization
    - Input event processing
    - Rendering ImGui draw data to ModernGL
    """

    VERTEX_SHADER = """
        #version 330 core

        uniform mat4 ProjMtx;
        in vec2 Position;
        in vec2 UV;
        in vec4 Color;
        out vec2 Frag_UV;
        out vec4 Frag_Color;

        void main() {
            Frag_UV = UV;
            Frag_Color = Color;
            gl_Position = ProjMtx * vec4(Position.xy, 0, 1);
        }
    """

    FRAGMENT_SHADER = """
        #version 330 core

        uniform sampler2D Texture;
        in vec2 Frag_UV;
        in vec4 Frag_Color;
        out vec4 Out_Color;

        void main() {
            Out_Color = Frag_Color * texture(Texture, Frag_UV.st);
        }
    """

    def __init__(self, ctx: moderngl.Context, display_size: tuple[int, int]):
        self.ctx = ctx
        self.display_size = display_size

        # Create ImGui context
        imgui.create_context()
        self.io = imgui.get_io()

        # Configure ImGui
        self.io.display_size = imgui.ImVec2(display_size[0], display_size[1])
        self.io.display_framebuffer_scale = imgui.ImVec2(1.0, 1.0)

        # Enable keyboard navigation
        self.io.config_flags |= imgui.ConfigFlags_.nav_enable_keyboard

        # Set up key mapping
        self._setup_key_map()

        # Create shader program
        self.program = ctx.program(
            vertex_shader=self.VERTEX_SHADER,
            fragment_shader=self.FRAGMENT_SHADER,
        )

        self.program['Texture'].value = 0

        # Create font texture
        self._create_font_texture()

        # Create buffers (will be resized as needed)
        self.vbo = ctx.buffer(reserve=65536)
        self.ibo = ctx.buffer(reserve=65536)

        # Create VAO
        self.vao = ctx.vertex_array(
            self.program,
            [
                (self.vbo, '2f 2f 4f1', 'Position', 'UV', 'Color'),
            ],
            index_buffer=self.ibo,
            index_element_size=4,  # 32-bit indices
        )

    def _setup_key_map(self) -> None:
        """Set up pygame key to imgui key mapping."""
        self._key_map = {
            pygame.K_TAB: imgui.Key.tab,
            pygame.K_LEFT: imgui.Key.left_arrow,
            pygame.K_RIGHT: imgui.Key.right_arrow,
            pygame.K_UP: imgui.Key.up_arrow,
            pygame.K_DOWN: imgui.Key.down_arrow,
            pygame.K_PAGEUP: imgui.Key.page_up,
            pygame.K_PAGEDOWN: imgui.Key.page_down,
            pygame.K_HOME: imgui.Key.home,
            pygame.K_END: imgui.Key.end,
            pygame.K_INSERT: imgui.Key.insert,
            pygame.K_DELETE: imgui.Key.delete,
            pygame.K_BACKSPACE: imgui.Key.backspace,
            pygame.K_SPACE: imgui.Key.space,
            pygame.K_RETURN: imgui.Key.enter,
            pygame.K_ESCAPE: imgui.Key.escape,
            pygame.K_a: imgui.Key.a,
            pygame.K_c: imgui.Key.c,
            pygame.K_v: imgui.Key.v,
            pygame.K_x: imgui.Key.x,
            pygame.K_y: imgui.Key.y,
            pygame.K_z: imgui.Key.z,
        }

    def _create_font_texture(self) -> None:
        """Create the font atlas texture."""
        # Get font atlas
        pixels, width, height, _ = self.io.fonts.get_tex_data_as_rgba32()

        # Create texture
        self.font_texture = self.ctx.texture((width, height), 4, bytes(pixels))
        self.font_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)

        # Set texture ID
        self.io.fonts.tex_id = self.font_texture.glo

    def process_event(self, event: pygame.event.Event) -> bool:
        """
        Process a pygame event for ImGui.

        Returns True if ImGui wants to capture this event.
        """
        io = self.io

        if event.type == pygame.MOUSEMOTION:
            io.add_mouse_pos_event(float(event.pos[0]), float(event.pos[1]))
            return io.want_capture_mouse

        elif event.type == pygame.MOUSEBUTTONDOWN:
            button = self._pygame_button_to_imgui(event.button)
            if button is not None:
                io.add_mouse_button_event(button, True)
            return io.want_capture_mouse

        elif event.type == pygame.MOUSEBUTTONUP:
            button = self._pygame_button_to_imgui(event.button)
            if button is not None:
                io.add_mouse_button_event(button, False)
            return io.want_capture_mouse

        elif event.type == pygame.MOUSEWHEEL:
            io.add_mouse_wheel_event(float(event.x), float(event.y))
            return io.want_capture_mouse

        elif event.type == pygame.KEYDOWN:
            key = self._key_map.get(event.key)
            if key is not None:
                io.add_key_event(key, True)

            # Modifiers
            io.add_key_event(imgui.Key.mod_ctrl, event.mod & pygame.KMOD_CTRL)
            io.add_key_event(imgui.Key.mod_shift, event.mod & pygame.KMOD_SHIFT)
            io.add_key_event(imgui.Key.mod_alt, event.mod & pygame.KMOD_ALT)

            return io.want_capture_keyboard

        elif event.type == pygame.KEYUP:
            key = self._key_map.get(event.key)
            if key is not None:
                io.add_key_event(key, False)
            return io.want_capture_keyboard

        elif event.type == pygame.TEXTINPUT:
            io.add_input_characters_utf8(event.text)
            return io.want_text_input

        return False

    def _pygame_button_to_imgui(self, button: int) -> int | None:
        """Convert pygame mouse button to imgui."""
        mapping = {
            1: imgui.MouseButton_.left,
            2: imgui.MouseButton_.middle,
            3: imgui.MouseButton_.right,
        }
        return mapping.get(button)

    def new_frame(self, dt: float) -> None:
        """Start a new ImGui frame."""
        self.io.delta_time = dt if dt > 0 else 1/60
        imgui.new_frame()

    def render(self) -> None:
        """Render ImGui draw data."""
        imgui.render()
        draw_data = imgui.get_draw_data()

        if draw_data is None:
            return

        # Get display info
        fb_width = int(draw_data.display_size.x * draw_data.framebuffer_scale.x)
        fb_height = int(draw_data.display_size.y * draw_data.framebuffer_scale.y)

        if fb_width <= 0 or fb_height <= 0:
            return

        # Setup render state
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.ctx.disable(moderngl.CULL_FACE)
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.SCISSOR_TEST)

        # Setup orthographic projection
        proj = self._create_ortho_matrix(draw_data)
        self.program['ProjMtx'].write(proj)

        # Render command lists
        for cmd_list in draw_data.cmd_lists:
            # Upload vertex/index data
            vtx_data = cmd_list.vtx_buffer.data()
            idx_data = cmd_list.idx_buffer.data()

            # Resize buffers if needed
            if len(vtx_data) > self.vbo.size:
                self.vbo.orphan(len(vtx_data) * 2)
            if len(idx_data) > self.ibo.size:
                self.ibo.orphan(len(idx_data) * 2)

            self.vbo.write(vtx_data)
            self.ibo.write(idx_data)

            # Execute draw commands
            idx_offset = 0
            for cmd in cmd_list.cmd_buffer:
                if cmd.user_callback:
                    # User callback (not implemented)
                    pass
                else:
                    # Clip rectangle
                    clip = cmd.clip_rect
                    x = int(clip.x)
                    y = int(fb_height - clip.w)
                    w = int(clip.z - clip.x)
                    h = int(clip.w - clip.y)

                    if w > 0 and h > 0:
                        self.ctx.scissor = (x, y, w, h)

                        # Bind texture
                        if cmd.texture_id:
                            # Find texture by OpenGL name
                            if cmd.texture_id == self.font_texture.glo:
                                self.font_texture.use(0)

                        # Draw
                        self.vao.render(
                            mode=moderngl.TRIANGLES,
                            vertices=cmd.elem_count,
                            first=idx_offset,
                        )

                idx_offset += cmd.elem_count

        # Restore state
        self.ctx.disable(moderngl.SCISSOR_TEST)
        self.ctx.scissor = None

    def _create_ortho_matrix(self, draw_data) -> bytes:
        """Create orthographic projection matrix."""
        import struct

        L = draw_data.display_pos.x
        R = draw_data.display_pos.x + draw_data.display_size.x
        T = draw_data.display_pos.y
        B = draw_data.display_pos.y + draw_data.display_size.y

        matrix = [
            2.0 / (R - L), 0.0, 0.0, 0.0,
            0.0, 2.0 / (T - B), 0.0, 0.0,
            0.0, 0.0, -1.0, 0.0,
            (R + L) / (L - R), (T + B) / (B - T), 0.0, 1.0,
        ]

        return struct.pack('16f', *matrix)

    def resize(self, width: int, height: int) -> None:
        """Handle window resize."""
        self.display_size = (width, height)
        self.io.display_size = imgui.ImVec2(width, height)

    def shutdown(self) -> None:
        """Clean up resources."""
        imgui.destroy_context()
