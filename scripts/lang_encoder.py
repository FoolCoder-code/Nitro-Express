import json
import zlib
import base64
from pathlib import Path
import sys

# Make sure we can import helpers from src/core when running this utility.
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from core.path_resolver import asset_font, ensure_dir, locale_dir  # noqa: E402

corresponding_font = {
    "en_us": "CactusClassicalSerif-Regular.ttf",
    "zh_tw": "CactusClassicalSerif-Regular.ttf"
}

LANG_DIR = locale_dir()
ensure_dir(LANG_DIR)

for lang_path in LANG_DIR.glob("*.json"):
    lang_code = lang_path.stem
    with lang_path.open("r", encoding="utf-8") as reader:
        data = json.load(reader)
        data["font_path"] = str(asset_font(corresponding_font[lang_code]))
        compressed = base64.b64encode(zlib.compress(json.dumps(data, ensure_ascii=False).encode("utf-8")))
        output_path = ensure_dir(lang_path.with_suffix(".pak"))
        with output_path.open("wb") as f:
            f.write(compressed)
