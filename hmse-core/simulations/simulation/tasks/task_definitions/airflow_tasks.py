import logging

from config.deployment_config import k8s
from simulations.projects import project_service
from simulations.projects.project_metadata import ProjectMetadata
from simulations.simulation.airflow import airflow_simulation_service
from simulations.simulation.simulation_enums import SimulationStageName

logger = logging.getLogger(__name__)


# Configuration tasks
@k8s(identification=SimulationStageName.INITIALIZATION)
def __initialization(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_mapped_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.SAVE_REFERENCE_HYDRUS_MODELS)
def __save_reference_hydrus_models(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.OUTPUT_EXTRACTION)
def __output_extraction_to_json(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.INITIALIZE_NEW_ITERATION_FILES)
def __initialize_new_iteration_files(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.CREATE_PER_ZONE_HYDRUS_MODELS)
def __create_per_zone_hydrus_models(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.ITERATION_PRE_CONFIGURATION)
def __iteration_pre_configuration(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.FEEDBACK_SAVE_OUTPUT_ITERATION)
def __save_last_iteration(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.CLEANUP)
def __cleanup(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_airflow_job(**kwargs)
    project_metadata.finished = True
    project_service.save_or_update_metadata(project_metadata)


# Data tasks
@k8s(identification=SimulationStageName.WEATHER_DATA_TRANSFER)
def __weather_data_to_hydrus(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.HYDRUS_TO_MODFLOW_DATA_PASSING)
def __hydrus_to_modflow(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.MODFLOW_TO_HYDRUS_DATA_PASSING)
def __modflow_to_hydrus(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.MODFLOW_INIT_CONDITION_TRANSFER_STEADY_STATE)
def __modflow_init_condition_transfer_steady_state(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.MODFLOW_INIT_CONDITION_TRANSFER_TRANSIENT)
def __modflow_init_condition_transfer_transient(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_airflow_job(**kwargs)


# Simulation tasks
@k8s(identification=SimulationStageName.HYDRUS_SIMULATION)
def hydrus_simulation(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_mapped_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.HYDRUS_SIMULATION_WARMUP)
def hydrus_simulation_warmup(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_mapped_airflow_job(**kwargs)


@k8s(identification=SimulationStageName.MODFLOW_SIMULATION)
def modflow_simulation(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching airflow task for stage: {kwargs['stage_name']}")
    __monitor_mapped_airflow_job(**kwargs)


# Util functions
def __monitor_airflow_job(**kwargs):
    airflow_simulation_service.get().monitor_job(
        dag_run_id=kwargs["dag_run_id"],
        chapter_name=kwargs["chapter_name"],
        stage_name=kwargs["stage_name"]
    )


def __monitor_mapped_airflow_job(**kwargs):
    airflow_simulation_service.get().monitor_mapped_job(
        dag_run_id=kwargs["dag_run_id"],
        chapter_name=kwargs["chapter_name"],
        stage_name=kwargs["stage_name"]
    )
