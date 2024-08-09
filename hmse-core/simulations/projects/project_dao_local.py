import json
import logging
import os
import shutil
from typing import List

import numpy as np
from werkzeug.datastructures import FileStorage

from config.deployment_config import desktop, docker
from hmse_utils.processing.local_fs_configuration import local_paths
from hmse_utils.processing.local_fs_configuration.path_constants import \
    get_workspace_local_path
from hmse_utils.processing.typing_help import ModflowID, HydrusID
from simulations.projects import project_dao
from simulations.projects.project_metadata import ProjectMetadata
from simulations.projects.typing_help import ProjectID, WeatherID, ShapeID

logger = logging.getLogger(__name__)


@desktop(identification=project_dao.IDENTIFICATION)
@docker(identification=project_dao.IDENTIFICATION)
class ProjectDaoLocal:

    def __init__(self):
        logger.debug(f"Initializing local project DAO using workspace path: {get_workspace_local_path()}")
        os.makedirs(get_workspace_local_path(), exist_ok=True)

    def read_metadata(self, project_id: ProjectID) -> ProjectMetadata:
        logger.debug(f"Reading metadata for project: {project_id}")
        with open(local_paths.get_project_metadata_path(project_id), 'r') as handle:
            return ProjectMetadata(**json.load(handle))

    def read_all_metadata(self) -> List[ProjectMetadata]:
        logger.debug("Reading metadata of all projects")
        return [self.read_metadata(project_id) for project_id in self.read_all_names()]

    def read_all_names(self) -> List[str]:
        logger.debug("Reading names of all projects")
        return os.listdir(get_workspace_local_path())

    def save_or_update_metadata(self, metadata: ProjectMetadata) -> None:
        project_id = metadata.project_id
        logger.debug(f"Saving changes to metadata for project: {project_id}")
        os.makedirs(local_paths.get_project_dir(project_id), exist_ok=True)

        with open(local_paths.get_project_metadata_path(project_id), 'w') as handle:
            json.dump(metadata.to_json_response(), handle, indent=2, default=lambda o: o.__dict__)

        os.makedirs(local_paths.get_modflow_dir(project_id), exist_ok=True)
        os.makedirs(local_paths.get_hydrus_dir(project_id), exist_ok=True)
        os.makedirs(local_paths.get_weather_dir(project_id), exist_ok=True)
        os.makedirs(local_paths.get_shapes_dir(project_id), exist_ok=True)
        os.makedirs(local_paths.get_rch_shapes_dir(project_id), exist_ok=True)

    def delete_project(self, project_id: ProjectID) -> None:
        logger.debug(f"Deleting project: {project_id}")
        try:
            shutil.rmtree(local_paths.get_project_dir(project_id))
        except OSError as e:
            logging.error(f"Error occurred during deleting project {project_id}: {str(e)}")

    def download_project(self, project_id: ProjectID) -> str:
        logger.debug(f"Archiving project for download: {project_id}")
        return shutil.make_archive(base_name=os.path.join(local_paths.get_project_dir(project_id), project_id),
                                   format='zip',
                                   root_dir=local_paths.get_simulation_dir(project_id))

    def add_hydrus_model(self, project_id: ProjectID,
                         hydrus_id: HydrusID,
                         validated_model_path: str) -> None:
        logger.debug(f"Adding hydrus model {hydrus_id} to project: {project_id}")
        hydrus_model_dir = local_paths.get_hydrus_model_path(project_id, hydrus_id)
        os.makedirs(hydrus_model_dir)
        for hydrus_file in os.listdir(validated_model_path):
            validated_file_path = os.path.join(validated_model_path, hydrus_file)
            shutil.move(validated_file_path, hydrus_model_dir)

    def add_modflow_model(self, project_id: ProjectID,
                          modflow_id: ModflowID,
                          validated_model_path: str) -> None:
        logger.debug(f"Adding modflow model {modflow_id} to project: {project_id}")
        modflow_model_dir = local_paths.get_modflow_model_path(project_id, modflow_id)
        os.makedirs(modflow_model_dir)
        for modflow_file in os.listdir(validated_model_path):
            validated_file_path = os.path.join(validated_model_path, modflow_file)
            shutil.move(validated_file_path, modflow_model_dir)

    def delete_hydrus_model(self, project_id: ProjectID, hydrus_id: HydrusID) -> None:
        logger.debug(f"Deleting hydrus model {hydrus_id} from project: {project_id}")
        shutil.rmtree(local_paths.get_hydrus_model_path(project_id, hydrus_id))

    def delete_modflow_model(self, project_id: ProjectID, modflow_id: ModflowID) -> None:
        logger.debug(f"Deleting modflow model {modflow_id} from project: {project_id}")
        shutil.rmtree(local_paths.get_modflow_model_path(project_id, modflow_id))
        rch_shapes_path = local_paths.get_rch_shapes_dir(project_id)
        shutil.rmtree(rch_shapes_path)
        os.makedirs(rch_shapes_path)

    def add_weather_file(self, project_id: ProjectID, weather_id: WeatherID, weather_file: FileStorage) -> None:
        logger.debug(f"Adding SWAT weather file {weather_id} to project: {project_id}")
        os.makedirs(local_paths.get_weather_dir(project_id), exist_ok=True)
        weather_file.save(f"{local_paths.get_weather_model_path(project_id, weather_id)}")

    def delete_weather_file(self, project_id: ProjectID, weather_id: WeatherID) -> None:
        logger.debug(f"Deleting SWAT weather file {weather_id} to project: {project_id}")
        os.remove(local_paths.get_weather_model_path(project_id, weather_id))

    def save_or_update_shape(self,
                             project_id: ProjectID,
                             shape_id: ShapeID,
                             shape_mask: np.ndarray) -> None:
        logger.debug(f"Saving shape {shape_id} in project: {project_id}")
        os.makedirs(local_paths.get_shapes_dir(project_id), exist_ok=True)
        np.save(local_paths.get_shape_path(project_id, shape_id), shape_mask)

    def get_rch_shapes(self, project_id: ProjectID):
        logger.debug(f"Retrieving RCH shapes for project: {project_id}")
        return {shape_id[:-4]: np.load(local_paths.get_rch_shape_filepath(project_id, shape_id[:-4]))
                for shape_id in os.listdir(local_paths.get_rch_shapes_dir(project_id))}

    def delete_rch_shapes(self, project_id: ProjectID):
        logger.debug(f"Deleting all RCH shapes in project: {project_id}")
        rch_shapes_path = local_paths.get_rch_shapes_dir(project_id)
        for rch_shape_id in os.listdir(rch_shapes_path):
            os.remove(os.path.join(rch_shapes_path, rch_shape_id))

    def get_shape(self, project_id: ProjectID, shape_id: ShapeID) -> np.ndarray:
        logger.debug(f"Reading shape {shape_id} in project: {project_id}")
        return np.load(local_paths.get_shape_path(project_id, shape_id))

    def delete_shape(self, project_id: ProjectID, shape_id: ShapeID) -> None:
        logger.debug(f"Deleting shape {shape_id} in project: {project_id}")
        os.remove(local_paths.get_shape_path(project_id, shape_id))

    def add_modflow_rch_shapes(self, project_id: ProjectID, rch_shapes: List[np.ndarray]):
        logger.debug(f"Generating RCH shapes for project: {project_id}")
        os.makedirs(local_paths.get_rch_shapes_dir(project_id), exist_ok=True)
        for i, mask in enumerate(rch_shapes):
            shape_id = f"rch_shape_{i + 1}"
            np.save(local_paths.get_rch_shape_filepath(project_id, shape_id), mask)

    def get_project_root(self, project_id: ProjectID) -> str:
        # Not needed
        ...
