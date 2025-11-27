import pygame

from typing import Any, Sequence


class SettingEntryBase:
    # Shared layout + interaction helpers for all setting entries.
    def __init__(
        self,
        text: str,
        pos: tuple[int, int],
        entry_width: int,
        option_width: int,
        font: pygame.font.Font,
    ) -> None:
        # Static UI data
        self.text = text
        self.pos = pos
        self.entry_width = entry_width
        self.option_width = option_width
        self.font = font

        # Colors for normal, arrow, and hover states
        self.text_color = (255, 255, 255)
        self.arrow_color = (200, 200, 200)
        self.hover_color = (255, 200, 100)

        # Spacing constants used by all child layouts
        self.spacing = 12
        self.outer_gap = self.spacing * 2
        self._mouse_down_last = False

        # Populated at layout time
        self.text_surface: pygame.Surface | None = None
        self.text_rect: pygame.Rect | None = None

    def _compute_area(self) -> tuple[int, int, int]:
        # Compute the right-side block where options/arrows live
        area_left = self.pos[0] + self.entry_width - self.option_width
        area_top = self.pos[1]
        center_x = area_left + self.option_width // 2
        return area_left, area_top, center_x

    def _build_text(self) -> tuple[int, int, int]:
        # Render the label and return placement helpers
        self.text_surface = self.font.render(self.text, True, self.text_color)
        self.text_rect = self.text_surface.get_rect(topleft=self.pos)
        return self._compute_area()

    def _update_click_state(self) -> bool:
        # Detect a fresh left click (not just held down)
        mouse_buttons = pygame.mouse.get_pressed(3)
        left_clicked = mouse_buttons[0] and not self._mouse_down_last
        self._mouse_down_last = mouse_buttons[0]
        return left_clicked

    def _render_label(self, screen: pygame.Surface) -> None:
        # Draw the left-hand label if present
        if self.text_surface and self.text_rect:
            screen.blit(self.text_surface, self.text_rect.topleft)


class SettingOptionEntry(SettingEntryBase):
    # Arrow-based selector cycling through a fixed list of options.
    def __init__(
            self,
            text: str,
            options: Sequence[str],
            options_in_values: Sequence[Any],
            default_option: str,

            pos: tuple[int, int],
            entry_width: int,
            option_width: int,
            font: pygame.font.Font,
        ) -> None:
        if len(options) == 0:
            raise ValueError("SettingOptionEntry requires at least one option.")

        super().__init__(text, pos, entry_width, option_width, font)

        # Option list and current index
        self.options = list(options)
        self.options_in_values = list(options_in_values)
        self.current_index = self.options.index(default_option) if default_option in self.options else 0

        self._hover_left = False
        self._hover_right = False

        self._build_layout()

    @property
    def current_option(self) -> str:
        return self.options[self.current_index]

    def _build_layout(self) -> None:
        # Build text, arrows, and option placement
        area_left, area_top, center_x = self._build_text()

        option_surface = self.font.render(self.current_option, True, self.text_color)
        left_arrow_surface = self.font.render("<", True, self.arrow_color)
        right_arrow_surface = self.font.render(">", True, self.arrow_color)

        self.option_rect = option_surface.get_rect(midtop=(center_x, area_top))
        self.left_arrow_rect = left_arrow_surface.get_rect(topleft=(area_left, area_top))
        self.right_arrow_rect = right_arrow_surface.get_rect(
            topleft=(area_left + self.option_width - right_arrow_surface.get_width(), area_top)
        )

    def _set_option(self, direction: int) -> None:
        self.current_index = (self.current_index + direction) % len(self.options)
        self._build_layout()

    def update(self, delta: float, mouse_pos: tuple[int, int]):
        left_clicked = self._update_click_state()

        # Hover states update every frame for color feedback
        self._hover_left = self.left_arrow_rect.collidepoint(mouse_pos)
        self._hover_right = self.right_arrow_rect.collidepoint(mouse_pos)

        # Click switches to previous/next option
        if left_clicked:
            if self._hover_left:
                self._set_option(-1)
            elif self._hover_right:
                self._set_option(1)

    @property
    def current_option_in_value(self):
        return self.options_in_values[self.current_index]

    def render(self, screen: pygame.Surface):
        self._render_label(screen)

        left_surface = self.font.render("<", True, self.hover_color if self._hover_left else self.arrow_color)
        option_surface = self.font.render(self.current_option, True, self.text_color)
        right_surface = self.font.render(">", True, self.hover_color if self._hover_right else self.arrow_color)

        screen.blit(left_surface, self.left_arrow_rect.topleft)
        screen.blit(option_surface, self.option_rect.topleft)
        screen.blit(right_surface, self.right_arrow_rect.topleft)

