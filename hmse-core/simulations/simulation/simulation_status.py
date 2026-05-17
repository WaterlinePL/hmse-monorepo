from typing import List

from simulations.projects.project_metadata import ProjectMetadata
from simulations.projects.simulation_core_mode import SimulationCoreMode
from simulations.simulation.simulation_chapter import SimulationChapter
from simulations.simulation.simulation_enums import SimulationStageName, SimulationStageStatus, SimulationStage
from simulations.simulation.tasks import hmse_task


class ChapterStatus:

    def __init__(self, chapter: SimulationChapter, metadata: ProjectMetadata, core_mode: SimulationCoreMode):
        stages = [hmse_task.get_stage_name(t) for t in chapter.get_simulation_tasks(metadata)]
        self.chapter = chapter
        self.stages = stages
        self.stages_statuses = [SimulationStage(stage, SimulationStageStatus.PENDING) for stage in stages]
        self._core_mode = core_mode

    def get_stages_names(self) -> List[SimulationStageName]:
        return self.stages

    def get_stages_statuses(self) -> List[SimulationStage]:
        return self.stages_statuses

    def set_stage_status(self, new_status: SimulationStageStatus, stage_idx: int, error: str = None):
        self.stages_statuses[stage_idx].status = new_status
        self.stages_statuses[stage_idx].error = error

    def to_json(self, i: int):
        stage_statuses = [
            {
                "id": f"{stage.name.get_as_id()}{i}",
                "name": stage.name.get_name(self._core_mode),
                "status": stage.status,
                "error": stage.error,
            } for i, stage in enumerate(self.stages_statuses)
        ]
        return {
            "chapter_id": f"{self.chapter.get_as_id()}{i}",
            "chapter_name": self.chapter.get_name(),
            "stage_statuses": stage_statuses
        }
