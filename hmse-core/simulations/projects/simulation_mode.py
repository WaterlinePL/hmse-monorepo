from enum import auto

from strenum import StrEnum


class SimulationMode(StrEnum):
    SIMPLE_COUPLING = auto()
    WITH_FEEDBACK = auto()
    SIMPLE_COUPLING_MT3DMS = auto()

    def is_simple(self) -> bool:
        return self in [SimulationMode.SIMPLE_COUPLING, SimulationMode.SIMPLE_COUPLING_MT3DMS]
