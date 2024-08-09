from config import deployment_config
from simulations.projects.project_metadata import ProjectMetadata
from simulations.simulation.simulation_enums import SimulationStageName
from simulations.simulation.tasks.hmse_task import hmse_task


class SimulationTasks:

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.HYDRUS_SIMULATION)
    def hydrus_simulation(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.HYDRUS_SIMULATION)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.HYDRUS_SIMULATION_WARMUP)
    def hydrus_simulation_warmup(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.HYDRUS_SIMULATION_WARMUP)(
            project_metadata,
            **kwargs
        )

    @staticmethod
    @hmse_task(stage_name=SimulationStageName.MODFLOW_SIMULATION)
    def modflow_simulation(project_metadata: ProjectMetadata, **kwargs) -> None:
        deployment_config.get_deployment_function(SimulationStageName.MODFLOW_SIMULATION)(
            project_metadata,
            **kwargs
        )
