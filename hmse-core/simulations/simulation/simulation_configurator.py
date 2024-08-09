import logging
from typing import List

from config import deployment_config
from hmse_utils.processing.modflow.modflow_step import ModflowStepType
from simulations.projects.project_metadata import ProjectMetadata
from simulations.projects.simulation_mode import SimulationMode
from simulations.simulation.simulation_chapter import SimulationChapter


logger = logging.getLogger(__name__)

def configure_simulation(project_metadata: ProjectMetadata) -> 'Simulation':
    logger.info(f"Configuring simulation for project: {project_metadata.project_id}")
    sim_chapters = __chapters_from_metadata(project_metadata)
    logger.info(f"Simulation for project {project_metadata.project_id} has been configured "
                f"with following chapters: {sim_chapters}")
    return deployment_config.get_deployment_class(identification='simulation')(
        project_metadata=project_metadata,
        sim_chapters=sim_chapters,
    )


def __chapters_from_metadata(project_metadata: ProjectMetadata) -> List[SimulationChapter]:
    if project_metadata.simulation_mode == SimulationMode.SIMPLE_COUPLING:
        chapters = [SimulationChapter.SIMPLE_COUPLING]
    elif project_metadata.simulation_mode == SimulationMode.WITH_FEEDBACK:
        modflow_steps = project_metadata.modflow_metadata.steps_info
        starts_steady = modflow_steps[0].type == ModflowStepType.STEADY_STATE
        chapters = [SimulationChapter.FEEDBACK_WARMUP_STEADY_STATE
                    if starts_steady else SimulationChapter.FEEDBACK_WARMUP_TRANSIENT]
        chapters += [SimulationChapter.FEEDBACK_ITERATION for _ in modflow_steps[1:]]
        chapters.append(SimulationChapter.FEEDBACK_SIMULATION_FINALIZATION)
    else:
        raise KeyError("Unknown simulation mode!")

    return chapters
