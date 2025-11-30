import pygame

from typing import Union

from core.scene.EventState import EventState
from core.scene.Scene import Scene
from core.scene.SceneManager import SceneManager


class DialogueLog(Scene):
    def __init__(
        self,
        scene_manager: SceneManager,
        lines: list[tuple[str, str]],
        text_color: tuple[int, int, int],
        font: pygame.font.Font,
        *,
        is_overlay: bool = True,
        is_exclusive: bool = True
    ):
        self.sm = scene_manager
        self.is_overlay = is_overlay
        self.is_exclusive = is_exclusive

        self._lines = lines
        self._text_color = text_color
        self._font = font

        self.mouse_pos: tuple[int, int] = (0, 0)

        self._window_size: tuple[int, int] = self.sm.screen.get_size()
        self._render_lines: list[pygame.Surface] = []
        self._line_gap_px: int = 0
        self._scroll: float = 0.0
        self._max_scroll: float = 0.0

    def enter(self) -> None:
        self._window_size = self.sm.screen.get_size()
        self._rebuild_render_cache()
        return

    def leave(self) -> None:
        return

    def handle(self, ev: EventState) -> None:
        self.mouse_pos = ev.mouse_pos

        # Close when clicked anywhere / escape is pressed.
        if 1 in ev.mouse_down or pygame.K_ESCAPE in ev.key_down:
            self.sm.stack_pop()
            return

        step = self.rscale(40)
        page = self._window_size[1] * 0.8

        # Mouse Scroll
        if ev.wheel[1] != 0:
            self._scroll -= ev.wheel[1] * step

            # Coerce
            if self._scroll < 0.0:
                self._scroll = 0.0
            if self._scroll > self._max_scroll:
                self._scroll = self._max_scroll

        # Keyboard Scroll
        if pygame.K_UP in ev.key_down:
            self._scroll = max(0.0, self._scroll - step)
        if pygame.K_DOWN in ev.key_down:
            self._scroll = min(self._max_scroll, self._scroll + step)
        if pygame.K_PAGEUP in ev.key_down:
            self._scroll = max(0.0, self._scroll - page)
        if pygame.K_PAGEDOWN in ev.key_down:
            self._scroll = min(self._max_scroll, self._scroll + page)
        if pygame.K_HOME in ev.key_down:
            self._scroll = 0.0
        if pygame.K_END in ev.key_down:
            self._scroll = self._max_scroll

    def update(self, dt: float) -> None:
        return

    def draw(self, surface: pygame.Surface) -> None:
        # Background
        overlay = pygame.Surface(self.sm.screen.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        surface.blit(overlay, (0, 0))

        if not self._render_lines:
            return

        padding = self.rscale(36)
        h = self._window_size[1]
        y = padding - int(self._scroll)  # y after scroll

        # Draws only visible part
        for line_surf in self._render_lines:
            line_h = line_surf.get_height()

            # Skip when the bottom is above padding
            if y + line_h < padding:
                y += line_h + self._line_gap_px
                continue

            # Stop when the top is below padding
            if y > h - padding:
                break

            surface.blit(line_surf, (padding, y))
            y += line_h + self._line_gap_px

    def scale(self, base_value: Union[int, float]) -> float:
        return base_value * self.sm.uniform_scale

    def rscale(self, base_value: Union[int, float]) -> int:
        return round(base_value * self.sm.uniform_scale)

    def reload_language_data(self) -> None:
        return

    def _rebuild_render_cache(self) -> None:
        self._render_lines.clear()

        if not self._lines:
            self._scroll = 0.0
            self._max_scroll = 0.0
            return

        padding = self.rscale(36)
        max_width = self._window_size[0] - padding * 2
        self._line_gap_px = self.rscale(10)

        # Expand dialogues to multiple lines
        for speaker, text in self._lines:
            prefix = f"{speaker}{':' if speaker else ''} "
            full_text = prefix + text
            wrapped_text_lines = self._wrap_text(full_text, max_width)

            for t in wrapped_text_lines:
                surf = self._font.render(t, True, self._text_color)
                self._render_lines.append(surf)

        if not self._render_lines:
            self._scroll = 0.0
            self._max_scroll = 0.0
            return

        # Computes Height and Lines
        total_height = 0
        for surf in self._render_lines:
            total_height += surf.get_height() + self._line_gap_px
        total_height -= self._line_gap_px  # No gap for last line

        visible_height = self._window_size[1] - padding * 2
        self._max_scroll = max(0.0, float(total_height - visible_height))

        self._scroll = self._max_scroll

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        if not text:
            return [""]

        lines: list[str] = []
        current = ""

        for ch in text:
            candidate = current + ch
            w, _ = self._font.size(candidate)
            if w <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = ch

        if current:
            lines.append(current)

        return lines
