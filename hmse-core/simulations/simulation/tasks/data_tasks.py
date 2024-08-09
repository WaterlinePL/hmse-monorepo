from config import deployment_config
from simulations.projects.project_metadata import ProjectMetadata
from simulations.simulation.simulation_enums import SimulationStageName
from simulations.simulation.tasks.hmse_task import hmse_task


class DataTasks:

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.WEATHER_DATA_TRANSFER)
    def weather_data_to_hydrus(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.WEATHER_DATA_TRANSFER)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.HYDRUS_TO_MODFLOW_DATA_PASSING)
    def hydrus_to_modflow(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.HYDRUS_TO_MODFLOW_DATA_PASSING)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.MODFLOW_TO_HYDRUS_DATA_PASSING)
    def modflow_to_hydrus(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.MODFLOW_TO_HYDRUS_DATA_PASSING)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.MODFLOW_INIT_CONDITION_TRANSFER_STEADY_STATE)
    def modflow_init_condition_transfer_steady_state(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.MODFLOW_INIT_CONDITION_TRANSFER_STEADY_STATE)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.MODFLOW_INIT_CONDITION_TRANSFER_TRANSIENT)
    def modflow_init_condition_transfer_transient(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.MODFLOW_INIT_CONDITION_TRANSFER_TRANSIENT)(
            project_metadata,
            **kwargs
        )
