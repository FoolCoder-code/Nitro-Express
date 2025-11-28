import pygame

from core.ui.components.AnimatedGlowingButton import AnimatedGlowingButton


class SaveSlotEntry:
    """
    Simple save slot used by the save selector screen.
    """
    def __init__(
        self,
        slot_index: int,
        text: str,
        action_text: str,
        action: str,
        pos: tuple[int, int],
        entry_width: int,
        font: pygame.font.Font,
    ) -> None:
        # Static UI data
        self.slot_index = slot_index
        self.pos = pos
        self.entry_width = entry_width
        self.text = text
        self.font = font

        # Colors + spacing
        self.text_color = (255, 255, 255)
        self.spacing = 12
        self._mouse_down_last = False

        # Action Button
        self.text_surface = self.font.render(self.text, True, self.text_color)
        self.text_rect = self.text_surface.get_rect(topleft=self.pos)
        button_preview = self.font.render(action_text, True, self.text_color)
        button_width, _ = button_preview.get_size()
        center_x = self.pos[0] + self.entry_width - self.spacing * 2 - button_width // 2
        center_y = self.text_rect.centery

        self.action_button = AnimatedGlowingButton(
            action_text,
            action,
            (center_x, center_y),
            self.font,
        )

        # Updated each frame
        self.was_clicked = False

    def update(self, delta: float, mouse_pos: tuple[int, int]) -> None:
        """
        Update hover/click state. Consuming clicks is up to the parent scene.
        """
        self.was_clicked = False
        if self.action_button:
            self.action_button.update(delta, mouse_pos)

            left_clicked = self._update_click_state()
            if left_clicked and self.action_button.is_hovered:
                self.was_clicked = True

    def render(self, screen: pygame.Surface) -> None:
        if self.text_surface and self.text_rect:
            screen.blit(self.text_surface, self.text_rect.topleft)

        if self.action_button:
            self.action_button.render(screen)

    def _update_click_state(self) -> bool:
        mouse_buttons = pygame.mouse.get_pressed(3)
        left_clicked = mouse_buttons[0] and not self._mouse_down_last
        self._mouse_down_last = mouse_buttons[0]
        return left_clicked
