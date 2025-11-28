import pygame

from typing import Union
from core.path_resolver import asset_illustration
from core.locale.pak_loader import LangData
from core.scene.EventState import EventState
from core.scene.SceneManager import SceneManager
from core.scene.Scene import Scene
from core.ui.components.AnimatedSlidingButton import AnimatedSlidingButton
from core.scene.SettingsScreen import SettingsScreen
from core.scene.SaveSelector import SaveSelector


class Titlescreen(Scene):
    def __init__(
            self,
            scene_manager: SceneManager,
            button_hover_offset: tuple[int, int] = (30, -5),
            button_hover_animation_speed: float = 10.0
        ):
        self.sm: SceneManager = scene_manager

        self.windows_size: tuple[int, int] = self.sm.screen.get_size()
        self.button_hover_offset: tuple[int, int] = (
            self.rscale(button_hover_offset[0]),
            self.rscale(button_hover_offset[1])
        )
        self.button_hover_animation_speed: float = button_hover_animation_speed
        self.buttons: list[AnimatedSlidingButton] = []

        self.mouse_pos: tuple[int, int] = (0, 0)

    def enter(self) -> None:
        self.reload_elements(self.sm.language_data)

    def leave(self) -> None:
        return

    def handle(self, ev: EventState) -> bool:
        # For detecting if mouse is hovering on buttons
        self.mouse_pos = ev.mouse_pos

        # LMB isn't clicked
        if 1 not in ev.mouse_down:
            return False

        for button in self.buttons:
            if not button.is_hovered:
                continue

            print(f"Selected action: {button.action}")
            match button.action:
                case "game":
                    self.sm.stack_push(SaveSelector(self.sm))
                case "settings":
                    self.sm.stack_push(SettingsScreen(self.sm))
                case "exit":
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
            break
        return False

    def update(self, dt: float) -> None:
        for button in self.buttons:
            button.update(dt, self.mouse_pos)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.background)
        surface.blit(self.trapezoid_overlay)
        surface.blit(self.title, (self.windows_size[0] * 0.1, self.windows_size[1] * 0.15))

        for btn in self.buttons:
            btn.render(surface)

    def reload_language_data(self) -> None:
        self.reload_elements(self.sm.language_data)

    def scale(self, base_value: Union[int, float]) -> float:
        return base_value * self.sm.uniform_scale

    def rscale(self, base_value: Union[int, float]) -> int:
        return round(base_value * self.sm.uniform_scale)

    @property
    def is_overlay(self) -> bool:
        return False

    def reload_elements(self, language_data: LangData)-> None:
        # Fonts
        font_path = language_data.get_str("font_path")
        self.title_font = pygame.font.Font(font_path, self.rscale(96))
        self.button_font = pygame.font.Font(font_path, self.rscale(48))

        # Background
        bg_img = pygame.image.load(
            asset_illustration("title_background.png")
        ).convert()

        bg_img_w, bg_img_h = bg_img.get_size()

        # Background Scaling
        if bg_img_w == 0 or bg_img_h == 0:
            self.background = pygame.transform.scale(bg_img, self.windows_size)
        else:
            bg_img_scale = max(self.windows_size[0] / bg_img_w, self.windows_size[1] / bg_img_h)
            scaled_size = (int(bg_img_w * bg_img_scale), int(bg_img_h * bg_img_scale))
            scaled_bg_img = pygame.transform.smoothscale(bg_img, scaled_size)

            self.background = pygame.Surface(self.windows_size)
            bg_offset_x = (self.windows_size[0] - scaled_size[0]) // 2
            bg_offset_y = (self.windows_size[1] - scaled_size[1]) // 2
            self.background.blit(scaled_bg_img, (bg_offset_x, bg_offset_y))

        # Title
        self.title = self.title_font.render(
            language_data.get_str("titlescreen", "title"), True, (255, 255, 255)
        )

        # Buttons
        button_data = [
            (language_data.get_str("titlescreen", "button_start"), "game"),
            (language_data.get_str("titlescreen", "button_settings"), "settings"),
            (language_data.get_str("titlescreen", "button_exit"), "exit")
        ]
        self.buttons: list[AnimatedSlidingButton] = []
        self.hover_index = -1

        btn_x = self.windows_size[0] * 0.15
        btn_start_y = self.windows_size[1] * 0.35
        scaled_gap = self.windows_size[1] * 0.09
        for i, (text, action) in enumerate(button_data):
            topleft = (
                round(btn_x),
                round(btn_start_y + i*scaled_gap)
            )
            btn = AnimatedSlidingButton(text, action, topleft, self.button_font, self.button_hover_offset, self.button_hover_animation_speed)
            self.buttons.append(btn)

        # Trapezoid
        self.trapezoid_overlay = pygame.Surface(self.windows_size, pygame.SRCALPHA)
        self.trapezoid_color = (0, 0, 0, 160)
        top_left = (0, 0)
        top_right = (self.windows_size[0] * 0.45, 0)
        bottom_right = (self.windows_size[0] * 0.30, self.windows_size[1])
        bottom_left = (0, self.windows_size[1])

        pygame.draw.polygon(
            self.trapezoid_overlay,
            self.trapezoid_color,
            [top_left, top_right, bottom_right, bottom_left]
        )
