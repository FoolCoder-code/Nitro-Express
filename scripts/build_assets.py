import sys
import datetime
import json
import zlib
import base64
from pathlib import Path

# Make sure we can import helpers from src/core when running this utility.
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from core.path_resolver import assets_root, asset_font, ensure_dir, locale_dir # noqa: E402

corresponding_font = {
    "en_us": "CactusClassicalSerif-Regular.ttf",
    "zh_tw": "CactusClassicalSerif-Regular.ttf"
}

LANG_DIR = locale_dir()
ensure_dir(LANG_DIR)

# Locales & Font
for lang_path in LANG_DIR.glob("*.json"):
    lang_code = lang_path.stem
    with lang_path.open("r", encoding="utf-8") as reader:
        data = json.load(reader)
        data["font_path"] = str(asset_font(corresponding_font[lang_code]))
        compressed = base64.b64encode(zlib.compress(json.dumps(data, ensure_ascii=False).encode("utf-8")))
        output_path = ensure_dir(lang_path.with_suffix(".pak"))
        with output_path.open("wb") as f:
            f.write(compressed)

# Assets
for foldername, filetype in zip(
        ["illustration", "sprite", "scene"],
        ["png", "png", "json"]
    ):
    pak_raw_data = {
        "category": foldername,
        "built_at": datetime.datetime.now().isoformat(),

        "header": {
            "filetype": filetype,
            "count": 0,
        },
        "entries": {}
    }

    assets_sub_dir = assets_root() / foldername

    for asset_path in assets_sub_dir.glob(f"*.{filetype}"):
        with asset_path.open("rb") as reader:
            pak_raw_data["entries"][asset_path.stem] = {
                "filename": asset_path.name,
                "encoded_string": base64.b64encode(reader.read()).decode("ascii")
            }
            pak_raw_data["header"]["count"] = pak_raw_data["header"].get("count", 0) + 1

    with open(assets_root() / f"{foldername}.pak", "wb") as writer:
        writer.write(
            base64.b64encode(
                zlib.compress(
                    json.dumps(
                        pak_raw_data,
                        separators=(",", ":")).encode("utf-8"),
                        level=9
                )
            )
        )