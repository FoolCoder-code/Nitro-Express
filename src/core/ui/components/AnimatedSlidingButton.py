import pygame

class AnimatedSlidingButton:
    def __init__(
            self,
            text: str,
            action: str,
            base_pos: tuple[int, int],
            font: pygame.font.Font,

            hover_offset: tuple[int, int] = (30, 0),
            hover_animation_speed: float = 10.0,
            *,
            normal_color: tuple[int, int, int] = (255, 255, 255),
            hover_color: tuple[int, int, int] = (255, 200, 100)
        ) -> None:
        # Data
        self.text = text
        self.action = action
        self.base_pos = base_pos
        self.current_offset = [0.0, 0.0]
        self.target_offset = [0.0, 0.0]

        self.is_hovered = False

        # Initialize
        self.normal_surface = font.render(self.text, True, normal_color)
        self.hover_surface = font.render(self.text, True, hover_color)
        self.rect = self.normal_surface.get_rect(
            topleft = self.base_pos
        )

        # Sliding effect
        self.hover_offset = list(hover_offset)
        self.hover_animation_speed = hover_animation_speed

    def update(self, delta: float, mouse_pos: tuple[int, int]):
        if self.rect.collidepoint(mouse_pos[0], mouse_pos[1]):
            self.is_hovered = True
            self.target_offset = self.hover_offset
        else:
            self.is_hovered = False
            self.target_offset = [0.0, 0.0]

        for i in [0, 1]:
            self.current_offset[i] += (self.target_offset[i] - self.current_offset[i]) * self.hover_animation_speed * delta
        self.rect.x = int(self.base_pos[0] + self.current_offset[0])
        self.rect.y = int(self.base_pos[1] + self.current_offset[1])

    def render(self, screen: pygame.Surface):
        surface = self.hover_surface if self.is_hovered else self.normal_surface
        screen.blit(surface, self.rect.topleft)
