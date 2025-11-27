import pygame

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class EventState:
    quit: bool = False
    resized: bool = False
    size: Tuple[int, int] = (0, 0)

    key_down: set[int] = field(default_factory=set)
    key_up: set[int] = field(default_factory=set)
    text_input: List[str] = field(default_factory=list)

    mouse_pos: Tuple[int, int] = (0, 0)
    mouse_rel: Tuple[int, int] = (0, 0)
    mouse_buttons: Tuple[int, int, int] = (0, 0, 0)
    mouse_down: set[int] = field(default_factory=set)
    mouse_up: set[int] = field(default_factory=set)

    wheel: Tuple[int, int] = (0, 0)
    wheel_events: List[Tuple[int, int]] = field(default_factory=list)

    dropped_files: List[str] = field(default_factory=list)
    modifiers: int = 0

    keys_pressed: Tuple[bool, ...] = tuple()

    def reset(self) -> None:
        """
        Clear instantaneous flags while keeping the continuous ones
        """
        self.quit = False
        self.resized = False

        self.key_down.clear()
        self.key_up.clear()
        self.text_input.clear()

        self.mouse_rel = (0, 0)
        self.mouse_down.clear()
        self.mouse_up.clear()
        self.wheel = (0, 0)

        self.dropped_files.clear()

    def pump_events(self) -> None:
        """
        Flush pygame.events to update self
        """
        # Update the snapshots of flags
        self.keys_pressed = pygame.key.get_pressed()
        self.mouse_pos = pygame.mouse.get_pos()
        self.mouse_rel = pygame.mouse.get_rel()
        self.mouse_buttons = pygame.mouse.get_pressed(num_buttons=3)

        for event in pygame.event.get():
            et = event.type
            if et == pygame.QUIT:
                self.quit = True

            elif et == pygame.VIDEORESIZE:
                self.resized = True
                self.size = (event.w, event.h)

            elif et == pygame.KEYDOWN:
                self.key_down.add(event.key)
                self.modifiers = event.mod

                if event.key == pygame.K_ESCAPE:
                    pass

            elif et == pygame.KEYUP:
                self.key_up.add(event.key)
                self.modifiers = event.mod

            elif et == pygame.TEXTINPUT:
                self.text_input.append(event.text)

            elif et == pygame.MOUSEBUTTONDOWN:
                b = event.button
                # Regular Mouse Buttons
                if b in (1, 2, 3):
                    self.mouse_down.add(b)
                # SDL 1 Wheel Events
                elif b in (4, 5, 6, 7):
                    dx = (1 if b == 7 else -1 if b == 6 else 0)
                    dy = (1 if b == 4 else -1 if b == 5 else 0)
                    if dx or dy:
                        self.wheel = (self.wheel[0] + dx, self.wheel[1] + dy)
                        self.wheel_events.append((dx, dy))

            elif et == pygame.MOUSEBUTTONUP:
                b = event.button
                if b in (1, 2, 3):
                    self.mouse_up.add(b)
                # Wheel Events ignored for already in MOUSEBUTTONDOWN

            elif hasattr(pygame, "MOUSEWHEEL") and et == pygame.MOUSEWHEEL:
                # SDL 2 Wheel event
                dx = int(event.x)
                dy = int(event.y)
                self.wheel = (self.wheel[0] + dx, self.wheel[1] + dy)
                self.wheel_events.append((dx, dy))

            elif et == pygame.DROPFILE:
                self.dropped_files.append(event.file)

        # Update again for events might change them
        # Idk why this happens
        self.mouse_pos = pygame.mouse.get_pos()
        self.mouse_rel = pygame.mouse.get_rel()
        self.mouse_buttons = pygame.mouse.get_pressed(num_buttons=3)
