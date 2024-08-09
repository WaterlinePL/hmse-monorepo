import logging
from dataclasses import dataclass, field
from threading import Thread
from typing import Dict, List

from simulations.projects import project_service
from simulations.projects.project_metadata import ProjectMetadata
from simulations.projects.typing_help import ProjectID
from simulations.simulation import simulation_configurator
from simulations.simulation.simulation_status import ChapterStatus

__INSTANCE = None

logger = logging.getLogger(__name__)


@dataclass
class SimulationService:
    simulations: Dict[ProjectID, 'Simulation'] = field(default_factory=dict)

    def run_simulation(self, project_metadata: ProjectMetadata) -> None:
        logger.info(f"Starting simulation for project: {project_metadata.project_id}")

        simulation = simulation_configurator.configure_simulation(project_metadata)
        self.register_simulation_if_necessary(simulation)

        project_metadata.finished = False
        project_service.save_or_update_metadata(project_metadata)

        # Run simulation in background
        thread = Thread(target=simulation.run_simulation)
        thread.start()

    def check_simulation_status(self, project_id: ProjectID) -> List[ChapterStatus]:
        """
        Return status of each step in particular simulation.
        @param project_id: ID of the simulated project to check
        @return: Status of hydrus stage, passing stage and modflow stage (in this exact order)
        """
        logger.debug(f"Checking simulation status for project: {project_id}")
        all_chapter_statuses = self.simulations[project_id].get_simulation_status()
        if all_chapter_statuses[-1].get_stages_statuses()[-1].status.is_finished():
            del self.simulations[project_id]
        return all_chapter_statuses

    def register_simulation_if_necessary(self, simulation):
        logger.debug(f"Registering simulation for project: {simulation.project_metadata.project_id}")
        self.simulations[simulation.project_metadata.project_id] = simulation


def get() -> SimulationService:
    global __INSTANCE
    __INSTANCE = __INSTANCE or SimulationService()
    return __INSTANCE
