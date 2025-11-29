import os
import io
import datetime
import json
import zlib
import base64

from typing import Union, TypedDict, NotRequired
from core.path_resolver import assets_root


class AssetPak(TypedDict):
    category: str
    built_at: datetime.datetime
    header: dict[str, Union[str, int]]
    entries: dict[str, NotRequired[dict[str, str]]]


def read_illustration_pak() -> AssetPak:
    pak_path = assets_root() / "illustration.pak"

    if not os.path.exists(pak_path):
        raise FileExistsError

    with pak_path.open("rb") as reader:
        pak_data = json.loads(
            zlib.decompress(
                base64.b64decode(reader.read())
            ),
        )
    return AssetPak(
        category = pak_data["category"],
        built_at = datetime.datetime.now().fromisoformat(pak_data["built_at"]),
        header = {
            "filetype": pak_data["header"]["filetype"],
            "count": int(pak_data["header"]["count"])
        },
        entries = {
            pk: pv for pk, pv in pak_data["entries"].items()
        }
    )

def read_sprite_pak() -> AssetPak:
    pak_path = assets_root() / "sprite.pak"

    if not os.path.exists(pak_path):
        raise FileExistsError

    with pak_path.open("rb") as reader:
        pak_data = json.loads(
            zlib.decompress(
                base64.b64decode(reader.read())
            ),
        )
    return AssetPak(
        category = pak_data["category"],
        built_at = datetime.datetime.now().fromisoformat(pak_data["built_at"]),
        header = {
            "filetype": pak_data["header"]["filetype"],
            "count": int(pak_data["header"]["count"])
        },
        entries = {
            pk: pv for pk, pv in pak_data["entries"].items()
        }
    )


def read_scene_pak() -> AssetPak:
    pak_path = assets_root() / "scene.pak"

    if not os.path.exists(pak_path):
        raise FileExistsError

    with pak_path.open("rb") as reader:
        pak_data = json.loads(
            zlib.decompress(
                base64.b64decode(reader.read())
            ),
        )
    return AssetPak(
        category = pak_data["category"],
        built_at = datetime.datetime.now().fromisoformat(pak_data["built_at"]),
        header = {
            "filetype": pak_data["header"]["filetype"],
            "count": int(pak_data["header"]["count"])
        },
        entries = {
            pk: pv for pk, pv in pak_data["entries"].items()
        }
    )

def unpack_encoded_string(encoded_string: str) -> bytes:
    return base64.b64decode(encoded_string)