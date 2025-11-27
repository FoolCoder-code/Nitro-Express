import os

from configparser import ConfigParser
from core.path_resolver import config_file_path

type ConfigValue = str | float | int | bool


WINDOW_TITLE = "Nitro Express"
SUPPORTED_RESOLUTIONS = (
    (1280, 720),
    (1360, 765),
    (1600, 900),
    (1920, 1080)
)
SUPPORTED_MAXIMUM_REFRESH_RATE = (
    60,
    120,
    144,
    240,
    360,
    1000
)
LANGUAGE_NAMES = {
    "en_us": "English",
    "zh_tw": "繁體中文",
}
SUPPORTED_LANGUAGE_CODES = tuple(LANGUAGE_NAMES.keys())
DEFAULT_LANGUAGE_CODE = SUPPORTED_LANGUAGE_CODES[0]

DEFAULT_CONFIG = {
    "General": {
        "language": DEFAULT_LANGUAGE_CODE,
        "resolution_width": f"{SUPPORTED_RESOLUTIONS[0]}".split(",")[0].strip("( )"),
        "resolution_height": f"{SUPPORTED_RESOLUTIONS[0]}".split(",")[1].strip("( )"),
        "max_refresh_rate": SUPPORTED_MAXIMUM_REFRESH_RATE[0]
    },
    "Volume": {
        "sfx": 50,
        "bgm": 50,
    },
    "Scene":{
        "text_display_speed": 50,
        "autoplay_mode_speed": 50,
        "skip_read_scenes": False
    }
}

def get_config_parser() -> ConfigParser:
    """
    Load and return the shared configuration parser, creating defaults if needed.

    :return ConfigParser: Parser of the config.ini file located in the root folder.
    """
    parser = ConfigParser()
    path = config_file_path()

    # Ensure a config file exists before attempting to read it.
    if not os.path.exists(path):
        parser.read_dict(DEFAULT_CONFIG)
        write_config(parser)

    parser.read(path, encoding="utf-8")

    return parser

def write_config(config: ConfigParser) -> None:
    """
    Write the provided mapping to disk. Used for defaults.
    :param config: Config Parser to be written to file.
    """
    with open(config_file_path(), "w", encoding="utf-8") as f:
        config.write(f)

if __name__ == "__main__":
    print("Configuration file is now set to default.")
    os.remove(config_file_path())
    get_config_parser()