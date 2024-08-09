import os
import tempfile
from typing import List, Dict

import numpy as np
from werkzeug.datastructures import FileStorage

from hmse_utils.processing.hydrus import hydrus_utils
from hmse_utils.processing.modflow import modflow_utils, zonebudget_shape_parser
from hmse_utils.processing.modflow.modflow_metadata import ModflowMetadata
from hmse_utils.processing.typing_help import HydrusID
from simulations.projects import project_dao, polygon_processor
from simulations.projects.project_exceptions import ProjectSimulationNotFinishedError
from simulations.projects.project_metadata import ProjectMetadata
from simulations.projects.shape_utils import generate_random_html_color
from simulations.projects.simulation_mode import SimulationMode
from simulations.projects.typing_help import ProjectID, WeatherID, ShapeID


def get(project_id: ProjectID) -> ProjectMetadata:
    return project_dao.get().read_metadata(project_id)


def get_all_project_names() -> List[ProjectID]:
    return project_dao.get().read_all_names()


def save_or_update_metadata(metadata: ProjectMetadata) -> None:
    project_dao.get().save_or_update_metadata(metadata)


def delete(project_id: ProjectID) -> None:
    project_dao.get().delete_project(project_id)


def download_project(project_id: ProjectID):
    if not project_dao.get().read_metadata(project_id).finished:
        raise ProjectSimulationNotFinishedError()
    return project_dao.get().download_project(project_id)


def is_finished(project_id: ProjectID) -> bool:
    return project_dao.get().read_metadata(project_id).finished


def add_hydrus_model(project_id: ProjectID, hydrus_model: FileStorage) -> HydrusID:
    metadata = project_dao.get().read_metadata(project_id)

    with tempfile.TemporaryDirectory() as validation_dir:
        hydrus_id = hydrus_utils.validate_model(hydrus_model, validation_dir)
        project_dao.get().add_hydrus_model(project_id, hydrus_id, validation_dir)
        metadata.add_hydrus_model(hydrus_id)
        project_dao.get().save_or_update_metadata(metadata)
        return hydrus_id


def delete_hydrus_model(project_id: ProjectID, hydrus_id: HydrusID):
    metadata = project_dao.get().read_metadata(project_id)
    metadata.remove_hydrus_model(hydrus_id)
    project_dao.get().delete_hydrus_model(project_id, hydrus_id)
    project_dao.get().save_or_update_metadata(metadata)


def set_modflow_model(project_id: ProjectID, modflow_model: FileStorage) -> ModflowMetadata:
    metadata = project_dao.get().read_metadata(project_id)

    if metadata.modflow_metadata:
        project_dao.get().delete_modflow_model(project_id, metadata.modflow_metadata.modflow_id)

    with tempfile.TemporaryDirectory() as validation_dir:
        model_metadata, extra_data, inactive_cells_shape = modflow_utils.extract_and_fix_metadata(
            modflow_model,
            validation_dir
        )
        modflow_id = model_metadata.modflow_id
        project_dao.get().add_modflow_model(project_id, modflow_id, validation_dir)
        metadata.set_modflow_metadata(model_metadata)

        inactive_shape_id = "inactive_modflow_cells"
        inactive_shape_color = "#999999"
        project_dao.get().save_or_update_shape(project_id, inactive_shape_id, inactive_cells_shape)
        metadata.add_shape_metadata(inactive_shape_id, inactive_shape_color)

        metadata.start_date = extra_data.start_date
        project_dao.get().save_or_update_metadata(metadata)
        project_dao.get().add_modflow_rch_shapes(project_id, extra_data.rch_shapes)
        return model_metadata


def delete_modflow_model(project_id: ProjectID):
    metadata = project_dao.get().read_metadata(project_id)
    modflow_id = metadata.modflow_metadata.modflow_id

    metadata.remove_modflow_metadata()
    wipe_all_shapes(project_id)
    project_dao.get().delete_rch_shapes(project_id)
    metadata.shapes = {}
    metadata.shapes_to_hydrus = {}

    project_dao.get().delete_modflow_model(project_id, modflow_id)
    project_dao.get().save_or_update_metadata(metadata)


def add_weather_file(project_id: ProjectID, weather_file: FileStorage) -> WeatherID:
    metadata = project_dao.get().read_metadata(project_id)
    weather_id = weather_file.filename[:-4]  # .csv file
    metadata.add_weather_file(weather_id)
    project_dao.get().add_weather_file(project_id, weather_id, weather_file)
    project_dao.get().save_or_update_metadata(metadata)
    return weather_id


def delete_weather_file(project_id: ProjectID, weather_id: HydrusID):
    metadata = project_dao.get().read_metadata(project_id)
    metadata.remove_weather_file(weather_id)
    project_dao.get().delete_weather_file(project_id, weather_id)
    project_dao.get().save_or_update_metadata(metadata)


def get_all_shapes(project_id: ProjectID) -> Dict[ShapeID, List[List[int]]]:
    metadata = project_dao.get().read_metadata(project_id)
    shapes_to_masks = {shape_id: project_dao.get().get_shape(project_id, shape_id) for shape_id in
                       metadata.shapes.keys()}
    return __transform_mask_to_polygon(shapes_to_masks)


