import random
import pygame
import math

class ScreenShake:
    def __init__(self):
        self.duration = 0
        self.timer = 0
        self.intensity = 0
        self.frequency = 0
        self.infinite = False
        self.seed = random.random()

    def start(self, duration: float, intensity: float, frequency: float = 35, infinite: bool = False):
        self.duration = duration
        self.timer = duration
        self.intensity = intensity
        self.frequency = frequency
        self.infinite = infinite
        self.seed = random.random()

    def update(self, dt: float):
        if self.infinite and self.timer <= 0:
            self.timer = self.duration
        if self.timer <= 0:
            return
        self.timer -= dt

    def get_offset(self) -> pygame.Vector2:
        if self.timer <= 0:
            return pygame.Vector2(0, 0)

        t = self.timer / self.duration
        decay = t * t  # quadratic ease-out

        angle = random.random() * 2 * math.pi
        dist = random.random() * self.intensity * decay

        return pygame.Vector2(
            math.cos(angle) * dist,
            math.sin(angle) * dist
        )
