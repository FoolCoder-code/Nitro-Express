import pygame
import io
import json

from typing import Optional

from core.asset_manager import AssetPak, read_illustration_pak, read_sprite_pak, read_scene_pak, unpack_encoded_string
from core.config_manager import DEFAULT_LANGUAGE_CODE, get_config_parser
from core.locale.pak_loader import LangData
from core.scene.Scene import Scene
from core.scene.EventState import EventState
from core.scene.DialogueStructure import DialogueSceneData


class SceneManager:
    def __init__(
            self,
            screen: pygame.Surface,
            asset_illustrations: AssetPak | None = None,
            asset_sprites: AssetPak | None = None,
            asset_scenes: AssetPak | None = None
        ) -> None:
        self.scene_stack: list[Scene] = []
        self.screen = screen

        self.asset_illustrations = asset_illustrations if asset_illustrations else read_illustration_pak()
        self.asset_sprites = asset_sprites if asset_sprites else read_sprite_pak()
        self.asset_scenes = asset_scenes if asset_scenes else read_scene_pak()

        self.events = EventState()
        self._pending_switch: Optional[Scene] = None
        self.reloading_language_data: bool = False

        # Loads configuration and .paks of languages
        self.config_parser = get_config_parser()
        self.reload_language_data()

    @property
    def uniform_scale(self) -> float:
        # Scale based on 1920x1080
        # All the supported resolutions are 16:9 so only calculates once
        return self.screen.size[0] / 1920

    def get_illustration_iofile(self, filename_no_ext: str) -> io.BytesIO:
        return io.BytesIO(unpack_encoded_string(self.asset_illustrations["entries"][filename_no_ext]["encoded_string"]))

    def get_sprite_iofile(self, filename_no_ext: str) -> io.BytesIO:
        return io.BytesIO(unpack_encoded_string(self.asset_sprites["entries"][filename_no_ext]["encoded_string"]))

    def get_scene_data(self, filename_no_ext: str) -> DialogueSceneData:
        return json.loads(unpack_encoded_string(self.asset_scenes["entries"][filename_no_ext]["encoded_string"]))

    def reload_language_data(self) -> None:
        """
        Read language data based on current language and assign it to self.language_data.
        """
        curr_language = self.config_parser.get("General", "language", fallback = DEFAULT_LANGUAGE_CODE)
        self.language_data = LangData.from_pak(curr_language)
        self.reloading_language_data = True

    def stack_push(self, scene: Scene) -> None:
        """
        Push a scene on the stack and call enter so it can grab this manager.
        """
        self.scene_stack.append(scene)
        scene.enter()

    def stack_pop(self) -> None:
        """
        Pop the current top scene and notify it via leave for cleanup.
        """
        if self.scene_stack:
            top = self.scene_stack.pop()
            top.leave()

    def switch(self, scene: Scene) -> None:
        """
        Schedule a full switch to the given scene at the end of the frame.
        """
        self._pending_switch = scene

    def _apply_pending_switch(self) -> None:
        """
        If a switch is pending, clear the stack and push that scene.
        """
        if self._pending_switch is None:
            return

        while self.scene_stack:
            self.stack_pop()
        self.stack_push(self._pending_switch)
        self._pending_switch = None

    def update(self, delta: float) -> None:
        """
        Run the per-frame pipeline: events, input, update, draw, and switches.
        """
        # Clear event state and pump events
        self.events.reset()
        self.events.pump_events()

        # Reload interface when the current language is changed
        if self.reloading_language_data:
            for scene in self.scene_stack:
                scene.reload_language_data()
            self.reloading_language_data = False

        # Handle scenes and allow exclusive inputs for overlay
        # (Handle from last to first)
        for scene in reversed(self.scene_stack):
            if scene.handle(self.events):
                break

        # Update from first to last
        for scene in self.scene_stack:
            scene.update(delta)

        # Draw from first to last
        for scene in self.scene_stack:
            scene.draw(self.screen)

        # Apply switch
        self._apply_pending_switch()

    def clear(self) -> None:
        """
        emove all scenes from the stack, ensuring each receives leave.
        """
        while self.scene_stack:
            self.stack_pop()

    def top(self) -> Optional[Scene]:
        """
        Return the current top scene, or None if the stack is empty.

        Returns:
            Optional[Scene]: Current top scene, or None for the stack is empty.
        """
        return self.scene_stack[-1] if self.scene_stack else None

    def __len__(self) -> int:
        """
        Expose how many scenes are currently stacked.

        Returns:
            int: length of the stack of scenes.
        """
        return len(self.scene_stack)
