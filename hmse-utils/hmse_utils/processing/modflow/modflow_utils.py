import copy
import logging
import os
from collections import deque
from typing import List, Tuple, Optional
from zipfile import ZipFile

import flopy
import numpy as np
from flopy.modflow import ModflowBas

from hmse_utils.processing.local_fs_configuration import local_paths
from hmse_utils.processing.model_exceptions import ModflowMissingFileError, ModflowCommonError
from hmse_utils.processing.modflow.modflow_extra_data import ModflowExtraData, extract_extra_from_model
from hmse_utils.processing.modflow.modflow_metadata import ModflowMetadata
from hmse_utils.processing.modflow.modflow_step import ModflowStepType, ModflowStep
from hmse_utils.processing.unit_manager import LengthUnit

logger = logging.getLogger(__name__)


def adapt_model_to_display(metadata: ModflowMetadata):
    if not metadata:
        return 0, 0, None

    row_cells, col_cells, total_width, total_height = scale_cells_size(metadata.row_cells, metadata.col_cells)
    return total_width, total_height, ModflowMetadata(row_cells=row_cells, col_cells=col_cells,
                                                      modflow_id=metadata.modflow_id,
                                                      rows=metadata.rows, cols=metadata.cols,
                                                      grid_unit=metadata.grid_unit,
                                                      steps_info=copy.deepcopy(metadata.steps_info))


def extract_and_fix_metadata(modflow_archive, tmp_dir: str) -> Tuple[
    ModflowMetadata, ModflowExtraData, np.ndarray]:
    logger.debug(f"Validating and extracting modflow model {modflow_archive.filename}")
    fixed_modflow_name = local_paths.fix_model_name(modflow_archive.filename)
    extension = fixed_modflow_name.split('.')[-1]
    modflow_id = fixed_modflow_name.replace(f".{extension}", "")

    modflow_path = os.path.join(tmp_dir, fixed_modflow_name)
    modflow_archive.save(modflow_path)
    with ZipFile(modflow_path, 'r') as archive:
        archive.extractall(tmp_dir)
    os.remove(modflow_path)
    __validate_model(tmp_dir)
    __fix_modflow_project(tmp_dir)

    model = flopy.modflow.Modflow.load(scan_for_modflow_file(tmp_dir),
                                       model_ws=tmp_dir,
                                       load_only=["rch", "dis"],
                                       forgive=True)

    model_shape = (model.nrow, model.ncol)
    model_steps = [ModflowStep(duration=int(duration), type=ModflowStepType.from_bool(is_steady_state))
                   for is_steady_state, duration in zip(model.modeltime.steady_state, model.modeltime.perlen)]
    model_metadata = ModflowMetadata(modflow_id,
                                     rows=model_shape[0], cols=model_shape[1],
                                     row_cells=model.dis.delc.array.tolist(),
                                     col_cells=model.dis.delr.array.tolist(),
                                     grid_unit=LengthUnit.map_from_alias(model.modelgrid.units),
                                     steps_info=model_steps)
    rch_shape_data, inactive_cells_data = get_shapes_from_rch(model_path=tmp_dir, model_shape=model_shape)
    extra_data = ModflowExtraData(
        **extract_extra_from_model(model),
        rch_shapes=rch_shape_data
    )
    return model_metadata, extra_data, inactive_cells_data


def scale_cells_size(row_cells: List[float],
                     col_cells: List[float],
                     max_width: float = 100) -> Tuple[List[float], List[float], int, int]:
    """
    Get cells size of modflow model
    @param col_cells: list of modflow model cols width
    @param row_cells: list of modflow model rows height
    @param max_width: Parameter for scaling purposes
    @return: Tuple with lists containing width of the Modflow project cells (row_cells, col_cells)
            and model total width and height
    """
    row_cells = np.array(row_cells, dtype="float64")
    col_cells = np.array(col_cells, dtype="float64")

    total_width = np.sum(col_cells)
    total_height = np.sum(row_cells)

    row_cells /= 0.03 * total_height
    col_cells /= 0.02 * total_width
    return list(row_cells), list(col_cells), int(total_width), int(total_height)


