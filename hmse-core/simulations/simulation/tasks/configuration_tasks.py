from config import deployment_config
from simulations.projects.project_metadata import ProjectMetadata
from simulations.simulation.simulation_enums import SimulationStageName
from simulations.simulation.tasks.hmse_task import hmse_task


class ConfigurationTasks:

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.INITIALIZATION)
    def initialization(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.INITIALIZATION)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.SAVE_REFERENCE_HYDRUS_MODELS)
    def save_reference_hydrus_models(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.SAVE_REFERENCE_HYDRUS_MODELS)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.OUTPUT_EXTRACTION)
    def output_extraction_to_json(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.OUTPUT_EXTRACTION)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.CLEANUP)
    def cleanup(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.CLEANUP)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.INITIALIZE_NEW_ITERATION_FILES)
    def initialize_new_iteration_files(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.INITIALIZE_NEW_ITERATION_FILES)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.CREATE_PER_ZONE_HYDRUS_MODELS)
    def create_per_zone_hydrus_models(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.CREATE_PER_ZONE_HYDRUS_MODELS)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.ITERATION_PRE_CONFIGURATION)
    def iteration_pre_configuration(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.ITERATION_PRE_CONFIGURATION)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.FEEDBACK_SAVE_OUTPUT_ITERATION)
    def save_last_iteration(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.FEEDBACK_SAVE_OUTPUT_ITERATION)(
            project_metadata,
            **kwargs
        )
