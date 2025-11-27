import sys
import pygame

from core.config_manager import get_config_parser, WINDOW_TITLE
from core.scene.SceneManager import SceneManager
from core.scene.Titlescreen import Titlescreen


def main() -> None:
    # Initialize
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)

    config = get_config_parser()

    window_size = (
        config.getint("General", "resolution_width"),
        config.getint("General", "resolution_height")
    )
    max_refresh_rate = config.getint("General", "max_refresh_rate")

    window = pygame.display.set_mode(window_size)
    clock = pygame.time.Clock()

    scene_manager = SceneManager(window)
    scene_manager.stack_push(Titlescreen(scene_manager))

    # Main Loop
    while True:
        delta = clock.tick(max_refresh_rate) / 1000.0
        scene_manager.update(delta)
        pygame.display.flip()

        if scene_manager.events.quit:
            break

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
