import logging
import os
import tempfile
from typing import List

import numpy as np
from werkzeug.datastructures import FileStorage

from config.deployment_config import k8s
from hmse_utils.processing.local_fs_configuration.path_constants import METADATA_FILENAME
from hmse_utils.processing.typing_help import ModflowID, HydrusID
from simulations.projects import project_dao
from simulations.projects.minio_controller import minio_controller
from simulations.projects.project_metadata import ProjectMetadata
from simulations.projects.typing_help import ProjectID, WeatherID, ShapeID

logger = logging.getLogger(__name__)


@k8s(identification=project_dao.IDENTIFICATION)
class ProjectDaoMinio:

    def read_metadata(self, project_id: ProjectID) -> ProjectMetadata:
        logger.debug(f"Reading metadata for project: {project_id}")
        metadata_dict = minio_controller.get().get_json_content(f"projects/{project_id}/{METADATA_FILENAME}")
        return ProjectMetadata(**metadata_dict)

    def read_all_metadata(self) -> List[ProjectMetadata]:
        logger.debug("Reading metadata of all projects")
        return [self.read_metadata(project_id) for project_id in self.read_all_names()]

    def read_all_names(self) -> List[str]:
        logger.debug("Reading names of all projects")
        return [obj.object_name.replace("projects/", '')[:-1]
                for obj in minio_controller.get().list_bucket_content("projects/")
                if obj.object_name != "projects/"]

    def save_or_update_metadata(self, metadata: ProjectMetadata) -> None:
        logger.debug(f"Saving changes to metadata for project: {metadata.project_id}")
        minio_controller.get().put_json_file(metadata.to_json_response(),
                                             f"projects/{metadata.project_id}/metadata.json")

    def delete_project(self, project_id: ProjectID) -> None:
        logger.debug(f"Deleting project: {project_id}")
        minio_controller.get().delete_directory(f"projects/{project_id}/")

    def download_project(self, project_id: ProjectID) -> FileStorage:
        logger.debug(f"Archiving project for download: {project_id}")
        return minio_controller.get().get_file_bytes(f"projects/{project_id}/output.zip")

    def add_hydrus_model(self, project_id: ProjectID,
                         hydrus_id: HydrusID,
                         validated_model_path: os.PathLike) -> None:
        logger.debug(f"Adding hydrus model {hydrus_id} to project: {project_id}")
        minio_controller.get().upload_directory_to_bucket(validated_model_path,
                                                          f"projects/{project_id}/hydrus/{hydrus_id}")

    def add_modflow_model(self, project_id: ProjectID,
                          modflow_id: ModflowID,
                          validated_model_path: os.PathLike) -> None:
        logger.debug(f"Adding modflow model {modflow_id} to project: {project_id}")
        minio_controller.get().upload_directory_to_bucket(validated_model_path,
                                                          f"projects/{project_id}/modflow/{modflow_id}")

    def delete_hydrus_model(self, project_id: ProjectID, hydrus_id: HydrusID) -> None:
        logger.debug(f"Deleting hydrus model {hydrus_id} from project: {project_id}")
        minio_controller.get().delete_directory(f"projects/{project_id}/hydrus/{hydrus_id}/")

    def delete_modflow_model(self, project_id: ProjectID, modflow_id: ModflowID) -> None:
        logger.debug(f"Deleting modflow model {modflow_id} from project: {project_id}")
        minio_controller.get().delete_directory(f"projects/{project_id}/modflow/{modflow_id}/")

    def add_weather_file(self, project_id: ProjectID, weather_id: WeatherID, weather_file: FileStorage) -> None:
        logger.debug(f"Adding SWAT weather file {weather_id} to project: {project_id}")
        with tempfile.TemporaryDirectory() as tmp_dir:
            path_to_weather_file = os.path.join(tmp_dir, weather_file.filename)
            weather_file.save(path_to_weather_file)
            minio_controller.get().put_file(path_to_weather_file, f"projects/{project_id}/weather/{weather_id}.csv")

    def delete_weather_file(self, project_id: ProjectID, weather_id: WeatherID) -> None:
        logger.debug(f"Deleting SWAT weather file {weather_id} to project: {project_id}")
        minio_controller.get().delete_file(f"projects/{project_id}/weather/{weather_id}.csv")

    def save_or_update_shape(self,
                             project_id: ProjectID,
                             shape_id: ShapeID,
                             shape_mask: np.ndarray,
                             is_rch: bool = False) -> None:
        logger.debug(f"Saving shape {shape_id} in project: {project_id}")
        with tempfile.TemporaryDirectory() as tmp_dir:
            shape_path = os.path.join(tmp_dir, "shape.npy")
            np.save(shape_path, shape_mask)
            shape_project_dir = "rch_shapes" if is_rch else "shapes"
            s3_path = f"projects/{project_id}/{shape_project_dir}/{shape_id}.npy"
            minio_controller.get().put_file(shape_path, s3_path)

    def get_rch_shapes(self, project_id: ProjectID):
        logger.debug(f"Retrieving RCH shapes for project: {project_id}")
        rch_shapes = {}
        rch_paths = [obj.object_name for obj in
                     minio_controller.get().list_bucket_content(f"projects/{project_id}/rch_shapes/")]
        for rch_shape_bucket_path in rch_paths:
            shape_id = rch_shape_bucket_path.split("/")[-1].split('.')[0]
            rch_shapes[shape_id] = self.get_shape(project_id, shape_id)
        return rch_shapes

    def delete_rch_shapes(self, project_id: ProjectID):
        logger.debug(f"Deleting all RCH shapes in project: {project_id}")
        minio_controller.get().delete_directory(f"projects/{project_id}/rch_shapes")

    def get_shape(self, project_id: ProjectID, shape_id: ShapeID) -> np.ndarray:
        logger.debug(f"Reading shape {shape_id} in project: {project_id}")
        shape_dir = "rch_shapes" if shape_id.startswith("rch_shape_") else "shapes"
        with tempfile.TemporaryDirectory() as tmp_dir:
            shape_path = os.path.join(tmp_dir, "shape.npy")
            minio_controller.get().get_file(f"projects/{project_id}/{shape_dir}/{shape_id}.npy", shape_path)
            return np.load(shape_path)

    def delete_shape(self, project_id: ProjectID, shape_id: ShapeID) -> None:
        logger.debug(f"Deleting shape {shape_id} in project: {project_id}")
        minio_controller.get().delete_file(f"projects/{project_id}/shapes/{shape_id}.npy")

    def add_modflow_rch_shapes(self, project_id: ProjectID, rch_shapes: List[np.ndarray]):
        logger.debug(f"Generating RCH shapes for project: {project_id}")
        for i, mask in enumerate(rch_shapes):
            shape_id = f"rch_shape_{i + 1}"
            self.save_or_update_shape(project_id, shape_id, mask, is_rch=True)

    def get_project_root(self, project_id: ProjectID) -> str:
        return f"{minio_controller.get().get_root()}/projects/{project_id}"
