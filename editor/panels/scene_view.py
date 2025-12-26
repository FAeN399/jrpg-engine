"""
Scene View panel - displays the game world for editing.

This is the main viewport where the user interacts with
the game world, placing tiles, entities, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import struct

import pygame
import moderngl
import numpy as np
from imgui_bundle import imgui

from editor.panels.base import Panel

if TYPE_CHECKING:
    from engine.core import Game
    from editor.app import EditorState


class SceneViewPanel(Panel):
    """
    Main scene view for world editing.

    Displays the tilemap and entities, allowing the user
    to paint tiles, place entities, and navigate the world.
    """

    @property
    def title(self) -> str:
        return "Scene"

    def __init__(self, game: Game, state: EditorState):
        super().__init__(game, state)

        # Viewport state
        self._viewport_pos = (0, 0)
        self._viewport_size = (800, 600)
        self._camera_x = 0.0
        self._camera_y = 0.0
        self._zoom = 1.0

        # Mouse state
        self._is_panning = False
        self._last_mouse_pos = (0, 0)
        self._last_paint_tile: tuple[int, int] | None = None

        # Render target
        self._fbo: moderngl.Framebuffer | None = None
        self._fbo_texture: moderngl.Texture | None = None
        self._needs_resize = True

        # Grid rendering resources
        self._grid_program: moderngl.Program | None = None
        self._grid_vbo: moderngl.Buffer | None = None
        self._grid_vao: moderngl.VertexArray | None = None
        self._init_grid_shader()

    def update(self, dt: float) -> None:
        pass

    def _init_grid_shader(self) -> None:
        """Initialize the grid rendering shader."""
        ctx = self.game.ctx

        vertex_shader = """
        #version 330 core
        in vec2 in_position;
        uniform mat4 u_projection;
        uniform vec2 u_camera;
        uniform float u_zoom;

        void main() {
            vec2 pos = (in_position - u_camera) * u_zoom;
            gl_Position = u_projection * vec4(pos, 0.0, 1.0);
        }
        """

        fragment_shader = """
        #version 330 core
        out vec4 fragColor;
        uniform vec4 u_color;

        void main() {
            fragColor = u_color;
        }
        """

        self._grid_program = ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader,
        )

    def _get_window_flags(self) -> int:
        return imgui.WindowFlags_.no_scrollbar | imgui.WindowFlags_.no_scroll_with_mouse

    def _render_content(self) -> None:
        # Get content region size
        content_size = imgui.get_content_region_avail()
        width = int(content_size.x)
        height = int(content_size.y)

        if width <= 0 or height <= 0:
            return

        # Check if we need to resize the framebuffer
        if (self._fbo is None or
            self._viewport_size != (width, height)):
            self._resize_viewport(width, height)

        # Render scene to framebuffer
        self._render_scene()

        # Display the texture in ImGui
        if self._fbo_texture:
            # Get cursor position for mouse handling
            cursor_pos = imgui.get_cursor_screen_pos()
            self._viewport_pos = (cursor_pos.x, cursor_pos.y)

            # Display texture as image
            imgui.image(
                self._fbo_texture.glo,
                imgui.ImVec2(width, height),
                imgui.ImVec2(0, 1),  # UV0 (flipped)
                imgui.ImVec2(1, 0),  # UV1
            )

            # Handle input if the image is hovered
            if imgui.is_item_hovered():
                self._handle_input()

        # Overlay controls
        self._render_overlay()

    def _resize_viewport(self, width: int, height: int) -> None:
        """Resize the render target."""
        ctx = self.game.ctx

        # Release old resources
        if self._fbo:
            self._fbo.release()
        if self._fbo_texture:
            self._fbo_texture.release()

        # Create new framebuffer
        self._fbo_texture = ctx.texture((width, height), 4)
        self._fbo_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self._fbo = ctx.framebuffer(color_attachments=[self._fbo_texture])

        self._viewport_size = (width, height)
        self._needs_resize = False

    def _render_scene(self) -> None:
        """Render the game world to the framebuffer."""
        if not self._fbo:
            return

        self._fbo.use()
        self.game.ctx.clear(0.2, 0.2, 0.25, 1.0)

        # Render tilemap layers
        self._render_tilemap()

        # Render grid if enabled
        if self.state.show_grid:
            self._render_grid()

        # Render tile selection highlight
        self._render_selection()

        # Restore default framebuffer
        self.game.ctx.screen.use()

    def _render_tilemap(self) -> None:
        """Render the tilemap layers."""
        tilemap = self.state.current_tilemap
        if not tilemap:
            return

        ctx = self.game.ctx
        width, height = self._viewport_size
        tile_size = self.state.grid_size

        # Simple tile rendering using immediate mode rectangles
        # For each visible layer, draw filled rectangles for tiles
        for layer in tilemap.layers:
            if not layer.visible:
                continue

            # Calculate visible tile range
            start_x = max(0, int(self._camera_x / tile_size) - 1)
            start_y = max(0, int(self._camera_y / tile_size) - 1)
            end_x = min(layer.width, int((self._camera_x + width / self._zoom) / tile_size) + 2)
            end_y = min(layer.height, int((self._camera_y + height / self._zoom) / tile_size) + 2)

            # Build geometry for visible tiles
            vertices = []
            for ty in range(start_y, end_y):
                for tx in range(start_x, end_x):
                    tile_id = layer.get_tile(tx, ty)
                    if tile_id < 0:
                        continue

                    # World position
                    px = tx * tile_size
                    py = ty * tile_size

                    # Convert to screen coordinates
                    sx = (px - self._camera_x) * self._zoom
                    sy = (py - self._camera_y) * self._zoom
                    sw = tile_size * self._zoom
                    sh = tile_size * self._zoom

                    # Generate color based on tile_id for visualization
                    r = ((tile_id * 37) % 128 + 64) / 255.0
                    g = ((tile_id * 73) % 128 + 64) / 255.0
                    b = ((tile_id * 97) % 128 + 64) / 255.0

                    # Two triangles per tile (6 vertices)
                    for vx, vy in [(sx, sy), (sx + sw, sy), (sx + sw, sy + sh),
                                   (sx, sy), (sx + sw, sy + sh), (sx, sy + sh)]:
                        vertices.extend([vx, vy, r, g, b, layer.opacity])

            if not vertices:
                continue

            # Create simple colored tile shader if needed
            self._render_tile_batch(vertices)

    def _render_tile_batch(self, vertices: list[float]) -> None:
        """Render a batch of colored tiles."""
        if not vertices:
            return

        ctx = self.game.ctx
        width, height = self._viewport_size

        # Simple colored rect shader
        if not hasattr(self, '_tile_program'):
            self._tile_program = ctx.program(
                vertex_shader="""
                #version 330 core
                in vec2 in_position;
                in vec4 in_color;
                out vec4 v_color;
                uniform mat4 u_projection;

                void main() {
                    gl_Position = u_projection * vec4(in_position, 0.0, 1.0);
                    v_color = in_color;
                }
                """,
                fragment_shader="""
                #version 330 core
                in vec4 v_color;
                out vec4 fragColor;

                void main() {
                    fragColor = v_color;
                }
                """
            )

        # Create orthographic projection
        proj = np.array([
            [2.0 / width, 0, 0, -1],
            [0, -2.0 / height, 0, 1],
            [0, 0, -1, 0],
            [0, 0, 0, 1],
        ], dtype='f4')

        self._tile_program['u_projection'].write(proj.tobytes())

        # Create buffer and VAO
        data = struct.pack(f'{len(vertices)}f', *vertices)
        vbo = ctx.buffer(data)
        vao = ctx.vertex_array(
            self._tile_program,
            [(vbo, '2f 4f', 'in_position', 'in_color')],
        )

        vao.render()
        vbo.release()
        vao.release()

    def _render_grid(self) -> None:
        """Render the editor grid."""
        if not self._grid_program:
            return

        ctx = self.game.ctx
        width, height = self._viewport_size
        tile_size = self.state.grid_size

        # Calculate visible grid range
        start_x = int(self._camera_x / tile_size) * tile_size
        start_y = int(self._camera_y / tile_size) * tile_size
        end_x = int((self._camera_x + width / self._zoom) / tile_size + 2) * tile_size
        end_y = int((self._camera_y + height / self._zoom) / tile_size + 2) * tile_size

        # Build grid lines
        vertices = []

        # Vertical lines
        for x in range(start_x, end_x + 1, tile_size):
            sx = (x - self._camera_x) * self._zoom
            vertices.extend([sx, 0, sx, height])

        # Horizontal lines
        for y in range(start_y, end_y + 1, tile_size):
            sy = (y - self._camera_y) * self._zoom
            vertices.extend([0, sy, width, sy])

        if not vertices:
            return

        # Create orthographic projection
        proj = np.array([
            [2.0 / width, 0, 0, -1],
            [0, -2.0 / height, 0, 1],
            [0, 0, -1, 0],
            [0, 0, 0, 1],
        ], dtype='f4')

        self._grid_program['u_projection'].write(proj.tobytes())
        self._grid_program['u_camera'].value = (0, 0)  # Already applied
        self._grid_program['u_zoom'].value = 1.0
        self._grid_program['u_color'].value = (0.4, 0.4, 0.4, 0.5)

        # Create buffer and draw
        data = struct.pack(f'{len(vertices)}f', *vertices)

        if self._grid_vbo:
            self._grid_vbo.release()
        if self._grid_vao:
            self._grid_vao.release()

        self._grid_vbo = ctx.buffer(data)
        self._grid_vao = ctx.vertex_array(
            self._grid_program,
            [(self._grid_vbo, '2f', 'in_position')],
        )

        self._grid_vao.render(moderngl.LINES)

    def _render_selection(self) -> None:
        """Render the current tile selection highlight."""
        if not self.state.selected_tile:
            return

        tile_x, tile_y = self.state.selected_tile
        tile_size = self.state.grid_size

        # Calculate screen position
        sx = (tile_x * tile_size - self._camera_x) * self._zoom
        sy = (tile_y * tile_size - self._camera_y) * self._zoom
        sw = tile_size * self._zoom
        sh = tile_size * self._zoom

        # Draw selection rectangle using the grid shader
        if not self._grid_program:
            return

        ctx = self.game.ctx
        width, height = self._viewport_size

        # Rectangle outline (4 lines)
        vertices = [
            sx, sy, sx + sw, sy,      # Top
            sx + sw, sy, sx + sw, sy + sh,  # Right
            sx + sw, sy + sh, sx, sy + sh,  # Bottom
            sx, sy + sh, sx, sy,      # Left
        ]

        proj = np.array([
            [2.0 / width, 0, 0, -1],
            [0, -2.0 / height, 0, 1],
            [0, 0, -1, 0],
            [0, 0, 0, 1],
        ], dtype='f4')

        self._grid_program['u_projection'].write(proj.tobytes())
        self._grid_program['u_camera'].value = (0, 0)
        self._grid_program['u_zoom'].value = 1.0
        self._grid_program['u_color'].value = (1.0, 1.0, 0.0, 1.0)  # Yellow

        data = struct.pack(f'{len(vertices)}f', *vertices)
        vbo = ctx.buffer(data)
        vao = ctx.vertex_array(self._grid_program, [(vbo, '2f', 'in_position')])
        vao.render(moderngl.LINES)
        vbo.release()
        vao.release()

    def _render_overlay(self) -> None:
        """Render overlay UI on top of the scene."""
        # Position overlay in top-left of viewport
        overlay_pos = imgui.ImVec2(
            self._viewport_pos[0] + 10,
            self._viewport_pos[1] + 10
        )
        imgui.set_next_window_pos(overlay_pos)
        imgui.set_next_window_bg_alpha(0.6)

        overlay_flags = (
            imgui.WindowFlags_.no_decoration |
            imgui.WindowFlags_.always_auto_resize |
            imgui.WindowFlags_.no_saved_settings |
            imgui.WindowFlags_.no_focus_on_appearing |
            imgui.WindowFlags_.no_nav
        )

        if imgui.begin("SceneOverlay", None, overlay_flags):
            imgui.text(f"Camera: ({self._camera_x:.0f}, {self._camera_y:.0f})")
            imgui.text(f"Zoom: {self._zoom:.1f}x")

            if self.state.selected_tile:
                imgui.text(f"Tile: {self.state.selected_tile}")

        imgui.end()

    def _handle_input(self) -> None:
        """Handle mouse input in the viewport."""
        io = imgui.get_io()
        mouse_pos = io.mouse_pos

        # Calculate mouse position relative to viewport
        rel_x = mouse_pos.x - self._viewport_pos[0]
        rel_y = mouse_pos.y - self._viewport_pos[1]

        # Convert to world coordinates
        world_x = (rel_x / self._zoom) + self._camera_x
        world_y = (rel_y / self._zoom) + self._camera_y

        # Calculate tile position
        tile_x = int(world_x // self.state.grid_size)
        tile_y = int(world_y // self.state.grid_size)
        self.state.selected_tile = (tile_x, tile_y)

        # Middle mouse button for panning
        if imgui.is_mouse_dragging(imgui.MouseButton_.middle):
            delta = io.mouse_delta
            self._camera_x -= delta.x / self._zoom
            self._camera_y -= delta.y / self._zoom

        # Scroll wheel for zooming
        if io.mouse_wheel != 0:
            zoom_factor = 1.1 if io.mouse_wheel > 0 else 0.9

            # Zoom towards mouse position
            old_world_x = (rel_x / self._zoom) + self._camera_x
            old_world_y = (rel_y / self._zoom) + self._camera_y

            self._zoom *= zoom_factor
            self._zoom = max(0.25, min(4.0, self._zoom))

            new_world_x = (rel_x / self._zoom) + self._camera_x
            new_world_y = (rel_y / self._zoom) + self._camera_y

            self._camera_x += old_world_x - new_world_x
            self._camera_y += old_world_y - new_world_y

        # Left click for tool action
        if imgui.is_mouse_clicked(imgui.MouseButton_.left):
            self._on_tool_click(world_x, world_y, tile_x, tile_y)

        # Left drag for painting
        if imgui.is_mouse_down(imgui.MouseButton_.left):
            self._on_tool_drag(world_x, world_y, tile_x, tile_y)

    def _on_tool_click(
        self,
        world_x: float,
        world_y: float,
        tile_x: int,
        tile_y: int,
    ) -> None:
        """Handle tool click."""
        # Reset last paint position on new click
        self._last_paint_tile = (tile_x, tile_y)

        if self.state.current_tool == "brush":
            self._paint_tile(tile_x, tile_y)
        elif self.state.current_tool == "eraser":
            self._erase_tile(tile_x, tile_y)
        elif self.state.current_tool == "select":
            self.state.selected_tile = (tile_x, tile_y)
        elif self.state.current_tool == "eyedropper":
            self._eyedrop_tile(tile_x, tile_y)

    def _on_tool_drag(
        self,
        world_x: float,
        world_y: float,
        tile_x: int,
        tile_y: int,
    ) -> None:
        """Handle tool drag."""
        if self.state.current_tool == "brush":
            # Only paint if we moved to a new tile
            if self._last_paint_tile != (tile_x, tile_y):
                self._paint_tile(tile_x, tile_y)
                self._last_paint_tile = (tile_x, tile_y)
        elif self.state.current_tool == "eraser":
            if self._last_paint_tile != (tile_x, tile_y):
                self._erase_tile(tile_x, tile_y)
                self._last_paint_tile = (tile_x, tile_y)

    def _paint_tile(self, tile_x: int, tile_y: int) -> None:
        """Paint a tile at the specified position."""
        layer = self.state.get_current_layer()
        if not layer:
            # Create a default tilemap if none exists
            if not self.state.current_tilemap:
                self.state.create_new_tilemap()
                layer = self.state.get_current_layer()

        if layer:
            # Apply brush size
            brush_size = self.state.brush_size
            tile_id = self.state.brush_tile

            for dy in range(brush_size):
                for dx in range(brush_size):
                    layer.set_tile(tile_x + dx, tile_y + dy, tile_id)

            self.state.mark_dirty()

    def _erase_tile(self, tile_x: int, tile_y: int) -> None:
        """Erase a tile at the specified position."""
        layer = self.state.get_current_layer()
        if layer:
            brush_size = self.state.brush_size

            for dy in range(brush_size):
                for dx in range(brush_size):
                    layer.set_tile(tile_x + dx, tile_y + dy, -1)

            self.state.mark_dirty()

    def _eyedrop_tile(self, tile_x: int, tile_y: int) -> None:
        """Pick the tile at the specified position."""
        layer = self.state.get_current_layer()
        if layer:
            tile_id = layer.get_tile(tile_x, tile_y)
            if tile_id >= 0:
                self.state.brush_tile = tile_id

    def screen_to_world(self, screen_x: float, screen_y: float) -> tuple[float, float]:
        """Convert screen coordinates to world coordinates."""
        rel_x = screen_x - self._viewport_pos[0]
        rel_y = screen_y - self._viewport_pos[1]
        return (
            (rel_x / self._zoom) + self._camera_x,
            (rel_y / self._zoom) + self._camera_y,
        )

    def world_to_screen(self, world_x: float, world_y: float) -> tuple[float, float]:
        """Convert world coordinates to screen coordinates."""
        return (
            (world_x - self._camera_x) * self._zoom + self._viewport_pos[0],
            (world_y - self._camera_y) * self._zoom + self._viewport_pos[1],
        )
