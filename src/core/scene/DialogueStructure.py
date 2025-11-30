from typing import TypedDict

class DialogueCharacterData(TypedDict):
    id: str
    sprite_filename: str
    scale: float
    default_layer: int

class DialogueActionData(TypedDict):
    type: str
    args: dict[str, str | int | float | bool | dict[str, str]]

class DialogueStepData(TypedDict):
    id: str
    actions: list[DialogueActionData]

class DialogueSceneData(TypedDict):
    characters: list[DialogueCharacterData]
    steps: list[DialogueStepData]