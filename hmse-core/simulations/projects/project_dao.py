import abc
from typing import List

import numpy as np
from werkzeug.datastructures import FileStorage

from config.deployment_config import get_deployment_class, required
from hmse_utils.processing.typing_help import ModflowID, HydrusID
from simulations.projects.project_metadata import ProjectMetadata
from simulations.projects.typing_help import ProjectID, WeatherID, ShapeID

__INSTANCE = None
IDENTIFICATION = "project_dao"


@required(identification=IDENTIFICATION)
class ProjectDao(abc.ABC):

    def read_metadata(self, project_id: ProjectID) -> ProjectMetadata:
        ...

    def read_all_metadata(self) -> List[ProjectMetadata]:
        ...

    def read_all_names(self) -> List[str]:
        ...

    def save_or_update_metadata(self, metadata: ProjectMetadata) -> None:
        ...

    def delete_project(self, project_id: ProjectID) -> None:
        ...

    def download_project(self, project_id: ProjectID) -> str:
        ...

    def add_hydrus_model(self, project_id: ProjectID,
                         hydrus_id: HydrusID,
                         validated_model_path: str) -> None:
        ...

    def add_modflow_model(self, project_id: ProjectID,
                          modflow_id: ModflowID,
                          validated_model_path: str) -> None:
        ...

    def delete_hydrus_model(self, project_id: ProjectID, hydrus_id: HydrusID) -> None:
        ...

    def delete_modflow_model(self, project_id: ProjectID, modflow_id: ModflowID) -> None:
        ...

    def add_weather_file(self, project_id: ProjectID, weather_id: WeatherID, weather_file: FileStorage) -> None:
        ...

    def delete_weather_file(self, project_id: ProjectID, weather_id: WeatherID) -> None:
        ...

    def save_or_update_shape(self,
                             project_id: ProjectID,
                             shape_id: ShapeID,
                             shape_mask: np.ndarray) -> None:
        ...

    def get_rch_shapes(self, project_id: ProjectID):
        ...

    def delete_rch_shapes(self, project_id: ProjectID):
        ...

    def get_shape(self, project_id: ProjectID, shape_id: ShapeID) -> np.ndarray:
        ...

    def delete_shape(self, project_id: ProjectID, shape_id: ShapeID) -> None:
        ...

    def add_modflow_rch_shapes(self, project_id: ProjectID, rch_shapes: List[np.ndarray]):
        ...

    def get_project_root(self, project_id: ProjectID) -> str:
        ...


def get() -> ProjectDao:
    global __INSTANCE
    __INSTANCE = __INSTANCE or get_deployment_class(IDENTIFICATION)()
    return __INSTANCE
