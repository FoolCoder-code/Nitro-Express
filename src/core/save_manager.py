import os
import base64
import json
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from core.path_resolver import ensure_dir, userdata_dir


class SaveDict(TypedDict):
    Savetime: datetime
    Day: int
    Slot_msg: str


_SAVE_DIR: Path = userdata_dir("sav")
_ENCRYPTION_KEY = b"nitro-express-save"


def _xor_bytes(data: bytes) -> bytes:
    """Simple XOR cipher using the static key."""
    key_len = len(_ENCRYPTION_KEY)
    return bytes(b ^ _ENCRYPTION_KEY[i % key_len] for i, b in enumerate(data))


def _encrypt(payload: bytes) -> bytes:
    encrypted = _xor_bytes(payload)
    return base64.urlsafe_b64encode(encrypted)


def _decrypt(payload: bytes) -> bytes:
    decoded = base64.urlsafe_b64decode(payload)
    return _xor_bytes(decoded)


def _save_path(filename_no_ext: str) -> Path:
    ensure_dir(_SAVE_DIR)
    return _SAVE_DIR / f"{filename_no_ext}.sav"


def read_save_file(slot: int) -> SaveDict:
    """
    Read and decrypt the save file for the given slot.
    Raises FileNotFoundError if the slot does not exist.
    """
    path = _save_path(f"savefile{slot}")
    data = json.loads(_decrypt(path.read_bytes()).decode("utf-8"))

    return SaveDict(
        Savetime=datetime.fromisoformat(data["Savetime"]),
        Day=int(data["Day"]),
        Slot_msg=str(data["Slot_msg"]),
    )


def write_save_file(slot: int, data: SaveDict) -> None:
    """
    Encrypt and write the save file for the given slot.
    """
    path = _save_path(f"savefile{slot}")

    serializable = {
        "Savetime": data["Savetime"].isoformat(),
        "Day": data["Day"],
        "Slot_msg": data["Slot_msg"],
    }

    payload = json.dumps(serializable, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    path.write_bytes(_encrypt(payload))

def remove_save_file(slot: int) -> None:
    """
    Remove the save file for the given slot.
    """
    os.remove(_save_path(f"savefile{slot}"))

def read_global_save_file() -> dict[str, int]:
    """
    Read and decrypt the global save file.
    Raises FileNotFoundError if the slot does not exist.
    """
    path = _save_path("global")

    return json.loads(_decrypt(path.read_bytes()).decode("utf-8"))


def write_global_save_file(data: dict[int, int]) -> None:
    """
    Encrypt and write the global save file.
    """
    path = _save_path("global")

    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    path.write_bytes(_encrypt(payload))