def get_shapes_from_rch(model_path: str, model_shape: Tuple[int, int]) -> Tuple[List[np.ndarray], np.ndarray]:
    """
    Defines shapes masks for uploaded Modflow model based on recharge

    @param model_path: Path of Modflow model
    @param model_shape: Tuple representing size of the Modflow project (rows, cols)
    @return: List of shapes read from Modflow project
    """

    logger.debug(f"Extracting RCH shapes for modflow mode under path: {model_path}")
    nam_file_name = scan_for_modflow_file(model_path)
    modflow_model = flopy.modflow.Modflow.load(nam_file_name,
                                               model_ws=model_path,
                                               load_only=["rch", "bas6"],
                                               forgive=True)

    stress_period = 0
    layer = 0

    recharge_masks = []
    is_checked_array = np.full(model_shape, False)
    recharge_array = modflow_model.rch.rech.array[stress_period][layer]
    modflow_rows, modflow_cols = model_shape

    for row in range(modflow_rows):
        for col in range(modflow_cols):
            if not is_checked_array[row][col]:
                recharge_masks.append(np.zeros(model_shape))
                __fill_mask_iterative(mask=recharge_masks[-1], recharge_array=recharge_array,
                                      is_checked_array=is_checked_array,
                                      project_shape=model_shape,
                                      row=row, col=col,
                                      value=recharge_array[row][col])

    ibound = next(pkg for pkg in modflow_model.packagelist if isinstance(pkg, ModflowBas)).ibound[0].array
    inactive_cells = np.where(ibound == 0, 1, 0)
    return recharge_masks, inactive_cells


def __fill_mask_iterative(mask: np.ndarray,
                          recharge_array: np.ndarray,
                          is_checked_array: np.ndarray,
                          project_shape: Tuple[int, int],
                          row: int,
                          col: int,
                          value: float):
    """
    Fill given mask with 1's according to recharge array (using DFS)

    @param mask: Binary mask of current shape - initially filled with 0's
    @param recharge_array: 2d array filled with modflow model recharge values
    @param is_checked_array: Control array - 'True' means that given cell was already used in one of the masks
    @param project_shape: Tuple representing shape of the Modflow project (rows, cols)
    @param row: Current column index
    @param col: Current row index
    @param value: Recharge value of current mask
    @return: None (result inside variable @mask)
    """
    modflow_rows, modflow_cols = project_shape

    stack = deque()
    stack.append((row, col))

    while stack:
        cur_row, cur_col = stack.pop()
        # return condition - out of bounds or given cell was already used
        if cur_row < 0 or cur_row >= modflow_rows or cur_col < 0 or cur_col >= modflow_cols or \
                is_checked_array[cur_row][cur_col]:
            continue

        if recharge_array[cur_row][cur_col] == value:
            is_checked_array[cur_row][cur_col] = True
            mask[cur_row][cur_col] = 1
            stack.append((cur_row - 1, cur_col))
            stack.append((cur_row + 1, cur_col))
            stack.append((cur_row, cur_col - 1))
            stack.append((cur_row, cur_col + 1))


def scan_for_modflow_file(model_path: str, ext: str = ".nam") -> Optional[str]:
    for file in os.listdir(model_path):
        if file.endswith(ext):
            return file
    return None


def __validate_model(model_path: str) -> None:
    """
    Validates modflow model - check if it contains .nam file (list of files), .rch file (recharge),
    perform recharge check.

    @param model_path: Path to Modflow project main directory
    @return: True if model is valid, False otherwise
    """

    nam_file_name = scan_for_modflow_file(model_path)
    if not nam_file_name:
        raise ModflowMissingFileError(description="Invalid Modflow model - .nam file not found!")

    try:
        # load whole model and validate it
        m = flopy.modflow.Modflow.load(nam_file_name,
                                       model_ws=model_path,
                                       forgive=True,
                                       check=True)
        if m.rch is None:
            raise ModflowMissingFileError(description="Invalid Modflow model - .rch file not found!")
        m.rch.check()
    except IOError:
        raise ModflowMissingFileError(description="Invalid Modflow model - validation detected missing files!")
    except KeyError:
        raise ModflowCommonError(description="Invalid Modflow model - validation detected an unspecified error!")


def __fix_modflow_project(modflow_base_dir: str):
    for file in os.listdir(modflow_base_dir):
        lowercase_file = file.lower()
        old_file = os.path.join(modflow_base_dir, file)
        new_file = os.path.join(modflow_base_dir, lowercase_file)
        os.rename(old_file, new_file)
        with open(new_file, 'r+b') as fp:
            original_content = fp.read()
            lf_separated_lines = original_content.replace(b'\r\n', b'\n')
            fp.seek(0)
            fp.write(lf_separated_lines)
            fp.truncate()
