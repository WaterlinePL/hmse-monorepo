from strenum import StrEnum


class SimulationCoreMode(StrEnum):
    MODFLOW_2005 = "modflow-2005"
    SEAWAT = "seawat"