class SettingValueEntry(SettingEntryBase):
    # Numeric value selector with small/big step arrows.
    def __init__(
            self,
            text: str,
            min_value: int,
            max_value: int,
            default_value: int,

            pos: tuple[int, int],
            entry_width: int,
            option_width: int,
            font: pygame.font.Font,

        ) -> None:
        if max_value < min_value:
            raise ValueError("max_value should be greater than or equal to min_value.")

        super().__init__(text, pos, entry_width, option_width, font)

        # Value bounds + current value
        self.min_value = min_value
        self.max_value = max_value
        self.value = max(self.min_value, min(self.max_value, default_value))

        # Track hover for each arrow type for coloring
        self._hover_map = {
            "big_left": False,
            "small_left": False,
            "small_right": False,
            "big_right": False
        }

        self._build_layout()

    def _format_value(self) -> str:
        # Cleanly format value to int-like or trimmed float
        rounded = round(self.value, 2)
        if rounded.is_integer():
            return str(int(rounded))
        return f"{rounded:.2f}".rstrip("0").rstrip(".")

    def _build_layout(self) -> None:
        # Build all arrow rects around the value
        area_left, area_top, center_x = self._build_text()

        value_surface = self.font.render(self._format_value(), True, self.text_color)
        left_double_arrow_surface = self.font.render("<<", True, self.arrow_color)
        left_arrow_surface = self.font.render("<", True, self.arrow_color)
        right_arrow_surface = self.font.render(">", True, self.arrow_color)
        right_double_arrow_surface = self.font.render(">>", True, self.arrow_color)

        self.value_rect = value_surface.get_rect(midtop=(center_x, area_top))

        self.double_left_arrow_rect = left_double_arrow_surface.get_rect(topleft=(area_left, area_top))
        self.double_right_arrow_rect = right_double_arrow_surface.get_rect(
            topleft=(area_left + self.option_width - right_double_arrow_surface.get_width(), area_top)
        )

        # Position single arrows with breathing room between double arrows and value
        desired_small_left_right = self.value_rect.left - self.spacing
        self.left_arrow_rect = left_arrow_surface.get_rect(top=area_top)
        self.left_arrow_rect.right = max(desired_small_left_right, self.double_left_arrow_rect.right + self.outer_gap)

        desired_small_right_left = self.value_rect.right + self.spacing
        self.right_arrow_rect = right_arrow_surface.get_rect(top=area_top)
        self.right_arrow_rect.left = min(
            desired_small_right_left,
            self.double_right_arrow_rect.left - self.outer_gap - self.right_arrow_rect.width
        )

    def _change_value(self, delta: int) -> None:
        # Clamp and rebuild to refresh rendered positions
        self.value = max(self.min_value, min(self.max_value, self.value + delta))
        self._build_layout()

    def update(self, delta: float, mouse_pos: tuple[int, int]):
        left_clicked = self._update_click_state()

        # Hover map updates for per-arrow coloring
        self._hover_map["big_left"] = self.double_left_arrow_rect.collidepoint(mouse_pos)
        self._hover_map["small_left"] = self.left_arrow_rect.collidepoint(mouse_pos)
        self._hover_map["small_right"] = self.right_arrow_rect.collidepoint(mouse_pos)
        self._hover_map["big_right"] = self.double_right_arrow_rect.collidepoint(mouse_pos)

        # Apply step sizes based on which arrow was clicked
        if left_clicked:
            if self._hover_map["big_left"]:
                self._change_value(-10)
            elif self._hover_map["small_left"]:
                self._change_value(-1)
            elif self._hover_map["small_right"]:
                self._change_value(1)
            elif self._hover_map["big_right"]:
                self._change_value(10)

    def render(self, screen: pygame.Surface):
        self._render_label(screen)

        double_left_arrow_surface = self.font.render(
            "<<", True, self.hover_color if self._hover_map["big_left"] else self.arrow_color
        )
        left_arrow_surface = self.font.render(
            "<", True, self.hover_color if self._hover_map["small_left"] else self.arrow_color
        )
        value_surface = self.font.render(self._format_value(), True, self.text_color)
        right_arrow_surface = self.font.render(
            ">", True, self.hover_color if self._hover_map["small_right"] else self.arrow_color
        )
        double_right_arrow_surface = self.font.render(
            ">>", True, self.hover_color if self._hover_map["big_right"] else self.arrow_color
        )

        screen.blit(double_left_arrow_surface, self.double_left_arrow_rect.topleft)
        screen.blit(left_arrow_surface, self.left_arrow_rect.topleft)
        screen.blit(value_surface, self.value_rect.topleft)
        screen.blit(right_arrow_surface, self.right_arrow_rect.topleft)
        screen.blit(double_right_arrow_surface, self.double_right_arrow_rect.topleft)

    @property
    def current_value(self) -> int:
        return self.value