def add_rch_shapes(project_id: ProjectID):
    rch_shapes = project_dao.get().get_rch_shapes(project_id)
    shape_ids = __save_new_shapes(project_id, rch_shapes)
    return {
        "shapeIds": shape_ids,
        "shapeMasks": __transform_mask_to_polygon(rch_shapes)
    }


def add_zb_shapes(project_id: ProjectID, zb_file: FileStorage):
    with tempfile.TemporaryDirectory() as zb_dir:
        zb_path = os.path.join(zb_dir, zb_file.filename)
        zb_file.save(zb_path)
        zb_shapes = zonebudget_shape_parser.read_zone_file(zb_path)

    zb_shapes = {f"zb_shape_{i + 1}": shape for i, shape in enumerate(zb_shapes)}
    shape_ids = __save_new_shapes(project_id, zb_shapes)
    return {
        "shapeIds": shape_ids,
        "shapeMasks": __transform_mask_to_polygon(zb_shapes)
    }


def save_or_update_shape(project_id: ProjectID, shape_id: ShapeID, color: str,
                         new_shape_id: ShapeID) -> None:
    metadata = project_dao.get().read_metadata(project_id)
    if metadata.contains_shape(shape_id) and shape_id != new_shape_id:
        project_dao.get().delete_shape(project_id, shape_id)
        current_shape_mapping = metadata.shapes_to_hydrus.get(shape_id)

        if current_shape_mapping is not None:
            if isinstance(current_shape_mapping, float):
                metadata.map_shape_to_manual_value(new_shape_id, current_shape_mapping)
            else:
                metadata.map_shape_to_hydrus(new_shape_id, current_shape_mapping)
            metadata.remove_shape_mapping(shape_id)
        metadata.remove_shape_metadata(shape_id)

    metadata.add_shape_metadata(new_shape_id, color)
    # project_dao.get().save_or_update_shape(project_id, new_shape_id, shape_mask)
    project_dao.get().save_or_update_metadata(metadata)


def delete_shape(project_id: ProjectID, shape_id: ShapeID) -> None:
    metadata = project_dao.get().read_metadata(project_id)
    metadata.remove_shape_metadata(shape_id)
    project_dao.get().delete_shape(project_id, shape_id)
    project_dao.get().save_or_update_metadata(metadata)


def map_shape_to_hydrus(project_id: ProjectID, shape_id: ShapeID, hydrus_id: HydrusID):
    metadata = project_dao.get().read_metadata(project_id)
    metadata.map_shape_to_hydrus(shape_id, hydrus_id)
    project_dao.get().save_or_update_metadata(metadata)


def map_shape_to_manual_value(project_id: ProjectID, shape_id: ShapeID, value: float):
    metadata = project_dao.get().read_metadata(project_id)
    metadata.map_shape_to_manual_value(shape_id, value)
    project_dao.get().save_or_update_metadata(metadata)


def map_hydrus_to_weather_file(project_id: ProjectID, hydrus_id: HydrusID, weather_id: WeatherID):
    metadata = project_dao.get().read_metadata(project_id)
    metadata.map_hydrus_to_weather(hydrus_id, weather_id)
    project_dao.get().save_or_update_metadata(metadata)


def remove_shape_mapping(project_id: ProjectID, shape_id: ShapeID):
    metadata = project_dao.get().read_metadata(project_id)
    metadata.remove_shape_mapping(shape_id)
    project_dao.get().save_or_update_metadata(metadata)


def remove_weather_hydrus_mapping(project_id: ProjectID, hydrus_id: HydrusID):
    metadata = project_dao.get().read_metadata(project_id)
    metadata.remove_hydrus_weather_mapping(hydrus_id)
    project_dao.get().save_or_update_metadata(metadata)


def wipe_all_shapes(project_id: ProjectID) -> None:
    metadata = project_dao.get().read_metadata(project_id)
    shape_ids = list(metadata.shapes.keys())
    for shape_id in shape_ids:
        project_dao.get().delete_shape(metadata.project_id, shape_id)
        metadata.remove_shape_metadata(shape_id)
    project_dao.get().save_or_update_metadata(metadata)


def update_simulation_mode(project_id: ProjectID, mode: str) -> None:
    metadata = project_dao.get().read_metadata(project_id)
    metadata.simulation_mode = SimulationMode(mode)
    project_dao.get().save_or_update_metadata(metadata)


def __transform_mask_to_polygon(shapes_to_mask: Dict[ShapeID, np.ndarray]) -> Dict[ShapeID, List[List[int]]]:
    res_shapes = {}
    for shape_id, mask in shapes_to_mask.items():
        shape_polygon, repeats = polygon_processor.get_polygons_from_mask(mask)
        res_shapes[shape_id] = polygon_processor.scale_polygon(shape_polygon, mask.shape, repeats).tolist()
    return res_shapes


def __save_new_shapes(project_id, shape_data):
    for shape_id, mask in shape_data.items():
        project_dao.get().save_or_update_shape(project_id, shape_id, mask)
    shape_ids = {shape_id: generate_random_html_color() for shape_id in shape_data.keys()}
    metadata = project_dao.get().read_metadata(project_id)
    metadata.shapes.update(shape_ids)
    project_dao.get().save_or_update_metadata(metadata)
    return shape_ids
