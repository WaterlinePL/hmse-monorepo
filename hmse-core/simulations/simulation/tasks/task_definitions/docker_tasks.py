import logging
from concurrent.futures import ThreadPoolExecutor, wait

from config.deployment_config import docker
from hmse_utils.processing.hydrus import hydrus_utils
from simulations.projects.project_metadata import ProjectMetadata
from simulations.projects.simulation_mode import SimulationMode
from simulations.simulation.deployment.hydrus_docker_deployer import HydrusDockerDeployer
from simulations.simulation.deployment.modflow2005_docker_deployer import ModflowDockerDeployer
from simulations.simulation.simulation_enums import SimulationStageName
from simulations.simulation.tasks.simulation_tasks import SimulationTasks

__MAX_CONCURRENT_MODELS = 8

logger = logging.getLogger(__name__)


# Simulation tasks
@docker(identification=SimulationStageName.HYDRUS_SIMULATION)
def __hydrus_simulation(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching docker task for stage: {kwargs['stage_name']}")
    simulations = []
    if project_metadata.simulation_mode == SimulationMode.SIMPLE_COUPLING:
        hydrus_to_launch = hydrus_utils.get_used_hydrus_models(project_metadata.shapes_to_hydrus)
    else:
        hydrus_to_launch = hydrus_utils.get_compound_hydrus_ids_for_feedback_loop(project_metadata.shapes_to_hydrus)
        hydrus_to_launch = [compound_hydrus_id for _, compound_hydrus_id in hydrus_to_launch]

    with ThreadPoolExecutor(max_workers=__MAX_CONCURRENT_MODELS) as exe:
        for hydrus_id in hydrus_to_launch:
            sim = HydrusDockerDeployer(project_metadata.project_id, hydrus_id)
            sim.run_simulation_image()
            simulations.append(exe.submit(sim.wait_for_termination))
        # wait(simulations)


@docker(identification=SimulationStageName.HYDRUS_SIMULATION_WARMUP)
def __hydrus_simulation_warmup(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching docker task for stage: {kwargs['stage_name']}")
    SimulationTasks.hydrus_simulation(project_metadata)


@docker(identification=SimulationStageName.MODFLOW_SIMULATION)
def __modflow_simulation(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching docker task for stage: {kwargs['stage_name']}")
    deployer = ModflowDockerDeployer(
        project_metadata.project_id,
        project_metadata.modflow_metadata.modflow_id
    )
    deployer.run_simulation_image()
    deployer.wait_for_termination()
