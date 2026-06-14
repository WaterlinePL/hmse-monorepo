from dataclasses import dataclass
from enum import auto

from dataclasses_json import dataclass_json
from strenum import StrEnum

from simulations.projects.typing_help import ShapeColor


class ShapeMode(StrEnum):
    INACTIVE = auto()
    RECHARGE = auto()
    SOLUTE = auto()

@dataclass_json
@dataclass
class ShapeMetadata:
    color: ShapeColor
    shape_mode: ShapeMode = ShapeMode.RECHARGE
