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

        # Render target
        self._fbo: moderngl.Framebuffer | None = None
        self._fbo_texture: moderngl.Texture | None = None
        self._needs_resize = True

    def update(self, dt: float) -> None:
        pass

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

        # Render grid if enabled
        if self.state.show_grid:
            self._render_grid()

        # TODO: Render tilemap
        # TODO: Render entities
        # TODO: Render selection

        # Restore default framebuffer
        self.game.ctx.screen.use()

    def _render_grid(self) -> None:
        """Render the editor grid."""
        # Simple grid rendering
        # TODO: Use shader for better performance
        pass

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
        if self.state.current_tool == "brush":
            self._paint_tile(tile_x, tile_y)
        elif self.state.current_tool == "select":
            self.state.selected_tile = (tile_x, tile_y)

    def _on_tool_drag(
        self,
        world_x: float,
        world_y: float,
        tile_x: int,
        tile_y: int,
    ) -> None:
        """Handle tool drag."""
        if self.state.current_tool == "brush":
            self._paint_tile(tile_x, tile_y)

    def _paint_tile(self, tile_x: int, tile_y: int) -> None:
        """Paint a tile at the specified position."""
        # TODO: Actually paint the tile
        self.state.mark_dirty()

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
