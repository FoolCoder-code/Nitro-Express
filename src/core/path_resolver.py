import sys

from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def src_root() -> Path:
    # For after packed with Pyinstaller, etc...： Use _MEIPASS or Executable dir
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", Path(sys.executable).parent)
        return Path(base).resolve()

    # For developing: Use src dir
    return Path(__file__).resolve().parent.parent

@lru_cache(maxsize=1)
def config_file_path() -> Path:
    return src_root() / "config.ini"

@lru_cache(maxsize=1)
def assets_root() -> Path:
    return src_root() / "assets"

def asset_font(*sub) -> Path:
    return assets_root().joinpath("font", *sub)

def asset_illustration(*sub) -> Path:
    return assets_root().joinpath("illustration", *sub)

def asset_sprite(*sub) -> Path:
    return assets_root().joinpath("sprite", *sub)

def asset_scene(*sub) -> Path:
    return assets_root().joinpath("scene", *sub)

@lru_cache(maxsize=1)
def core_root() -> Path:
    return src_root() / "core"

def core_locale(*sub) -> Path:
    return core_root().joinpath("locale", *sub)

def core_scene(*sub) -> Path:
    return core_root().joinpath("scene", *sub)

def core_ui(*sub) -> Path:
    return core_root().joinpath("ui", *sub)

@lru_cache(maxsize=1)
def locale_root() -> Path:
    return src_root() / "locale"

def locale_dir(*sub) -> Path:
    return locale_root().joinpath(*sub)

@lru_cache(maxsize=1)
def userdata_root() -> Path:
    return src_root() / "userdata"

def userdata_dir(*sub) -> Path:
    return userdata_root().joinpath(*sub)

def ensure_dir(path) -> Path:
    if path.suffix:
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)
    return path
