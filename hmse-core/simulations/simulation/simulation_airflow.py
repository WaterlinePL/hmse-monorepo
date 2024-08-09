import datetime
import logging
import time
from typing import List

import pytz
from werkzeug.exceptions import HTTPException

from config.deployment_config import k8s
from simulations.projects.project_metadata import ProjectMetadata
from simulations.projects.typing_help import ProjectID
from simulations.simulation.airflow import airflow_simulation_service
from simulations.simulation.simulation_chapter import SimulationChapter
from simulations.simulation.simulation_enums import SimulationStageStatus, SimulationStageName
from simulations.simulation.simulation_status import ChapterStatus

IDENTIFICATION = 'simulation'

logger = logging.getLogger(__name__)


@k8s(identification=IDENTIFICATION)
class Simulation:

    def __init__(self, project_metadata: ProjectMetadata, sim_chapters: List[SimulationChapter]):
        self.project_metadata = project_metadata
        self.chapter_statuses = [ChapterStatus(chapter, project_metadata) for chapter in sim_chapters]
        self.time_measurements = {}

    def run_simulation(self):
        logger.info(f"Running airflow simulation for project: {self.project_metadata.project_id}")
        airflow_simulation_service.get().init_activate_dags()
        for chapter in self.chapter_statuses:
            self.__run_chapter(chapter)

    def get_simulation_status(self) -> List[ChapterStatus]:
        return self.chapter_statuses

    def __run_chapter(self, chapter_status: ChapterStatus) -> None:
        logger.info(f"Running chapter: {chapter_status.chapter}")
        chapter_tasks = chapter_status.chapter.get_simulation_tasks(self.project_metadata)
        total_chapter_start = time.time()
        dag_run_id = Simulation.generate_unique_run_id(chapter_name=chapter_status.chapter.get_name_snake_case(),
                                                       project_id=self.project_metadata.project_id)
        logger.debug(f"Starting simulation DAG with dag_run_id: {dag_run_id}")
        airflow_simulation_service.get().start_chapter(
            run_id=dag_run_id,
            chapter_name=chapter_status.chapter,
            project_metadata=self.project_metadata
        )

        for i, workflow_task in enumerate(chapter_tasks):
            chapter_status.set_stage_status(SimulationStageStatus.RUNNING, stage_idx=i)
            logger.info(f"Running task: {chapter_status.get_stages_names()[i]}")

            # Launch and monitor stage
            try:
                task_start = time.time()
                workflow_task(
                    self.project_metadata,
                    dag_run_id=dag_run_id,
                    chapter_name=chapter_status.chapter,
                    stage_name=chapter_status.get_stages_names()[i]
                )
                task_end = time.time()
                task_name = str(chapter_status.get_stages_statuses()[i].name)
                self.time_measurements[task_name] = task_end - task_start
                logger.info(f"Task {chapter_status.get_stages_names()[i]} ended successfully")
            except Exception as error:
                desc = str(error)
                chapter_status.set_stage_status(SimulationStageStatus.ERROR, stage_idx=i, error=desc)
                logger.error(f"Task {chapter_status.get_stages_names()[i]} failed! Simulation interrupted!")
                raise HTTPException(description=desc)

            chapter_status.set_stage_status(SimulationStageStatus.SUCCESS, stage_idx=i)

            if chapter_status.get_stages_statuses()[i].name == SimulationStageName.MODFLOW_SIMULATION:
                total_chapter_end = time.time()
                self.time_measurements["TOTAL"] = total_chapter_end - total_chapter_start
                logger.info(f"Simulation time measurements: {self.time_measurements}")
        logger.info(f"Chapter {chapter_status.chapter} ended successfully")

    @staticmethod
    def generate_unique_run_id(chapter_name: str, project_id: ProjectID):
        return f"{project_id}-{chapter_name}-{datetime.datetime.now(pytz.timezone('Europe/Warsaw'))}"
