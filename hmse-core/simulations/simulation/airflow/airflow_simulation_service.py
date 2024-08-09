import logging
import os
from time import sleep
from typing import Callable, Dict

import requests
from requests.auth import HTTPBasicAuth

from config.deployment_config import k8s
from simulations.projects import project_dao
from simulations.projects.minio_controller import minio_controller
from simulations.projects.project_metadata import ProjectMetadata
from simulations.projects.simulation_mode import SimulationMode
from simulations.simulation.airflow.airflow_name_converter import convert_hmse_task_to_airflow_task_name, \
    convert_chapter_to_dag_name
from simulations.simulation.simulation_enums import SimulationStageStatus, SimulationStageName
from simulations.simulation.simulation_error import SimulationError

# Needed environment variables:
# AIRFLOW_API_ENDPOINT
# AIRFLOW_USER
# AIRFLOW_PASSWORD
AIRFLOW_API_ENDPOINT = os.environ.get("AIRFLOW_API_ENDPOINT")
AIRFLOW_USER = os.environ.get("AIRFLOW_USER")
AIRFLOW_PASSWORD = os.environ.get("AIRFLOW_PASSWORD")

__INSTANCE = None
IDENTIFICATION = "airflow_simulation_service"

logger = logging.getLogger(__name__)


@k8s(identification=IDENTIFICATION)
class AirflowSimulationService:
    def __init__(self):
        logger.debug(f"Initializing Airflow simulation service ({AIRFLOW_API_ENDPOINT})")
        self.auth = HTTPBasicAuth(AIRFLOW_USER, AIRFLOW_PASSWORD)

    def get_simulation_stage_status(self,
                                    run_id: str,
                                    chapter_name: 'SimulationChapter',
                                    task_id: str) -> SimulationStageStatus:

        logger.debug(f"Checking stage status for task {task_id} in DAG run: {run_id} (chapter {chapter_name})")
        resp = requests.get(self.__get_endpoint_for_task(run_id, chapter_name, task_id), auth=self.auth)
        resp.raise_for_status()
        status = resp.json()["state"]
        return AirflowSimulationService.__analyze_single_status(status)

    def get_mapped_stage_status(self,
                                run_id: str,
                                chapter_name: 'SimulationChapter',
                                task_id: str) -> SimulationStageStatus:

        logger.debug(f"Checking stage status for mapped task {task_id} in DAG run: {run_id} (chapter {chapter_name})")
        mapped_endpoint = f"{self.__get_endpoint_for_task(run_id, chapter_name, task_id)}/listMapped"
        resp = requests.get(mapped_endpoint, auth=self.auth)
        task_instances = resp.json()["task_instances"]
        task_statuses = set(AirflowSimulationService.__analyze_single_status(inst["state"]) for inst in task_instances)
        if SimulationStageStatus.ERROR in task_statuses:
            return SimulationStageStatus.ERROR
        elif SimulationStageStatus.RUNNING in task_statuses:
            return SimulationStageStatus.RUNNING
        elif SimulationStageStatus.PENDING in task_statuses:
            return SimulationStageStatus.PENDING
        return SimulationStageStatus.SUCCESS

    def init_activate_dags(self):
        dag_pattern = "hmse_"
        req_content = {
            "is_paused": False
        }
        resp = requests.patch(AirflowSimulationService.__get_endpoint_for_dags_state_update(),
                              params={
                                  "dag_id_pattern": dag_pattern,
                              },
                              json=req_content,
                              auth=self.auth)

        if resp.status_code != 200:
            raise SimulationError(description="Failed to connect to Airflow scheduler!")

        initialized_dags = [dag["dag_id"] for dag in resp.json()["dags"]]
        logger.info(f"Successfully initialized DAGs: {initialized_dags}")

    def start_chapter(self, run_id: str, chapter_name: 'SimulationChapter', project_metadata: ProjectMetadata):
        logger.debug(f"Starting chapter {chapter_name} for DAG run: {run_id}")
        req_content = {
            "conf": AirflowSimulationService.__prepare_config_json(project_metadata),
            "dag_run_id": run_id
        }
        resp = requests.post(AirflowSimulationService.__get_endpoint_for_simulation_start(chapter_name),
                             json=req_content,
                             auth=self.auth)
        if resp.status_code != 200:
            raise SimulationError(description="Chapter failed to start!")

    @staticmethod
    def __get_endpoint_for_task(run_id: str, chapter_name: 'SimulationChapter', task_id: str) -> str:
        dag_name = convert_chapter_to_dag_name(chapter_name)
        return (f"http://{AIRFLOW_API_ENDPOINT}/dags/{dag_name}/dagRuns/{run_id}/"
                f"taskInstances/{task_id}")

    @staticmethod
    def __analyze_single_status(airflow_task_status: str):
        if airflow_task_status in ("success", "skipped"):
            return SimulationStageStatus.SUCCESS
        elif airflow_task_status in ("failed", "upstream_failed"):
            return SimulationStageStatus.ERROR
        elif airflow_task_status == "running":
            return SimulationStageStatus.RUNNING
        return SimulationStageStatus.PENDING

    @staticmethod
    def __get_endpoint_for_simulation_start(chapter_name: 'SimulationChapter'):
        dag_name = convert_chapter_to_dag_name(chapter_name)
        return f"http://{AIRFLOW_API_ENDPOINT}/dags/{dag_name}/dagRuns"

    @staticmethod
    def __get_endpoint_for_dags_state_update():
        return f"http://{AIRFLOW_API_ENDPOINT}/dags"

    @staticmethod
    def __prepare_config_json(metadata: ProjectMetadata) -> Dict:
        s3_location_prefix = minio_controller.get().get_s3_prefix()
        s3_location = f"{s3_location_prefix}{project_dao.get().get_project_root(metadata.project_id)}"
        simulation_config = metadata.to_json_response().__dict__
        if "modflow_metadata" in simulation_config:
            simulation_config["modflow_metadata"] = simulation_config["modflow_metadata"].to_json()
        simulation_config["project_minio_location"] = s3_location
        simulation_config["is_feedback_loop"] = metadata.simulation_mode == SimulationMode.WITH_FEEDBACK
        return {"simulation": simulation_config}

    def monitor_job(self, dag_run_id: str, chapter_name: 'SimulationChapter', stage_name: SimulationStageName):
        logger.debug(f"Monitoring stage {stage_name} in DAG run: {dag_run_id} (chapter {chapter_name})")
        task_id = convert_hmse_task_to_airflow_task_name(stage_name)
        AirflowSimulationService.__monitor_airflow_task(dag_run_id, chapter_name, task_id,
                                                        status_getter_function=self.get_simulation_stage_status)

    def monitor_mapped_job(self, dag_run_id: str, chapter_name: 'SimulationChapter', stage_name: SimulationStageName):
        logger.debug(f"Monitoring mapped stage {stage_name} in DAG run: {dag_run_id} (chapter {chapter_name})")
        task_id = convert_hmse_task_to_airflow_task_name(stage_name)
        AirflowSimulationService.__monitor_airflow_task(dag_run_id, chapter_name, task_id,
                                                        status_getter_function=self.get_mapped_stage_status)

    @staticmethod
    def __monitor_airflow_task(dag_run_id: str,
                               chapter_name: 'SimulationChapter',
                               task_id: str,
                               status_getter_function: Callable):
        done = False
        while not done:
            status = status_getter_function(
                run_id=dag_run_id,
                chapter_name=chapter_name,
                task_id=task_id
            )
            done = AirflowSimulationService.handle_stage_status(task_id, status)
            sleep(2)

    @staticmethod
    def handle_stage_status(task_id: str, stage_status: SimulationStageStatus) -> bool:
        if stage_status == SimulationStageStatus.ERROR:
            raise SimulationError(f"Task {task_id} has failed!")
        if stage_status == SimulationStageStatus.SUCCESS:
            return True
        return False


def get() -> AirflowSimulationService:
    global __INSTANCE
    if __INSTANCE is None:
        __INSTANCE = AirflowSimulationService()
    return __INSTANCE
