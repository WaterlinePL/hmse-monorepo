import copy
import logging
from dataclasses import dataclass
from enum import auto
from typing import List, Callable, Set

from strenum import StrEnum

from simulations.simulation.tasks.configuration_tasks import ConfigurationTasks
from simulations.simulation.tasks.data_tasks import DataTasks
from simulations.simulation.tasks.simulation_tasks import SimulationTasks
from simulations.projects.project_metadata import ProjectMetadata

logger = logging.getLogger(__name__)


@dataclass
class SimulationChapter(StrEnum):
    SIMPLE_COUPLING = auto()
    FEEDBACK_WARMUP_STEADY_STATE = auto()
    FEEDBACK_WARMUP_TRANSIENT = auto()
    FEEDBACK_ITERATION = auto()
    FEEDBACK_SIMULATION_FINALIZATION = auto()

    def get_simulation_tasks(self, metadata: ProjectMetadata) -> List[Callable[[ProjectMetadata], None]]:
        tasks = copy.deepcopy(CHAPTER_TO_TASK_MAPPING[self])
        steps_to_skip = SimulationChapter.__get_steps_to_skip(tasks, metadata)
        final_tasks = [t for t in tasks if t not in steps_to_skip]
        logger.debug(f"Tasks for chapter {self}: {final_tasks} (skipped {steps_to_skip})")
        return final_tasks

    def get_name(self) -> str:
        return self.lower().replace('_', ' ').title()

    def get_as_id(self) -> str:
        return self.get_name().replace(' ', '')

    def get_name_snake_case(self):
        return self.lower()

    @staticmethod
    def __get_steps_to_skip(tasks: List[Callable[[ProjectMetadata], None]],
                            metadata: ProjectMetadata) -> Set[Callable[[ProjectMetadata], None]]:
        to_skip = set()

        is_hydrus_used = len(metadata.shapes_to_hydrus) > 0
        is_weather_transfer_used = len(metadata.hydrus_to_weather) > 0

        if not is_hydrus_used:
            if DataTasks.weather_data_to_hydrus in tasks:
                to_skip.add(DataTasks.weather_data_to_hydrus)

            if SimulationTasks.hydrus_simulation in tasks:
                to_skip.add(SimulationTasks.hydrus_simulation)

            if DataTasks.hydrus_to_modflow in tasks:
                to_skip.add(DataTasks.hydrus_to_modflow)

        if is_hydrus_used and not is_weather_transfer_used and DataTasks.weather_data_to_hydrus in tasks:
            to_skip.add(DataTasks.weather_data_to_hydrus)

        return to_skip

    def __hash__(self):
        return str(self).__hash__()


__SIMPLE_COUPLING_TASKS = [
    ConfigurationTasks.initialization,
    DataTasks.weather_data_to_hydrus,
    SimulationTasks.hydrus_simulation,
    DataTasks.hydrus_to_modflow,
    SimulationTasks.modflow_simulation,
    ConfigurationTasks.output_extraction_to_json,
    ConfigurationTasks.cleanup
]

__FEEDBACK_WARMUP_STEADY_STATE_TASKS = [
    ConfigurationTasks.initialization,
    DataTasks.weather_data_to_hydrus,
    ConfigurationTasks.save_reference_hydrus_models,
    ConfigurationTasks.create_per_zone_hydrus_models,
    ConfigurationTasks.initialize_new_iteration_files,
    DataTasks.modflow_init_condition_transfer_steady_state,
    SimulationTasks.hydrus_simulation_warmup
]

__FEEDBACK_WARMUP_TRANSIENT_TASKS = [
    ConfigurationTasks.initialization,
    DataTasks.weather_data_to_hydrus,
    ConfigurationTasks.save_reference_hydrus_models,
    ConfigurationTasks.create_per_zone_hydrus_models,
    ConfigurationTasks.initialize_new_iteration_files,
    DataTasks.modflow_init_condition_transfer_transient,
    SimulationTasks.hydrus_simulation_warmup
]

__FEEDBACK_ITERATION_TASKS = [
    ConfigurationTasks.iteration_pre_configuration,
    ConfigurationTasks.initialize_new_iteration_files,
    DataTasks.modflow_to_hydrus,
    SimulationTasks.hydrus_simulation,
    DataTasks.hydrus_to_modflow,
    SimulationTasks.modflow_simulation
]

__FEEDBACK_SIMULATION_FINALIZATION = [
    ConfigurationTasks.iteration_pre_configuration,
    ConfigurationTasks.output_extraction_to_json,
    ConfigurationTasks.cleanup
]

CHAPTER_TO_TASK_MAPPING = {
    SimulationChapter.SIMPLE_COUPLING: __SIMPLE_COUPLING_TASKS,
    SimulationChapter.FEEDBACK_WARMUP_STEADY_STATE: __FEEDBACK_WARMUP_STEADY_STATE_TASKS,
    SimulationChapter.FEEDBACK_WARMUP_TRANSIENT: __FEEDBACK_WARMUP_TRANSIENT_TASKS,
    SimulationChapter.FEEDBACK_ITERATION: __FEEDBACK_ITERATION_TASKS,
    SimulationChapter.FEEDBACK_SIMULATION_FINALIZATION: __FEEDBACK_SIMULATION_FINALIZATION
}
