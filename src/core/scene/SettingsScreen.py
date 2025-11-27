import pygame

from typing import Union
from core.config_manager import write_config, SUPPORTED_RESOLUTIONS, SUPPORTED_MAXIMUM_REFRESH_RATE, SUPPORTED_LANGUAGE_CODES, LANGUAGE_NAMES
from core.scene.EventState import EventState
from core.scene.SceneManager import SceneManager
from core.scene.Scene import Scene
from core.ui.components.AnimatedGlowingButton import AnimatedGlowingButton
from core.ui.components.SettingEntry import SettingOptionEntry, SettingValueEntry, SettingToggleEntry


class SettingsScreen(Scene):
    __SEPERATOR = "SEPERATOR_STRING"
    _SETTINGS_KEYS: list[str] = [
        "language",
        __SEPERATOR,
        "sfx",
        "bgm",
        __SEPERATOR,
        "resolution",
        "max_refresh_rate",
        __SEPERATOR,
        "text_display_speed",
        "autoplay_mode_speed",
        "skip_read_scenes"
    ]
    _OPTION_KEYS: set[str] = {
        "language",
        "resolution",
        "max_refresh_rate"
    }
    _VALUE_KEYS: set[str] = {
        "sfx",
        "bgm",
        "text_display_speed",
        "autoplay_mode_speed"
    }
    _TOGGLE_KEYS: set[str] = {
        "skip_read_scenes"
    }

    def __init__(
        self,
        scene_manager: SceneManager,
    ):
        self.sm: SceneManager = scene_manager
        self.window_size: tuple[int, int] = self.sm.screen.get_size()

        self.mouse_pos: tuple[int, int] = (0, 0)

    def enter(self) -> None:
        # Font
        font = pygame.font.Font(self.sm.language_data.get_str("font_path"), self.rscale(40))

        # Background
        background_opacity = 0.9
        background_alpha = int(255 * max(0.0, min(1.0, background_opacity)))
        self.background_overlay = pygame.Surface(self.window_size, pygame.SRCALPHA)
        # Fill with a semi-transparent mask to dim the gameplay layer.
        self.background_overlay.fill((0, 0, 0, background_alpha))

        # Options
        self.entries: list[Union[SettingOptionEntry, SettingValueEntry, SettingToggleEntry]] = []
        entry_width = int(self.window_size[0] * 0.7)
        option_width = max(self.rscale(260), entry_width // 3)
        start_x = (self.window_size[0] - entry_width) // 2
        start_y = int(self.window_size[1] * 0.12)
        gap_y = self.rscale(70)

        def _default_for(key: str) -> Union[str, float, bool]:
            config = self.sm.config_parser
            match key:
                case "language":
                    return LANGUAGE_NAMES[config.get("General", "language", fallback=SUPPORTED_LANGUAGE_CODES[0])]
                case "sfx":
                    return config.getint("Volume", "sfx", fallback=50)
                case "bgm":
                    return config.getint("Volume", "bgm", fallback=50)
                case "resolution":
                    width = config.getint("General", "resolution_width", fallback=SUPPORTED_RESOLUTIONS[0][0])
                    height = config.getint("General", "resolution_height", fallback=SUPPORTED_RESOLUTIONS[0][1])
                    return f"{width}x{height}"
                case "max_refresh_rate":
                    return config.getint("General", "max_refresh_rate", fallback=60)
                case "text_display_speed":
                    return config.getint("Scene", "text_display_speed", fallback=50)
                case "autoplay_mode_speed":
                    return config.getint("Scene", "autoplay_mode_speed", fallback=50)
                case "skip_read_scenes":
                    return config.getboolean("Scene", "skip_read_scenes", fallback=False)
            return ""

        for idx, key in enumerate(self._SETTINGS_KEYS):
            # Seperate sections
            if key == self.__SEPERATOR:
                continue

            pos = (start_x, start_y + idx * gap_y)
            label = f"{self.sm.language_data.get_str('settingsMenu', key)} >\\"
            default_value = _default_for(key)

            if key in self._OPTION_KEYS:
                match key:
                    case "language":
                        self.entries.append(
                            SettingOptionEntry(
                                label,
                                tuple(LANGUAGE_NAMES.values()),
                                SUPPORTED_LANGUAGE_CODES,
                                str(default_value),
                                pos,
                                entry_width,
                                option_width,
                                font
                            )
                        )
                    case "resolution":
                        resolutions = [f"{w}x{h}" for w, h in SUPPORTED_RESOLUTIONS]
                        resolutions_in_values = [(w, h) for w, h, in SUPPORTED_RESOLUTIONS]
                        self.entries.append(
                            SettingOptionEntry(
                                label,
                                resolutions,
                                resolutions_in_values,
                                str(default_value),
                                pos,
                                entry_width,
                                option_width,
                                font
                            )
                        )
                    case "max_refresh_rate":
                        self.entries.append(
                            SettingOptionEntry(
                                label,
                                [str(r) for r in SUPPORTED_MAXIMUM_REFRESH_RATE],
                                SUPPORTED_MAXIMUM_REFRESH_RATE,
                                str(default_value),
                                pos,
                                entry_width,
                                option_width,
                                font
                            )
                        )
                continue

            elif key in self._VALUE_KEYS:
                self.entries.append(
                    SettingValueEntry(label, 0, 100, int(default_value), pos, entry_width, option_width, font)
                )
                continue

            elif key in self._TOGGLE_KEYS:
                on_text = self.sm.language_data.get_str("settingsMenu", "on")
                off_text = self.sm.language_data.get_str("settingsMenu", "off")
                self.entries.append(
                    SettingToggleEntry(label, (on_text, off_text), bool(default_value), pos, entry_width, option_width, font)
                )

        # Return Button
        self.return_button = AnimatedGlowingButton(
            self.sm.language_data.get_str("settingsMenu", "return"),
            "return",
            (self.rscale(self.sm.screen.size[0] / 2), self.rscale(start_y + gap_y * (1 + len(self._SETTINGS_KEYS)))),
            font
        )

    def leave(self) -> None:
        key_section = {
            "language": "General",
            "resolution": "General",
            "max_refresh_rate": "General",

            "sfx": "Volume",
            "bgm": "Volume",

            "text_display_speed": "Scene",
            "autoplay_mode_speed": "Scene",
            "skip_read_scenes": "Scene",
        }

        # Writes current setting into parser and config file.
        for key, entry in zip([k for k in self._SETTINGS_KEYS if k != self.__SEPERATOR], self.entries):
            if isinstance(entry, SettingOptionEntry):
                if key == "resolution":
                    self.sm.config_parser[key_section[key]][f"{key}_width"] = str(entry.current_option_in_value[0])
                    self.sm.config_parser[key_section[key]][f"{key}_height"] = str(entry.current_option_in_value[1])
                    continue
                self.sm.config_parser[key_section[key]][key] = str(entry.current_option_in_value)
            elif isinstance(entry, SettingValueEntry):
                self.sm.config_parser[key_section[key]][key] = str(entry.current_value)
            elif isinstance(entry, SettingToggleEntry):
                self.sm.config_parser[key_section[key]][key] = str(entry.current_is_toggled)

        write_config(self.sm.config_parser)
        self.sm.reload_language_data()

        return

    def handle(self, ev: EventState) -> bool:
        # Log mouse pos for button collision check
        self.mouse_pos = ev.mouse_pos

        # Quit
        if (pygame.K_ESCAPE in ev.key_down) or \
            (1 in ev.mouse_down and self.return_button.is_hovered):
            self.sm.stack_pop()

        # Consume inputs
        return True

    def update(self, dt: float) -> None:
        for entry in self.entries:
            entry.update(dt, self.mouse_pos)
        self.return_button.update(dt, self.mouse_pos)

    def draw(self, surface: pygame.Surface) -> None:
        # Backgronnd
        surface.blit(self.background_overlay, (0, 0))

        for entry in self.entries:
            entry.render(surface)
        self.return_button.render(surface)

    def scale(self, base_value: Union[int, float]) -> float:
        return base_value * self.sm.uniform_scale

    def rscale(self, base_value: Union[int, float]) -> int:
        return round(base_value * self.sm.uniform_scale)

    def reload_language_data(self) -> None:
        # The config is saved after the scene gets dropped
        # Thus needless to reload
        return

    @property
    def is_overlay(self) -> bool:
        return True
