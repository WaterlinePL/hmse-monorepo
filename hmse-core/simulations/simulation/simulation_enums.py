from dataclasses import dataclass
from enum import auto
from typing import Optional

from strenum import StrEnum


class SimulationStageStatus(StrEnum):
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    ERROR = auto()

    def is_finished(self):
        return self == SimulationStageStatus.SUCCESS or self == SimulationStageStatus.ERROR


class SimulationStageName(StrEnum):
    INITIALIZATION = auto()
    WEATHER_DATA_TRANSFER = auto()
    HYDRUS_SIMULATION = auto()
    HYDRUS_SIMULATION_WARMUP = auto()
    HYDRUS_TO_MODFLOW_DATA_PASSING = auto()
    MODFLOW_SIMULATION = auto()
    OUTPUT_EXTRACTION = auto()
    CLEANUP = auto()

    INITIALIZE_NEW_ITERATION_FILES = auto()
    SAVE_REFERENCE_HYDRUS_MODELS = auto()
    CREATE_PER_ZONE_HYDRUS_MODELS = auto()

    MODFLOW_TO_HYDRUS_DATA_PASSING = auto()
    MODFLOW_INIT_CONDITION_TRANSFER_STEADY_STATE = auto()
    MODFLOW_INIT_CONDITION_TRANSFER_TRANSIENT = auto()

    ITERATION_PRE_CONFIGURATION = auto()
    FEEDBACK_SAVE_OUTPUT_ITERATION = auto()

    def get_as_id(self) -> str:
        return self.lower().replace('_', ' ').title().replace(' ', '')

    def get_name(self) -> str:
        return {
            SimulationStageName.INITIALIZATION: "Simulation initialization",
            SimulationStageName.WEATHER_DATA_TRANSFER: "Applying weather data to Hydrus models",
            SimulationStageName.HYDRUS_SIMULATION: "Hydrus simulations",
            SimulationStageName.HYDRUS_SIMULATION_WARMUP: "Hydrus simulations warmup",
            SimulationStageName.HYDRUS_TO_MODFLOW_DATA_PASSING: "Passing data from Hydrus to Modflow",
            SimulationStageName.MODFLOW_SIMULATION: "Modflow simulation",
            SimulationStageName.OUTPUT_EXTRACTION: "Exporting output",
            SimulationStageName.CLEANUP: "Cleaning up after simulation",
            SimulationStageName.INITIALIZE_NEW_ITERATION_FILES: "Initializing files for new iteration",
            SimulationStageName.CREATE_PER_ZONE_HYDRUS_MODELS: "Creating per zone Hydrus models",
            SimulationStageName.MODFLOW_TO_HYDRUS_DATA_PASSING: "Passing data from Modflow to Hydrus",
            SimulationStageName.ITERATION_PRE_CONFIGURATION: "Copying iteration files to new directory",
            SimulationStageName.FEEDBACK_SAVE_OUTPUT_ITERATION: "Saving last iteration files",
            SimulationStageName.SAVE_REFERENCE_HYDRUS_MODELS: "Creating Hydrus reference models",
            SimulationStageName.MODFLOW_INIT_CONDITION_TRANSFER_STEADY_STATE: "Modflow warmup (steady state simulation)"
                                                                              " and zones depth transfer to Hydrus",
            SimulationStageName.MODFLOW_INIT_CONDITION_TRANSFER_TRANSIENT: "Modflow zones depth transfer to Hydrus "
                                                                           "(BAS file)",
        }[self]


@dataclass
class SimulationStage:
    name: SimulationStageName
    status: SimulationStageStatus
    error: Optional[str] = None
