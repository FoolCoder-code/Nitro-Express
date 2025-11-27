import pygame


def brighten(color: tuple[int, int, int], factor: float = 1.25) -> tuple[int, int, int]:
    """Slightly brighten a color."""
    r, g, b = color
    return (
        min(int(r * factor), 255),
        min(int(g * factor), 255),
        min(int(b * factor), 255),
    )

class AnimatedGlowingButton:
    def __init__(
        self,
        text: str,
        action: str,
        base_pos: tuple[int, int],
        font: pygame.font.Font,
        *,
        normal_color: tuple[int, int, int] = (255, 255, 255),
        hover_text_color: tuple[int, int, int] | None = None,
        hover_letter_spacing: int = 2, # Extra letter spacing on hover (pixels)
        glow_color: tuple[int, int, int] = (255, 255, 255),
        glow_layers: int = 32, # Number of glow layers
        glow_scale_step: float = 0.02, # Scale step per layer
        glow_max_alpha: int = 80, # Maximum opacity when fully glowing
        glow_animation_speed: float = 10.0, # Glow fade-in/out speed
    ) -> None:
        self.text = text
        self.action = action
        self.base_pos = base_pos
        self.is_hovered = False

        # Color settings
        self.normal_color = normal_color
        self.hover_text_color = hover_text_color or brighten(normal_color)
        self.glow_color = glow_color

        self.glow_layers = glow_layers
        self.glow_scale_step = glow_scale_step
        self.glow_max_alpha = glow_max_alpha
        self.glow_animation_speed = glow_animation_speed

        self.font = font

        # Not hovered: normal text (no extra spacing)
        self.normal_surface = self.font.render(self.text, True, self.normal_color)

        # Hovered: slightly brighter with extra letter spacing
        self.hover_surface, self.hover_glyphs = self._render_text_with_spacing(
            self.text,
            self.font,
            self.hover_text_color,
            hover_letter_spacing,
        )

        # Shared hitbox centered on base_pos using the max of normal/hover sizes
        max_w = max(self.normal_surface.get_width(), self.hover_surface.get_width())
        max_h = max(self.normal_surface.get_height(), self.hover_surface.get_height())
        self.rect = pygame.Rect(0, 0, max_w, max_h)
        self.rect.center = self.base_pos

        self.glow_glyphs = [
            (
                self._create_multi_layer_glow(glyph, self.glow_color, self.glow_layers, self.glow_scale_step),
                x_offset,
                glyph.get_size(),
            )
            for glyph, x_offset in self.hover_glyphs
        ]

        # Glow intensity (0.0~1.0)
        self.hover_amount = 0.0

    @staticmethod
    def _render_text_with_spacing(
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        spacing: int,
    ) -> tuple[pygame.Surface, list[tuple[pygame.Surface, int]]]:
        """Render text with extra letter spacing and return surface plus glyph positions."""
        if spacing <= 0:
            glyph = font.render(text, True, color)
            return glyph, [(glyph, 0)]

        # Render glyphs one by one
        glyphs: list[pygame.Surface] = []
        widths: list[int] = []
        max_h = 0

        for ch in text:
            glyph = font.render(ch, True, color)
            glyphs.append(glyph)
            w, h = glyph.get_size()
            widths.append(w)
            if h > max_h:
                max_h = h

        if not glyphs:
            empty = font.render("", True, color)
            return empty, []

        total_width = sum(widths) + spacing * (len(glyphs) - 1)
        surf = pygame.Surface((total_width, max_h), pygame.SRCALPHA)

        x = 0
        glyph_positions: list[tuple[pygame.Surface, int]] = []
        for glyph, w in zip(glyphs, widths):
            surf.blit(glyph, (x, 0))
            glyph_positions.append((glyph, x))
            x += w + spacing

        return surf, glyph_positions

    @staticmethod
    def _create_multi_layer_glow(
        base_surface: pygame.Surface,
        color: tuple[int, int, int],
        layers: int,
        scale_step: float,
    ) -> pygame.Surface:
        """
        Create a natural-looking text glow from base_surface:
        - Use base_surface as the core
        - Each layer scales up slightly and lowers alpha
        - Stack many layers for a soft gradient
        Returns: glow_surface
        """
        w, h = base_surface.get_size()

        # Estimate max scale to size glow_surface
        max_scale = 1.0 + scale_step * (layers - 1)
        gw = int(w * max_scale) + 2
        gh = int(h * max_scale) + 2

        glow_surf = pygame.Surface((gw, gh), pygame.SRCALPHA)
        center = (gw // 2, gh // 2)

        # Tint base_surface to glow_color first to avoid the original color affecting the glow
        base_colored = base_surface.copy()
        # Simple tint: fill and alpha blend
        tint = pygame.Surface(base_surface.get_size(), pygame.SRCALPHA)
        tint.fill((*color, 0))
        base_colored.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        for i in range(layers):
            scale = 1.0 + scale_step * i
            layer_w = max(1, int(w * scale))
            layer_h = max(1, int(h * scale))

            layer = pygame.transform.smoothscale(base_colored, (layer_w, layer_h))

            # Bright center, dimmer edges using a simple squared falloff
            t = i / max(layers - 1, 1)
            alpha = int(255 * (1.0 - t) ** 2)

            layer.set_alpha(alpha)
            layer_rect = layer.get_rect(center=center)
            glow_surf.blit(layer, layer_rect)

        return glow_surf

    def update(self, delta: float, mouse_pos: tuple[int, int]):
        # Only evaluate hover; position stays unchanged
        self.is_hovered = self.rect.collidepoint(mouse_pos)

        target = 1.0 if self.is_hovered else 0.0
        self.hover_amount += (target - self.hover_amount) * self.glow_animation_speed * delta

        # Clamp to avoid floating-point drift
        if self.hover_amount < 0.001:
            self.hover_amount = 0.0
        elif self.hover_amount > 0.999:
            self.hover_amount = 1.0

    def render(self, screen: pygame.Surface):
        surface = self.hover_surface if self.is_hovered else self.normal_surface
        surface_rect = surface.get_rect(center=self.rect.center)

        if self.hover_amount > 0.0 and self.glow_glyphs:
            alpha = int(self.glow_max_alpha * self.hover_amount)
            glow_layout_rect = self.hover_surface.get_rect(center=self.rect.center)

            for glow_surface, x_offset, glyph_size in self.glow_glyphs:
                glow_surface.set_alpha(alpha)
                letter_center = (
                    glow_layout_rect.x + x_offset + glyph_size[0] * 0.5,
                    glow_layout_rect.y + glyph_size[1] * 0.5,
                )
                glow_rect = glow_surface.get_rect(center=letter_center)
                screen.blit(glow_surface, glow_rect.topleft)

        screen.blit(surface, surface_rect.topleft)
