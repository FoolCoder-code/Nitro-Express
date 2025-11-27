import os
import json
import zlib
import base64

from collections.abc import Mapping
from typing import Any
from core.path_resolver import locale_dir

type LangNode = str | LangDict
type LangDict = dict[str, LangNode]


class LangData(dict[str, LangNode]):
    """Nested language dictionary with helper methods."""

    @classmethod
    def from_pak(cls, lang_code: str) -> "LangData":
        """
        Load encoded .paks with the given language code and return LangData.

        :param lang_code: e.g. 'zh_tw', 'en_us'
        :return: LangData (nested dictionary of UI texts).
        """
        pak_path = locale_dir(f"{lang_code}.pak")

        if not os.path.exists(pak_path):
            raise FileNotFoundError(
                f"Can't find asset {lang_code}.pak.\nPlease check file integrity."
            )

        # No try-except for language .paks are necessary
        with open(pak_path, "rb") as f:
            encoded = f.read()

        decoded = zlib.decompress(base64.b64decode(encoded)).decode("utf-8")
        raw = json.loads(decoded)

        if not isinstance(raw, dict):
            raise ValueError("Language pak root must be a dict")

        def _validate(node: Any) -> LangNode:
            if isinstance(node, str):
                return node
            if isinstance(node, dict):
                return {str(k): _validate(v) for k, v in node.items()}
            raise TypeError(
                f"Invalid value in language pak: {node!r} "
                "(expected str or dict[str, ...])"
            )

        validated: LangDict = {str(k): _validate(v) for k, v in raw.items()}
        return cls(validated)

    def get_str(self, *path: str) -> str:
        """
        Get a leaf string at the given path, e.g. ["menu", "title"].
        Raises TypeError if the leaf is not a string.

        :param path: Path to the key.
        :return str: Value of the key.
        """
        cur: LangNode = self
        for key in path:
            if not isinstance(cur, Mapping):
                raise TypeError(f"Expected dict at {key=}, got {type(cur)!r}")
            cur = cur[key]

        if not isinstance(cur, str):
            raise TypeError("Expected str at leaf")
        return cur

    def get_map(self, *path: str) -> LangDict:
        """
        Get a nested dict at the given path.
        Raises TypeError if the leaf is not a dict-like mapping.

        :param path: Path to the key of the dictionary
        :return LangDict: The target dictionary
        """
        cur: LangNode = self
        for key in path:
            if not isinstance(cur, Mapping):
                raise TypeError(f"Expected dict at {key=}, got {type(cur)!r}")
            cur = cur[key]

        if not isinstance(cur, dict):
            raise TypeError("Expected nested dict at leaf")
        return cur