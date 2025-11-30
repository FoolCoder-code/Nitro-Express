import pygame

from typing import Union
from core.scene.EventState import EventState
from core.scene.SceneManager import SceneManager
from core.scene.Scene import Scene
from core.scene.DialogueLog import DialogueLog
from core.scene.DialogueStructure import DialogueSceneData, DialogueActionData
from core.ui.components.AnimatedGlowingButton import AnimatedGlowingButton
from core.ui.effects.CoordsAnimator import Linear, OutCubic, InCubic, OutBack, InBack, Elastic
from core.ui.effects.Typewriter import Typewriter


class DialogueScene(Scene):
    def __init__(self, scene_manager: SceneManager, dialogue_data: DialogueSceneData, as_an_overlay: bool = False):
        self.sm = scene_manager
        self.dialogue_data: DialogueSceneData = dialogue_data
        self._as_an_overlay = as_an_overlay

        self.windows_size: tuple[int, int] = self.sm.screen.get_size()
        self.mouse_pos: tuple[int, int] = (0, 0)
        self.buttons: list[AnimatedGlowingButton] = []

        # Dialogue States
        self._last_pressed_continue: bool = False  # Handles input to prevent continuously skipping scenes
        self._continue_dialogue: bool = False      # For main loop to advance steps & actions
        self._curr_step_idx: int = 0
        self._curr_action_idx: int = 0
        self._last_action_idx: int = -1
        self.dialogue_history: list[tuple[str, str]] = []  # For Log Overlay (Speaker, Dialogue)

        self._dropdown_menu_toggled: bool = False

        self._auto_mode: bool = False
        self._auto_advance_timer: float = 0.0
        self._auto_advance_delay: float = 0.8 / self.config_cps_scale

        self._hide_mode: bool = False
        self._skip_mode: bool = False

        # UI Elements
        self.tw = Typewriter("", self.config_cps_scale)
        self._dialogue_lines: list[pygame.Surface] = []  # Wrapped dialogue lines (each is a rendered Surface)

        self.characters = {
            "sprite": {},
            "pos": {},
            "animator": {},
            "is_highlighted": {}
        }

        self.text_color: tuple[int, int, int] = self.dialogue_data.get(
            "text_color", (214, 214, 214)
        )
        self.slash_color: tuple[int, int, int] = self.dialogue_data.get(
            "slash_color", (214, 214, 214)
        )

    def enter(self) -> None:
        self.reload_elements()

        self._curr_step_idx = 0
        self._curr_action_idx = 0
        self._last_action_idx = -1
        self._continue_dialogue = False

        self._execute_step(self._curr_step_idx)

    def leave(self) -> None:
        return

    def handle(self, ev: EventState) -> bool:
        def keyboard_event() -> bool:
            # Reset the guard once the advance keys are released so future presses work
            if pygame.K_SPACE in ev.key_up or pygame.K_RETURN in ev.key_up:
                self._last_pressed_continue = False

            if not (pygame.K_SPACE in ev.key_down or pygame.K_RETURN in ev.key_down):
                return False

            if self._last_pressed_continue:
                return True

            self._last_pressed_continue = True
            if self.tw.is_finished:
                self._continue_dialogue = True
            else:
                self.tw.skip()
            return True

        def mouse_event() -> bool:
            if 1 not in ev.mouse_down:
                return False

            # Disable hide mode for LMB is clicked during hide mode
            if self._hide_mode:
                self._hide_mode = False
                return True

            for button in self.buttons:  # Prioritize Buttons
                if not button.is_hovered:
                    continue

                match button.action:
                    case "log":
                        if not self.dialogue_font:
                            return True
                        self.sm.stack_push(
                            DialogueLog(
                                self.sm,
                                self.dialogue_history,
                                self.text_color,
                                self.dialogue_font
                            )
                        )
                    case "auto":
                        self._auto_mode = not self._auto_mode
                        self._auto_advance_timer = 0.0
                    case "more":
                        self._dropdown_menu_toggled = not self._dropdown_menu_toggled
                    case "hide":
                        self._hide_mode = True
                    case "skip":
                        self._skip_mode = True
                return True

            # Continue the dialogue for no button is hovered
            if not self._last_pressed_continue:
                if self.tw.is_finished:
                    self._continue_dialogue = True
                else:
                    self.tw.skip()
            self._last_pressed_continue = False

            return True

        self.mouse_pos = ev.mouse_pos

        # Return when anyone is triggered
        if keyboard_event():
            return self.is_overlay
        if mouse_event():
            return self.is_overlay
        return self.is_overlay

    def update(self, dt: float) -> None:
        # Character Pos
        for k, v in self.characters["animator"].items():
            if v is None:
                continue
            if v.is_finished:
                self.characters["animator"][k] = None
                continue
            v.update(dt)
            self.characters["pos"][k] = v.curr

        # Dialogue Text (typewriter + wrap)
        self.tw.update(dt)

        # Get max width of text area
        w, h = self.windows_size
        dialogue_x = int(w * 0.2)
        padding_right = self.rscale(60)
        max_width = w - dialogue_x - padding_right

        # Wrap
        wrapped_lines = self._wrap_text(self.tw.visible_text, max_width)

        # Save as Surfaces
        self._dialogue_lines = [
            self.dialogue_font.render(line, True, self.text_color)
            for line in wrapped_lines
        ]

        # Auto Mode Dialogue Advance
        if self._auto_mode:
            if self.tw.is_finished and not self._continue_dialogue:
                self._auto_advance_timer += dt
                if self._auto_advance_timer >= self._auto_advance_delay:
                    self._continue_dialogue = True
                    self._auto_advance_timer = 0.0
            else:
                self._auto_advance_timer = 0.0
        else:
            self._auto_advance_timer = 0.0

        # Buttons
        for button in self.buttons:
            button.update(dt, self.mouse_pos)

        # Step
        self._advance_dialogue()

    def draw(self, surface: pygame.Surface) -> None:
        w, h = self.windows_size

        # Background
        surface.blit(self.background)

        # Character Sprites
        for k in self.characters["sprite"].keys():
            c_sprite = self.characters["sprite"][k]
            # Draw from rect center
            c_rect = c_sprite.get_rect()
            c_w, c_h = c_rect.width, c_rect.height
            pos = self.characters["pos"][k]

            c_pos = (pos[0] - c_w // 2, pos[1] - c_h // 2)
            surface.blit(self.characters["sprite"][k], c_pos)

            # Highlight effect (Dim others)
            if self.characters["is_highlighted"][k]:
                continue
            darkness = 0.4
            not_highlighted_mask = c_sprite.copy()
            not_highlighted_mask.fill((0, 0, 0, int(255 * darkness)), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(not_highlighted_mask, c_pos)

        # Hide UI
        if self._hide_mode:
            return

        # Dialogue Overlay
        surface.blit(self.dialogue_overlay, (0, h - self.dialogue_overlay.get_rect().height))

        # Dialogue
        name_pos = (w * 0.07, h * 0.79)
        ctitle_pos = (w * 0.08, h * 0.86)
        dialogue_pos = (w * 0.2, h * 0.8)

        surface.blit(self.name_surface, name_pos)
        surface.blit(self.ctitle_surface, ctitle_pos)

        # Lines of Text
        x, y = dialogue_pos
        line_gap = self.rscale(4)
        padding_bottom = self.rscale(40)

        for line_surf in self._dialogue_lines:
            line_h = line_surf.get_height()

            # Stop when it's out of screen
            if y > h - padding_bottom:
                break

            surface.blit(line_surf, (x, y))
            y += line_h + line_gap

        slash_pos = (w * 0.17, h * 0.8)
        line_length = self.rscale(120)
        line_width = max(1, self.rscale(2))
        start_pos = (slash_pos[0], slash_pos[1] + line_length)
        end_pos = (slash_pos[0] + line_length * 0.4, slash_pos[1])
        pygame.draw.line(surface, self.slash_color, start_pos, end_pos, line_width)

        # UI buttons
        for button in self.buttons:
            if button.action in ["hide", "skip"] and not self._dropdown_menu_toggled:
                continue
            button.render(surface)

    def scale(self, base_value: Union[int, float]) -> float:
        return base_value * self.sm.uniform_scale

    def rscale(self, base_value: Union[int, float]) -> int:
        return round(base_value * self.sm.uniform_scale)

    def reload_language_data(self) -> None:
        self.reload_elements()

    @property
    def is_overlay(self) -> bool:
        return self._as_an_overlay

    def reload_elements(self) -> None:
        # Fonts
        font_path = self.sm.language_data.get_str("font_path")
        self.name_font = pygame.font.Font(font_path, self.rscale(50))
        self.ctitle_font = pygame.font.Font(font_path, self.rscale(36))
        self.slash_font = pygame.font.Font(font_path, self.rscale(92))
        self.dialogue_font = pygame.font.Font(font_path, self.rscale(40))
        self.button_font = pygame.font.Font(font_path, self.rscale(40))

        # Surfaces
        self.name_surface = self.name_font.render("", True, self.text_color)
        self.ctitle_surface = self.ctitle_font.render("", True, self.text_color)

        self._reload_dialogue_overlay()
        self._reload_background()
        self._reload_characters()
        self._build_buttons()

    def _reload_dialogue_overlay(self) -> None:
        w, h = self.windows_size

        height_ratio = 0.35
        overlay_height = int(h * height_ratio)

        overlay = pygame.Surface((w, overlay_height), pygame.SRCALPHA)

        max_alpha = 200

        for y in range(overlay_height):
            t = y / (overlay_height - 1) if overlay_height > 1 else 1.0
            alpha = int(max_alpha * t)

            pygame.draw.line(overlay, (0, 0, 0, alpha), (0, y), (w, y))

        self.dialogue_overlay = overlay

    def _reload_background(self) -> None:
        def get_last_background_filename() -> tuple[str, int] | tuple[None, None]:
            for idx in reversed(range(self._curr_step_idx + 1)):
                curr_step = self.dialogue_data["steps"][idx]
                for action in reversed(curr_step["actions"]):
                    if action["type"] != "set_background":
                        continue
                    return action["args"]["filename"], int(action["args"]["blur"])  # type: ignore
            return (None, None)

        filename, blur = get_last_background_filename()

        if filename is None:
            self.background = pygame.Surface(self.windows_size)
            self.background.fill((0, 0, 0))
            return

        self.background = pygame.transform.smoothscale(
            pygame.image.load(
                self.sm.get_illustration_iofile(filename)
            ).convert(),
            self.windows_size
        )

        if blur:
            self.background = pygame.transform.gaussian_blur(self.background, blur)

    def _reload_characters(self) -> None:
        self.characters = {
            "sprite": {},
            "pos": {},
            "animator": {},
            "is_highlighted": {}
        }

        for character_data in self.dialogue_data["characters"]:
            c_img = pygame.image.load(
                self.sm.get_sprite_iofile(character_data["sprite_filename"])
            ).convert_alpha()
            c_sprite = pygame.transform.smoothscale_by(
                c_img,
                self.scale(character_data["scale"])
            )
            c_id = character_data["id"]
            self.characters["sprite"][c_id] = c_sprite
            # Prevent showing on the screen while initializing
            self.characters["pos"][c_id] = self.characters["pos"].get(c_id, (-10000, 0))
            self.characters["animator"][c_id] = self.characters["animator"].get(c_id, None)
            self.characters["is_highlighted"][c_id] = self.characters["is_highlighted"].get(c_id, False)

    def _build_buttons(self) -> None:
        btn_y = self.rscale(42)
        margin = self.rscale(80)
        gap = self.rscale(120)
        vgap = self.rscale(70)

        log_pos = (margin, btn_y)
        auto_pos = (self.windows_size[0] - (margin + gap), btn_y)
        more_pos = (self.windows_size[0] - margin, btn_y)

        hide_pos = (self.windows_size[0] - margin, btn_y + vgap)
        skip_pos = (self.windows_size[0] - margin, btn_y + vgap * 2)

        for button_action, button_pos in zip(
            ["log", "auto", "more", "hide", "skip"],
            [log_pos, auto_pos, more_pos, hide_pos, skip_pos]
        ):
            self.buttons.append(AnimatedGlowingButton(
                self.sm.language_data.get_str("dialogueScene", f"button_{button_action}"),
                button_action,
                button_pos,
                self.button_font
            ))

    @property
    def config_cps_scale(self) -> float:
        config_value = self.sm.config_parser.getint(
            "Scene", "text_display_speed", fallback=50
        )
        return 1 + ((config_value - 50) / 50.0)

    def _advance_dialogue(self) -> None:
        steps = self.dialogue_data["steps"]
        if self._curr_step_idx >= len(steps):
            return

        step_finished = self._execute_step(self._curr_step_idx)

        if step_finished:
            self._curr_step_idx += 1
            self._curr_action_idx = 0
            self._last_action_idx = -1
            self._continue_dialogue = False

            if self._curr_step_idx < len(steps):
                self._execute_step(self._curr_step_idx)
            else:
                pass

    def _execute_step(self, idx: int) -> bool:
        actions = self.dialogue_data["steps"][idx]["actions"]

        if self._curr_action_idx >= len(actions):
            return True

        while self._curr_action_idx < len(actions):
            action = actions[self._curr_action_idx]
            action_type = action.get("type")

            # Skip Mode
            if self._skip_mode and action_type != "prompt":
                if action_type == "show_text":
                    self._execute_action(action)
                    self.tw.skip()
                else:
                    self._execute_action(action)

                self._curr_action_idx += 1
                self._last_action_idx = -1
                continue

            # Non Skip Mode
            if self._last_action_idx != self._curr_action_idx:
                self._execute_action(action)
                self._last_action_idx = self._curr_action_idx

            if action_type in ("show_text", "prompt"):
                if not self.tw.is_finished:
                    return False

                if not self._continue_dialogue:
                    return False

                self._continue_dialogue = False

            self._curr_action_idx += 1
            self._last_action_idx = -1

            # Meet Prompt Action in Skip Mode
            if self._skip_mode and action_type == "prompt":
                self._skip_mode = False
                return False  # Let next frame deal with it

        self._skip_mode = False
        return True

    def _execute_action(self, action: DialogueActionData) -> None:
        args = action.get("args", {})

        def show_text(action: DialogueActionData) -> None:
            speaker_name = args["speaker_name"]
            speaker_title = args["speaker_title"]
            full_text = args["text"]

            self.name_surface = self.name_font.render(speaker_name, True, self.text_color)  # type: ignore
            self.ctitle_surface = self.ctitle_font.render(speaker_title, True, self.text_color)  # type: ignore
            self.tw.reset(full_text)  # type: ignore
            self.dialogue_history.append((speaker_name, full_text))  # type: ignore

        def play_bgm(action: DialogueActionData) -> None:
            pass

        def play_sfx(action: DialogueActionData) -> None:
            pass

        def show_character(action: DialogueActionData) -> None:
            character_id = str(args["character_id"])
            pos = self._relative_scale_to_pos(float(args["x"]), float(args["y"]))  # type: ignore
            self.characters["pos"][character_id] = pos

        def move_character(action: DialogueActionData) -> None:
            character_id = str(args["character_id"])
            from_pos = self._relative_scale_to_pos(float(args["from_x"]), float(args["from_y"]))  # type: ignore
            to_pos = self._relative_scale_to_pos(float(args["to_x"]), float(args["to_y"]))  # type: ignore
            duration = float(args["duration"])  # type: ignore
            easing = args["easing"]

            match easing:
                case "linear":
                    self.characters["animator"][character_id] = Linear(from_pos, to_pos, duration)
                case "out_cubic":
                    self.characters["animator"][character_id] = OutCubic(from_pos, to_pos, duration)
                case "in_cubic":
                    self.characters["animator"][character_id] = InCubic(from_pos, to_pos, duration)
                case "out_back":
                    self.characters["animator"][character_id] = OutBack(from_pos, to_pos, duration)
                case "in_back":
                    self.characters["animator"][character_id] = InBack(from_pos, to_pos, duration)
                case "elastic":
                    self.characters["animator"][character_id] = Elastic(from_pos, to_pos, duration)

        def hide_character(action: DialogueActionData) -> None:
            character_id = str(args["character_id"])
            self.characters["sprite"].pop(character_id)
            self.characters["pos"].pop(character_id)
            self.characters["animator"].pop(character_id)

        def set_highlight(action: DialogueActionData) -> None:
            character_id = str(args["character_id"])
            dim_others = bool(args["dim_others"])
            if dim_others:
                self.characters["is_highlighted"] = {
                    k: False for k, _ in self.characters["is_highlighted"].items()
                }
            if character_id != "":
                self.characters["is_highlighted"][character_id] = True

        def screen_shake(action: DialogueActionData) -> None:
            # TODO: Implement
            duration = float(args["duration"])  # type: ignore
            intensity = float(args["intensity"])  # type: ignore

        def prompt(action: DialogueActionData) -> str:
            # TODO: Implement
            options = args["options"]
            return ""

        match action.get("type"):
            case "show_text":
                show_text(action)
            case "set_background":
                self._reload_background()  # Automatically apply last background with curr_step_idx
            case "play_bgm":
                pass
            case "play_sfx":
                pass
            case "show_character":
                show_character(action)
            case "move_character":
                move_character(action)
            case "hide_character":
                hide_character(action)
            case "set_highlight":
                set_highlight(action)
            case "screen_shake":
                screen_shake(action)
            case "prompt":
                prompt(action)

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        if not text:
            return [""]

        lines: list[str] = []
        current = ""

        for ch in text:
            if ch == "\n":
                lines.append(current)
                current = ""
                continue

            candidate = current + ch
            w, _ = self.dialogue_font.size(candidate)
            if w <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = ch

        if current:
            lines.append(current)

        return lines

    def _relative_scale_to_pos(self, x_scale: float, y_scale: float) -> tuple[float, float]:
        # Center: (0.0, 0.0)
        # Range: -1.0 ~ 1.0
        # Right: X positive
        # Down: Y Positive

        w_mid, h_mid = (v // 2 for v in self.windows_size)
        return (w_mid * (1 + x_scale), h_mid * (1 + y_scale))
