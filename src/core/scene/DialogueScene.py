import pygame

from typing import Union, Type
from core.scene.EventState import EventState
from core.scene.SceneManager import SceneManager
from core.scene.Scene import Scene
from core.scene.DialogueLog import DialogueLog
from core.scene.DialogueStructure import DialogueSceneData, DialogueActionData
from core.scene.PromptScene import PromptScene
from core.ui.components.AnimatedGlowingButton import AnimatedGlowingButton
from core.ui.effects.CoordsAnimator import Linear, OutCubic, InCubic, OutBack, InBack, Elastic
from core.ui.effects.ScreenShake import ScreenShake
from core.ui.effects.Typewriter import Typewriter


class DialogueScene(Scene):
    def __init__(
            self,
            scene_manager: SceneManager,
            dialogue_data: DialogueSceneData,
            *,
            is_overlay: bool = False,
            is_exclusive: bool = True
        ):
        self.sm = scene_manager
        self.is_overlay = is_overlay
        self.is_exclusive = is_exclusive

        self.dialogue_data: DialogueSceneData = dialogue_data

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

        self._is_speaker_exist: bool = False

        self._dropdown_menu_toggled: bool = False

        self._auto_mode: bool = False
        self._auto_advance_timer: float = 0.0
        self._auto_advance_delay: float = 0.8 / self.config_cps_scale

        self._hide_mode: bool = False
        self._skip_mode: bool = False
        self._awaiting_overlays: list[Type[Scene]] = []
        self._bg_transition: dict[str, object] | None = None

        # UI Elements
        self.tw = Typewriter("", self.config_cps_scale)
        self.shake_controller = ScreenShake()
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
        self._awaiting_overlays = []

        self._execute_step(self._curr_step_idx)

    def leave(self) -> None:
        return

    def handle(self, ev: EventState) -> None:
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
                        self.dialogue_history.pop() # Prevent duplicated entry
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
        keyboard_event()
        mouse_event()

    def update(self, dt: float) -> None:
        # Screen Shake Effect
        self.shake_controller.update(dt)

        self._update_background_transition(dt)

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
        padding_right = self.rscale(140)
        max_width = w - dialogue_x - padding_right

        # Wrap
        wrapped_lines = self._wrap_text(self.tw.visible_text, max_width)

        # Save as Surfaces
        self._dialogue_lines = [
            self.dialogue_font.render(line, True, self.text_color) for line in wrapped_lines
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

        # Auto-advance once any awaited overlay scenes are dismissed
        if self._awaiting_overlays:
            awaited = tuple(self._awaiting_overlays)
            overlay_open = any(isinstance(scene, awaited) for scene in self.sm.scene_stack)
            if not overlay_open:
                self._awaiting_overlays = []
                self._continue_dialogue = True

        # Step
        self._advance_dialogue()

    def draw(self, surface: pygame.Surface) -> None:
        w, h = self.windows_size
        s_x, s_y = self.shake_controller.get_offset()

        # Background
        if self._bg_transition and self._bg_transition.get("type") == "fade":
            duration = max(float(self._bg_transition.get("duration", 0.0)), 1e-6) # type: ignore
            elapsed = float(self._bg_transition.get("elapsed", 0.0)) # type: ignore
            progress = max(0.0, min(1.0, elapsed / duration))

            from_bg = self._bg_transition.get("from")
            to_bg = self._bg_transition.get("to")
            if isinstance(from_bg, pygame.Surface):
                surface.blit(from_bg, (s_x, s_y))
            if isinstance(to_bg, pygame.Surface):
                alpha = int(255 * progress)
                to_bg.set_alpha(alpha)
                surface.blit(to_bg, (s_x, s_y))
                to_bg.set_alpha(None)
        else:
            surface.blit(self.background, (s_x, s_y)) # type: ignore

        # Character Sprites
        for k in self.characters["sprite"].keys():
            c_sprite = self.characters["sprite"][k]
            # Draw from rect center
            c_rect = c_sprite.get_rect()
            c_w, c_h = c_rect.width, c_rect.height
            pos = self.characters["pos"][k]

            c_pos = (pos[0] - c_w // 2 + s_x, pos[1] - c_h // 2 + s_y)
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

        # Dialogue Down Arrow
        if self.tw.is_finished:
            surface.blit(self.down_arrow_surface, (w * 0.93, h * 0.9))

        # Dialogue
        name_pos = (w * 0.05, h * 0.79)
        ctitle_pos = (w * 0.08, h * 0.86)

        surface.blit(self.name_surface, name_pos)
        surface.blit(self.ctitle_surface, ctitle_pos)

        # Lines of Text
        d_y = h * 0.8
        line_gap = self.rscale(4)
        padding_bottom = self.rscale(40)

        for line_surf in self._dialogue_lines:
            line_h = line_surf.get_height()

            # Stop when it's out of screen
            if d_y > h - padding_bottom:
                break

            if self._is_speaker_exist:
                surface.blit(line_surf, (w * 0.2, d_y))
            else:
                surface.blit(line_surf, (w * 0.15, d_y))
            d_y += line_h + line_gap

        if self._is_speaker_exist:
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
        self.down_arrow_surface = self.dialogue_font.render("﹀", True, self.text_color)

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

    def _find_latest_background(self) -> tuple[str | None, int]:
        def find_in_step(step_idx: int, last_action_idx: int | None = None) -> tuple[str | None, int]:
            curr_step = self.dialogue_data["steps"][step_idx]
            max_idx = last_action_idx if last_action_idx is not None else len(curr_step["actions"]) - 1
            if max_idx < 0:
                return (None, 0)

            for action in reversed(curr_step["actions"][:max_idx + 1]):
                if action["type"] != "set_background":
                    continue
                args = action.get("args", {})
                return args.get("filename"), int(args.get("blur", 0)) # type: ignore
            return (None, 0)

        for idx in reversed(range(self._curr_step_idx + 1)):
            # Only consider actions that have already run in the current step
            last_action_idx = self._curr_action_idx - 1 if idx == self._curr_step_idx else None
            filename, blur = find_in_step(idx, last_action_idx)
            if filename is not None:
                return filename, blur

        return (None, 0)

    def _load_background_surface(self, filename: str | None, blur: int = 0) -> pygame.Surface:
        if filename is None:
            background = pygame.Surface(self.windows_size)
            background.fill((0, 0, 0))
            return background

        background = pygame.transform.smoothscale(
            pygame.image.load(
                self.sm.get_illustration_iofile(filename)
            ).convert(),
            self.windows_size
        )

        if blur:
            background = pygame.transform.gaussian_blur(background, blur)

        return background

    def _apply_background(self, filename: str | None, blur: int = 0, transition: dict | None = None) -> None:
        new_background = self._load_background_surface(filename, blur)

        if not transition or not isinstance(transition, dict):
            self.background = new_background
            self._bg_transition = None
            return

        transition_type = transition.get("type", "instant")
        duration = float(transition.get("duration", 0.0))

        if transition_type == "fade" and duration > 0 and hasattr(self, "background"):
            self._bg_transition = {
                "type": "fade",
                "duration": duration,
                "elapsed": 0.0,
                "from": self.background,
                "to": new_background
            }
        else:
            self.background = new_background
            self._bg_transition = None

    def _reload_background(self) -> None:
        filename, blur = self._find_latest_background()
        self._apply_background(filename, blur)

    def _update_background_transition(self, dt: float) -> None:
        if not self._bg_transition:
            return

        duration = float(self._bg_transition.get("duration", 0.0)) # type: ignore
        elapsed = float(self._bg_transition.get("elapsed", 0.0)) + max(dt, 0.0) # type: ignore
        self._bg_transition["elapsed"] = elapsed

        if duration <= 0 or elapsed >= duration:
            # Finish transition and commit new background
            self.background = self._bg_transition["to"]  # type: ignore
            self._bg_transition = None

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

        # Skip until step ends
        # self._skip_mode = False
        return True

    def _execute_action(self, action: DialogueActionData) -> None:
        args = action.get("args", {})

        def show_text() -> None:
            speaker_name = args["speaker_name"]
            speaker_title = args["speaker_title"]
            full_text = args["text"]

            self._is_speaker_exist = bool(speaker_name or speaker_title)

            self.name_surface = self.name_font.render(speaker_name, True, self.text_color)  # type: ignore
            self.ctitle_surface = self.ctitle_font.render(speaker_title, True, self.text_color)  # type: ignore
            self.tw.reset(full_text)  # type: ignore
            self.dialogue_history.append((speaker_name, full_text))  # type: ignore

        def play_bgm() -> None:
            pass

        def play_sfx() -> None:
            pass

        def show_character() -> None:
            character_id = str(args["character_id"])
            pos = self._relative_scale_to_pos(float(args["x"]), float(args["y"]))  # type: ignore
            self.characters["pos"][character_id] = pos

        def move_character() -> None:
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

        def hide_character() -> None:
            character_id = str(args["character_id"])
            self.characters["sprite"].pop(character_id)
            self.characters["pos"].pop(character_id)
            self.characters["animator"].pop(character_id)

        def set_highlight() -> None:
            character_id = str(args["character_id"])
            dim_others = bool(args["dim_others"])
            if dim_others:
                self.characters["is_highlighted"] = {
                    k: False for k, _ in self.characters["is_highlighted"].items()
                }
            if character_id != "":
                self.characters["is_highlighted"][character_id] = True

        def screen_shake() -> None:
            duration = float(args["duration"]) # type: ignore
            intensity = float(args["intensity"]) # type: ignore
            freq = int(args["frequency"]) # type: ignore
            infinite = bool(args["infinite"])
            self.shake_controller.start(duration, intensity, freq, infinite)

        def prompt() -> None:
            flag_key = str(args["id"])
            prompt_label = str(args["message"])
            options = list(args["options"]) # type: ignore

            option_labels = []
            option_values = []
            for option in options:
                option_labels.append(option["message"])
                option_values.append(option["flag_value"])

            self.sm.stack_push(PromptScene(
                self.sm,
                prompt_label,
                flag_key,
                option_labels,
                option_values,
                "title_background"
            ))
            # Register overlays that should resume flow when dismissed (extendable list)
            self._awaiting_overlays = [PromptScene]

        def change_dialogue_scene() -> None:
            for package in args:

                scene_id = str(package["scene_id"]) # type: ignore
                required_g_flags = dict(package["required_g_flags"]) # type: ignore

                # Check Flags
                for k, v in required_g_flags.items():
                    if self.sm.g_flags.get(k, "") != v:
                        return

                # Switch Scenes
                self.sm.switch(DialogueScene(
                    self.sm,
                    self.sm.get_scene_data(scene_id)
                ))
                return

        match action.get("type"):
            case "show_text":
                show_text()
            case "set_background":
                self._apply_background(
                    args.get("filename"), # type: ignore
                    int(args.get("blur", 0)), # type: ignore
                    args.get("transition") # type: ignore
                )
            case "play_bgm":
                pass
            case "play_sfx":
                pass
            case "show_character":
                show_character()
            case "move_character":
                move_character()
            case "hide_character":
                hide_character()
            case "set_highlight":
                set_highlight()
            case "screen_shake":
                screen_shake()
            case "prompt":
                prompt()
            case "change_dialogue_scene":
                change_dialogue_scene()

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
