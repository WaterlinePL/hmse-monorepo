import json
import logging
import os
import shutil
from typing import Dict, Union

import flopy
import numpy as np

from hmse_utils.processing.hydrus import hydrus_utils, hydrus_model_management
from hmse_utils.processing.local_fs_configuration import local_paths, feedback_loop_file_management
from hmse_utils.processing.modflow import modflow_model_management, modflow_utils

logger = logging.getLogger(__name__)


def local_files_initialization(project_id: str, **kwargs):
    logger.debug(f"Initializing local files for project: {project_id}")
    sim_dir = local_paths.get_simulation_dir(project_id)

    shutil.rmtree(sim_dir, ignore_errors=True)
    os.makedirs(sim_dir)
    shutil.copytree(local_paths.get_hydrus_dir(project_id),
                    local_paths.get_hydrus_dir(project_id, simulation_mode=True))
    shutil.copytree(local_paths.get_modflow_dir(project_id),
                    local_paths.get_modflow_dir(project_id, simulation_mode=True))


def preserve_reference_hydrus_models(project_id: str, **kwargs):
    logger.debug(f"Preserving reference hydrus models for project: {project_id}")
    shutil.copytree(local_paths.get_hydrus_dir(project_id, simulation_mode=True),
                    local_paths.get_hydrus_dir(project_id, simulation_mode=True, simulation_ref=True))


def extract_output_to_json(project_id: str, modflow_id: str, **kwargs):
    logger.debug(f"Extracting simulation output to JSON file for project: {project_id}")
    modflow_dir = local_paths.get_modflow_model_path(project_id, modflow_id, simulation_mode=True)
    nam_file = modflow_utils.scan_for_modflow_file(modflow_dir)
    modflow_model = flopy.modflow.Modflow.load(nam_file, model_ws=modflow_dir, forgive=True)

    fhd_path = modflow_utils.scan_for_modflow_file(modflow_dir, ext=".fhd")
    if fhd_path is not None:
        fhd_path = os.path.join(modflow_dir, fhd_path)
        modflow_output = flopy.utils.formattedfile.FormattedHeadFile(fhd_path, precision="single")

        result_fhd = np.array([modflow_output.get_data(idx=stress_period)
                               for stress_period in range(modflow_model.nper)])

        with open(local_paths.get_output_json_path(project_id), 'w') as handle:
            json.dump(result_fhd.tolist(), handle, indent=2)
            modflow_output.close()
    else:
        logger.warning(f"Skipping JSON output export for modflow model {modflow_id} in project {project_id} "
                       f"- no FHD output file configured.")


def initialize_feedback_iteration(project_id: str, modflow_id: str, spin_up: int,
                                  shapes_to_hydrus: Dict[str, Union[str, float]],
                                  **kwargs):
    logger.debug(f"Initializing new feedback iteration for project: {project_id}")
    modflow_model_management.prepare_model_for_next_iteration(project_id, modflow_id)
    hydrus_ids_data = hydrus_utils.get_compound_hydrus_ids_for_feedback_loop(shapes_to_hydrus)

    for ref_hydrus_id, compound_hydrus_id in hydrus_ids_data:
        hydrus_model_management.prepare_model_for_next_iteration(
            project_id=project_id,
            ref_hydrus_id=ref_hydrus_id,
            compound_hydrus_id=compound_hydrus_id,
            spin_up=spin_up
        )


def create_hydrus_models_for_zones(project_id: str, shapes_to_hydrus: Dict[str, Union[str, float]], **kwargs):
    logger.debug(f"Creating hydrus models for zones for project: {project_id}")
    hydrus_to_shapes = hydrus_utils.get_hydrus_to_shapes_mapping(shapes_to_hydrus)
    feedback_loop_file_management.create_per_shape_hydrus_models(project_id=project_id,
                                                                 used_hydrus_models=hydrus_to_shapes)


def pre_configure_iteration(project_id: str, **kwargs):
    feedback_loop_file_management.pre_configure_iteration(project_id)


def cleanup_project_volume(project_id: str, **kwargs):
    logger.debug(f"Performing cleanup after simulation for project: {project_id}")
    project_dir = local_paths.get_project_dir(project_id)
    shutil.rmtree(project_dir, ignore_errors=True)
