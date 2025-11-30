import datetime
import pygame

from typing import Union
from core.save_manager import SaveDict, read_save_file, write_save_file, remove_save_file
from core.path_resolver import ensure_dir, userdata_dir
from core.scene.EventState import EventState
from core.scene.SceneManager import SceneManager
from core.scene.Scene import Scene
from core.scene.DialogueScene import DialogueScene
from core.ui.components.AnimatedGlowingButton import AnimatedGlowingButton
from core.ui.components.SaveSlotEntry import SaveSlotEntry


class SaveSelector(Scene):
    """
    Simple save-selection scene that displays three placeholder slots.
    """
    def __init__(
            self,
            scene_manager: SceneManager,
            *,
            is_overlay: bool = True,
            is_exclusive: bool = True
        ):
        self.sm = scene_manager
        self.is_overlay = is_overlay
        self.is_exclusive = is_exclusive

        self.window_size = self.sm.screen.size

        self.mouse_pos: tuple[int, int] = (0, 0)
        self.slot_entries: list[SaveSlotEntry] = []

        self.save_operating_modes = ["load", "overwrite", "remove"]
        self.save_operating_mode: str = "load"

    def enter(self) -> None:
        # Font
        self.font = pygame.font.Font(self.sm.language_data.get_str("font_path"), self.rscale(36))

        # Background
        background_opacity = 0.9
        background_alpha = int(255 * max(0.0, min(1.0, background_opacity)))
        self.background_overlay = pygame.Surface(self.window_size, pygame.SRCALPHA)
        self.background_overlay.fill((0, 0, 0, background_alpha))

        # Slots
        self._slot_len = 16

        self._entry_width = self.rscale(1200)
        self._entry_start_x = (self.window_size[0] - self._entry_width) // 2
        self._entry_start_y = round(self.window_size[1] * 0.06)
        self._entry_gap_y = self.rscale(54)

        self._reload_save_slots()

        # Mode Button
        self._reload_mode_button(self.save_operating_mode)

        # Return Button
        self.return_button = AnimatedGlowingButton(
            self.sm.language_data.get_str("saveSelector", "return"),
            "return",
            (self.sm.screen.size[0] // 2, self._entry_start_y + self._entry_gap_y * (2 + self._slot_len)),
            self.font
        )

    def leave(self) -> None:
        return

    def handle(self, ev: EventState) -> None:
        self.mouse_pos = ev.mouse_pos

        # All the following events require LMB click
        if 1 not in ev.mouse_down:
            return

        # Slot Entry Buttons
        for entry in self.slot_entries:
            if not entry.action_button.is_hovered:
                continue
            print(f"Slot: {entry.slot_index} | Action: {entry.action_button.action}")
            from core.scene.PromptScene import PromptScene
            match entry.action_button.action:
                case "new":
                    write_save_file(entry.slot_index, SaveDict(
                        Savetime = datetime.datetime.now(),
                        Day = 1,
                        Slot_msg = "Awaken" # TODO: Add localization support for slot_msg
                    ))
                    self.sm.switch(DialogueScene(
                        self.sm,
                        self.sm.get_scene_data("dialogue_example")
                    ))
                case "load":
                    read_save_file(entry.slot_index)
                case "overwrite":
                    remove_save_file(entry.slot_index)
                case "remove":
                    remove_save_file(entry.slot_index)
            self._reload_save_slots()
            return

        # Toggle Mode
        if self.mode_button.is_hovered:
            self.save_operating_mode = self.save_operating_modes[
                (1 + self.save_operating_modes.index(self.save_operating_mode)) % len(self.save_operating_modes)
            ]
            print(f"Current Mode: {self.save_operating_mode}")
            self._reload_mode_button(self.save_operating_mode)
            self._reload_save_slots()

        # Quit
        if (pygame.K_ESCAPE in ev.key_down) or \
            self.return_button.is_hovered:
            self.sm.stack_pop()

    def update(self, dt: float) -> None:
        for entry in self.slot_entries:
            entry.update(dt, self.mouse_pos)

        self.mode_button.update(dt, self.mouse_pos)
        self.return_button.update(dt, self.mouse_pos)

    def draw(self, surface: pygame.Surface) -> None:
        # Background
        surface.blit(self.background_overlay, (0, 0))

        # Slot
        for entry in self.slot_entries:
            entry.render(surface)

        # Mode Button
        self.mode_button.render(surface)

        # Return Button
        self.return_button.render(surface)

    def scale(self, base_value: Union[int, float]) -> float:
        return base_value * self.sm.uniform_scale

    def rscale(self, base_value: Union[int, float]) -> int:
        return round(base_value * self.sm.uniform_scale)

    def reload_language_data(self) -> None:
        # It is impossible to change language in the scene
        pass

    def _reload_save_slots(self) -> None:
        ensure_dir(userdata_dir("sav"))
        self.slot_entries.clear()

        for idx in range(self._slot_len):
            try:
                sav_found = True
                curr_sav = read_save_file(idx+1)
            except FileNotFoundError:
                sav_found = False
                curr_sav = SaveDict(
                    Savetime = datetime.datetime(2000, 1, 1),
                    Day = 0,
                    Slot_msg = ""
                )

            entry_label = self.sm.language_data.get_str("saveSelector", "slot_label").replace(r"{slot}", str(idx + 1))
            day_label = self.sm.language_data.get_str("saveSelector", "day_label")

            if sav_found:
                entry_label = f"{entry_label} | {day_label.replace(r'{day}', str(curr_sav['Day']))} | {curr_sav['Slot_msg']}"

            action = self.save_operating_mode if sav_found else "new"
            action_text = self.sm.language_data.get_str("saveSelector", f"{action}_game_hint")

            self.slot_entries.append(SaveSlotEntry(
                idx + 1,
                entry_label,
                action_text,
                action,
                (self._entry_start_x, self._entry_start_y + self._entry_gap_y * idx),
                self._entry_width,
                self.font,
            ))

    def _reload_mode_button(self, mode: str) -> None:
        self.mode_button = AnimatedGlowingButton(
            self.sm.language_data.get_str("saveSelector", f"toggle_{mode}"),
            mode,
            (self.sm.screen.size[0] // 2, self._entry_start_y + self._entry_gap_y * (1 + self._slot_len)),
            self.font
        )