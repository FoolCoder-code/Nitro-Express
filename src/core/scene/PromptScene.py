import math
import pygame
import numpy as np

from typing import Union
from core.scene.EventState import EventState
from core.scene.SceneManager import SceneManager
from core.scene.Scene import Scene
from core.ui.components.AnimatedGlowingButton import AnimatedGlowingButton


class PromptScene(Scene):
    def __init__(
        self,
        sm: SceneManager,
        text: str,
        flag_key: str,
        options: list[str],
        option_flags: list[str],
        bg_filename_no_ext: str,
        *,
        is_overlay: bool = True,
        is_exclusive: bool = True
    ):
        if len(options) != len(option_flags):
            raise IndexError("Options and flags should have exactly same amount.")

        self.sm = sm
        self.is_overlay = is_overlay
        self.is_exclusive = is_exclusive

        self.text = text
        self.flag_key = flag_key
        self.options = options
        self.option_flags = option_flags

        self.window_size = self.sm.screen.get_size()
        self.option_rects: list[pygame.Rect] = []
        self.option_buttons: list[AnimatedGlowingButton] = []
        self.last_mouse_pos: tuple[int, int] = (0, 0)

        font_path = self.sm.language_data.get_str("font_path")
        self.font_title = pygame.font.Font(font_path, self.rscale(50))
        self.font_opt   = pygame.font.Font(font_path, self.rscale(44))

        # Layout constants
        self.panel_padding = self.rscale(36)
        self.row_gap = self.rscale(12)
        self.btn_padding_y = self.rscale(12)

        # Panel sizing (keep room for up to two rows of buttons)
        rows_estimate = math.ceil(len(self.options) / (1 if len(self.options) <= 1 else 2))
        row_height_guess = self.font_opt.get_height() + self.btn_padding_y * 2
        base_panel_h = max(self.rscale(210), int(self.window_size[1] * 0.22))
        min_content_h = (
            self.panel_padding * 2
            + self.font_title.get_height()
            + self.row_gap * 2
            + max(1, rows_estimate) * row_height_guess
            + max(0, rows_estimate - 1) * self.row_gap
        )
        panel_h = max(base_panel_h, min_content_h)
        panel_w = self.window_size[0]
        self.panel_size = (panel_w, panel_h)

        # Background
        raw_bg = pygame.image.load(
            self.sm.get_illustration_iofile(bg_filename_no_ext)
        ).convert_alpha()
        self.background = self._prepare_bg(raw_bg, self.panel_size)

        # Build base panel (white bar with tinted background)
        self.panel_surface = pygame.Surface(self.panel_size, pygame.SRCALPHA)
        self.panel_surface.fill((255, 255, 255, 235))
        self.panel_surface.blit(self.background, (0, 0))
        white_wash = pygame.Surface(self.panel_size, pygame.SRCALPHA)
        white_wash.fill((255, 255, 255, 70))
        self.panel_surface.blit(white_wash, (0, 0))

        # positioning
        self.rect = self.panel_surface.get_rect(center=(self.window_size[0]//2, self.window_size[1]//2))

        # Buttons
        self._build_option_buttons()

        self.frame = 0
        self.fade_duration = 18
        self.opacity = 0

        self.selected = 0

    def enter(self) -> None:
        pass

    def leave(self) -> None:
        pass

    def handle(self, ev: EventState) -> None:
        self.last_mouse_pos = ev.mouse_pos
        if pygame.K_ESCAPE in ev.key_down:
            self.sm.stack_pop()
        if self.options:
            if pygame.K_UP in ev.key_down:
                self.selected = (self.selected - 1) % len(self.options)
            if pygame.K_DOWN in ev.key_down:
                self.selected = (self.selected + 1) % len(self.options)
            if pygame.K_RETURN in ev.key_down:
                idx = self.selected
                self.sm.g_flags[self.flag_key] = self.option_flags[idx]
                self.sm.stack_pop()

        mouse_clicked = 1 in ev.mouse_down
        for idx, rect in enumerate(self.option_rects):
            mx, my = ev.mouse_pos
            if rect.collidepoint(mx, my):
                self.selected = idx
                if mouse_clicked:
                    self.sm.g_flags[self.flag_key] = self.option_flags[idx]
                    self.sm.stack_pop()

    def update(self, dt: float) -> None:
        if self.opacity < 255:
            self.frame += 1
            t = min(1, self.frame / self.fade_duration)
            self.opacity = int(255 * t)

        for idx, btn in enumerate(self.option_buttons):
            btn.update(dt, self.last_mouse_pos)
            if idx == self.selected:
                btn.is_hovered = True
                btn.hover_amount = 1.0

    def draw(self, surface: pygame.Surface) -> None:
        # Dim background
        dim = pygame.Surface(self.window_size, pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        surface.blit(dim, (0,0))

        # background panel
        panel = self.panel_surface.copy()

        # Draw Text
        title_surf = self.font_title.render(self.text, True, (30,30,30))
        title_rect = title_surf.get_rect(center=(self.panel_size[0] // 2, self.panel_padding + title_surf.get_height() // 2))
        panel.blit(title_surf, title_rect)

        # Draw Options
        self.option_rects = []
        if self.option_buttons:
            for idx, btn in enumerate(self.option_buttons):
                btn.render(panel)
                global_rect = btn.rect.move(self.rect.left, self.rect.top)
                self.option_rects.append(global_rect)

        panel.set_alpha(self.opacity)
        surface.blit(panel, self.rect)

    def scale(self, base_value: Union[int, float]) -> float:
        return base_value * self.sm.uniform_scale

    def rscale(self, base_value: Union[int, float]) -> int:
        return round(base_value * self.sm.uniform_scale)

    def reload_language_data(self) -> None:
        # It is impossible to change language in the scene
        pass

    def _prepare_bg(self, raw: pygame.Surface, target_size: tuple[int, int]) -> pygame.Surface:
        arr = pygame.surfarray.pixels3d(raw).copy()
        gray = (arr[...,0]*0.299 + arr[...,1]*0.587 + arr[...,2]*0.114).astype(np.uint8)
        gray_arr = np.stack((gray,gray,gray), axis=-1)
        surface = pygame.surfarray.make_surface(gray_arr).convert_alpha()

        # copy alpha channel
        alpha = pygame.surfarray.pixels_alpha(raw).copy()
        pygame.surfarray.pixels_alpha(surface)[:] = alpha

        # scale and crop to fit the panel while keeping central part
        target_w, target_h = target_size
        scale_ratio = max(target_w / surface.get_width(), target_h / surface.get_height())
        scaled_size = (
            max(1, int(surface.get_width() * scale_ratio)),
            max(1, int(surface.get_height() * scale_ratio))
        )
        scaled = pygame.transform.smoothscale(surface, scaled_size)

        fitted = pygame.Surface(target_size, pygame.SRCALPHA)
        offset_x = (scaled_size[0] - target_w) // 2
        offset_y = (scaled_size[1] - target_h) // 2
        fitted.blit(scaled, (-offset_x, -offset_y))

        # subtle desaturation wash for the semi-transparent look
        wash = pygame.Surface(target_size, pygame.SRCALPHA)
        wash.fill((245, 245, 245, 120))
        fitted.blit(wash, (0, 0))
        return fitted

    def _build_option_buttons(self) -> None:
        """
        Build text-only glowing buttons for options and cache their rects.
        """
        self.option_buttons.clear()
        self.option_rects = []

        if not self.options:
            return

        cols = 1 if len(self.options) == 1 else 2
        rows = math.ceil(len(self.options) / cols)
        available_w = self.panel_size[0] - self.panel_padding * 2
        col_width = available_w / cols
        row_height = self.font_opt.get_height() + self.btn_padding_y * 2

        # Position buttons toward lower half of the panel, but not above title
        option_area_top = self.panel_size[1] - self.panel_padding - rows * row_height - (rows - 1) * self.row_gap
        option_area_top = max(option_area_top, self.panel_padding + self.font_title.get_height() + self.row_gap * 2)

        for idx, opt in enumerate(self.options):
            row = idx // cols
            col = idx % cols

            cx = self.panel_padding + col_width * col + col_width / 2
            cy = option_area_top + row * (row_height + self.row_gap) + row_height / 2

            btn = AnimatedGlowingButton(
                opt,
                str(idx),
                (round(cx), round(cy)),
                self.font_opt,
                normal_color=(40, 40, 40),
                hover_text_color=(0, 0, 0),
                glow_color=(120, 120, 120),
                glow_layers=18,
                glow_max_alpha=90,
            )

            self.option_buttons.append(btn)
            self.option_rects.append(btn.rect.move(self.rect.left, self.rect.top))
