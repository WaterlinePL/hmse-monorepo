import logging
import os
import subprocess
from typing import List

from config import app_config
from config.deployment_config import desktop, docker
from simulations import path_formatter
from hmse_utils.processing.data_passing_utils import \
    DataProcessingException
from hmse_utils.processing.hydrus import hydrus_utils
from hmse_utils.processing.local_fs_configuration import local_paths
from hmse_utils.processing.modflow import modflow_utils
from hmse_utils.processing.task_logic import configuration_tasks_logic, data_tasks_logic
from simulations.projects.project_metadata import ProjectMetadata
from simulations.projects.simulation_mode import SimulationMode
from simulations.simulation.simulation_enums import SimulationStageName
from simulations.simulation.simulation_error import SimulationError
from simulations.simulation.tasks.simulation_tasks import SimulationTasks

logger = logging.getLogger(__name__)


# Configuration tasks
@desktop(identification=SimulationStageName.INITIALIZATION)
@docker(identification=SimulationStageName.INITIALIZATION)
def __initialization(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    configuration_tasks_logic.local_files_initialization(project_metadata.project_id)


@desktop(identification=SimulationStageName.SAVE_REFERENCE_HYDRUS_MODELS)
@docker(identification=SimulationStageName.SAVE_REFERENCE_HYDRUS_MODELS)
def __save_reference_hydrus_models(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    configuration_tasks_logic.preserve_reference_hydrus_models(project_metadata.project_id)


@desktop(identification=SimulationStageName.OUTPUT_EXTRACTION)
@docker(identification=SimulationStageName.OUTPUT_EXTRACTION)
def __output_extraction_to_json(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    configuration_tasks_logic.extract_output_to_json(
        project_id=project_metadata.project_id,
        modflow_id=project_metadata.modflow_metadata.modflow_id
    )


@desktop(identification=SimulationStageName.CLEANUP)
@docker(identification=SimulationStageName.CLEANUP)
def __dummy_cleanup(project_metadata: ProjectMetadata, **kwargs):
    # Empty - we do not want to delete results that should be downloaded
    pass


@desktop(identification=SimulationStageName.INITIALIZE_NEW_ITERATION_FILES)
@docker(identification=SimulationStageName.INITIALIZE_NEW_ITERATION_FILES)
def __initialize_new_iteration_files(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    configuration_tasks_logic.initialize_feedback_iteration(
        project_id=project_metadata.project_id,
        modflow_id=project_metadata.modflow_metadata.modflow_id,
        spin_up=project_metadata.spin_up,
        shapes_to_hydrus=project_metadata.shapes_to_hydrus
    )


@desktop(identification=SimulationStageName.CREATE_PER_ZONE_HYDRUS_MODELS)
@docker(identification=SimulationStageName.CREATE_PER_ZONE_HYDRUS_MODELS)
def __create_per_zone_hydrus_models(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    configuration_tasks_logic.create_hydrus_models_for_zones(
        project_id=project_metadata.project_id,
        shapes_to_hydrus=project_metadata.shapes_to_hydrus
    )


@desktop(identification=SimulationStageName.ITERATION_PRE_CONFIGURATION)
@docker(identification=SimulationStageName.ITERATION_PRE_CONFIGURATION)
def __iteration_pre_configuration(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    configuration_tasks_logic.pre_configure_iteration(project_metadata.project_id)


@desktop(identification=SimulationStageName.FEEDBACK_SAVE_OUTPUT_ITERATION)
@docker(identification=SimulationStageName.FEEDBACK_SAVE_OUTPUT_ITERATION)
def __save_last_iteration(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    __iteration_pre_configuration(project_metadata, **kwargs)


# Data tasks
@desktop(identification=SimulationStageName.WEATHER_DATA_TRANSFER)
@docker(identification=SimulationStageName.WEATHER_DATA_TRANSFER)
def __weather_data_to_hydrus(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    try:
        data_tasks_logic.weather_data_transfer_to_hydrus(
            project_id=project_metadata.project_id,
            start_date=project_metadata.start_date,
            spin_up=project_metadata.spin_up,
            modflow_metadata=project_metadata.modflow_metadata,
            hydrus_to_weather=project_metadata.hydrus_to_weather,
            shapes_to_hydrus=project_metadata.shapes_to_hydrus
        )
    except DataProcessingException as e:
        raise SimulationError(description=str(e))


@desktop(identification=SimulationStageName.HYDRUS_TO_MODFLOW_DATA_PASSING)
@docker(identification=SimulationStageName.HYDRUS_TO_MODFLOW_DATA_PASSING)
def __hydrus_to_modflow(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    try:
        data_tasks_logic.transfer_data_from_hydrus_to_modflow(
            project_id=project_metadata.project_id,
            shapes_to_hydrus=project_metadata.shapes_to_hydrus,
            is_feedback_loop=project_metadata.simulation_mode == SimulationMode.WITH_FEEDBACK,
            modflow_metadata=project_metadata.modflow_metadata,
            spin_up=project_metadata.spin_up
        )
    except DataProcessingException as e:
        raise SimulationError(description=str(e))


@desktop(identification=SimulationStageName.MODFLOW_TO_HYDRUS_DATA_PASSING)
@docker(identification=SimulationStageName.MODFLOW_TO_HYDRUS_DATA_PASSING)
def __modflow_to_hydrus(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    data_tasks_logic.transfer_data_from_modflow_to_hydrus(
        project_id=project_metadata.project_id,
        shapes_to_hydrus=project_metadata.shapes_to_hydrus,
        modflow_metadata=project_metadata.modflow_metadata
    )


@desktop(identification=SimulationStageName.MODFLOW_INIT_CONDITION_TRANSFER_STEADY_STATE)
@docker(identification=SimulationStageName.MODFLOW_INIT_CONDITION_TRANSFER_STEADY_STATE)
def __modflow_init_condition_transfer_steady_state(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    SimulationTasks.modflow_simulation(project_metadata)
    data_tasks_logic.transfer_data_from_modflow_to_hydrus(
        project_id=project_metadata.project_id,
        shapes_to_hydrus=project_metadata.shapes_to_hydrus,
        modflow_metadata=project_metadata.modflow_metadata
    )


@desktop(identification=SimulationStageName.MODFLOW_INIT_CONDITION_TRANSFER_TRANSIENT)
@docker(identification=SimulationStageName.MODFLOW_INIT_CONDITION_TRANSFER_TRANSIENT)
def __modflow_init_condition_transfer_transient(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    data_tasks_logic.transfer_data_from_modflow_to_hydrus_init_transient(
        project_id=project_metadata.project_id,
        shapes_to_hydrus=project_metadata.shapes_to_hydrus,
        modflow_metadata=project_metadata.modflow_metadata
    )


# Simulation tasks
@desktop(identification=SimulationStageName.HYDRUS_SIMULATION)
def __hydrus_simulation(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    simulations = []
    if project_metadata.simulation_mode == SimulationMode.SIMPLE_COUPLING:
        hydrus_to_launch = hydrus_utils.get_used_hydrus_models(project_metadata.shapes_to_hydrus)
    else:
        hydrus_to_launch = hydrus_utils.get_compound_hydrus_ids_for_feedback_loop(project_metadata.shapes_to_hydrus)
        hydrus_to_launch = [compound_hydrus_id for _, compound_hydrus_id in hydrus_to_launch]

    for hydrus_id in hydrus_to_launch:
        model_path = local_paths.get_hydrus_model_path(project_metadata.project_id, hydrus_id, simulation_mode=True)
        hydrus_exec_path = path_formatter.convert_backslashes_to_slashes(
            app_config.get_config().hydrus_program_path)
        proc = __run_local_program(
            exec_path=hydrus_exec_path,
            args=[path_formatter.convert_backslashes_to_slashes(model_path)]
        )
        simulations.append(proc)

    for proc in simulations:
        proc.communicate(input="\n")  # Press enter to close program (blocking)


@desktop(identification=SimulationStageName.HYDRUS_SIMULATION_WARMUP)
def __hydrus_simulation_warmup(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    SimulationTasks.hydrus_simulation(project_metadata)


@desktop(identification=SimulationStageName.MODFLOW_SIMULATION)
def __modflow_simulation(project_metadata: ProjectMetadata, **kwargs) -> None:
    logger.debug(f"Launching local task for stage: {kwargs['stage_name']}")
    modflow_id = project_metadata.modflow_metadata.modflow_id
    modflow_path = local_paths.get_modflow_model_path(project_metadata.project_id, modflow_id, simulation_mode=True)

    current_dir = os.getcwd()
    modflow_exec_path = path_formatter.convert_backslashes_to_slashes(app_config.get_config().modflow_program_path)
    nam_file = modflow_utils.scan_for_modflow_file(modflow_path)

    os.chdir(modflow_path)
    proc = __run_local_program(
        exec_path=modflow_exec_path,
        args=[nam_file]
    )
    os.chdir(current_dir)
    proc.communicate(input="\n")  # Press enter to close program (blocking)


# Util functions
def __run_local_program(exec_path: str, args: List[str], log_handle=None):
    logger.debug(f"Running local executable: {exec_path} (args: {args})")
    return subprocess.Popen([exec_path, *args],
                            shell=True, text=True,
                            stdin=subprocess.PIPE, stdout=log_handle, stderr=log_handle)