class SettingToggleEntry(SettingEntryBase):
    # Yes/No style toggle using arrows to flip state.
    def __init__(
            self,
            text: str,
            toggle_text: tuple[str, str], # Localized strings for [Yes, No]
            default_is_toggle: bool,

            pos: tuple[int, int],
            entry_width: int,
            option_width: int,
            font: pygame.font.Font
        ) -> None:
        super().__init__(text, pos, entry_width, option_width, font)

        self.toggle_text = toggle_text
        self.is_toggled = default_is_toggle

        self._hover_left = False
        self._hover_right = False

        self._build_layout()

    def _current_label(self) -> str:
        return self.toggle_text[0] if self.is_toggled else self.toggle_text[1]

    def _build_layout(self) -> None:
        # Build label and arrows for toggling
        area_left, area_top, center_x = self._build_text()

        label_surface = self.font.render(self._current_label(), True, self.text_color)
        left_arrow_surface = self.font.render("<", True, self.arrow_color)
        right_arrow_surface = self.font.render(">", True, self.arrow_color)

        self.label_rect = label_surface.get_rect(midtop=(center_x, area_top))
        self.left_arrow_rect = left_arrow_surface.get_rect(topleft=(area_left, area_top))
        self.right_arrow_rect = right_arrow_surface.get_rect(
            topleft=(area_left + self.option_width - right_arrow_surface.get_width(), area_top)
        )

    def update(self, delta: float, mouse_pos: tuple[int, int]):
        left_clicked = self._update_click_state()

        # Track hover for visual feedback
        self._hover_left = self.left_arrow_rect.collidepoint(mouse_pos)
        self._hover_right = self.right_arrow_rect.collidepoint(mouse_pos)

        # Flip toggle when either arrow is clicked
        if left_clicked and (self._hover_left or self._hover_right):
            self.is_toggled = not self.is_toggled
            self._build_layout()

    def render(self, screen: pygame.Surface):
        self._render_label(screen)

        left_surface = self.font.render("<", True, self.hover_color if self._hover_left else self.arrow_color)
        label_surface = self.font.render(self._current_label(), True, self.text_color)
        right_surface = self.font.render(">", True, self.hover_color if self._hover_right else self.arrow_color)

        screen.blit(left_surface, self.left_arrow_rect.topleft)
        screen.blit(label_surface, self.label_rect.topleft)
        screen.blit(right_surface, self.right_arrow_rect.topleft)

    @property
    def current_is_toggled(self) -> bool:
        return self.is_toggled