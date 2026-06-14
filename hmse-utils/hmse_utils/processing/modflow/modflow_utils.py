import copy
import logging
import os
import re
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
    model_steps = [
        ModflowStep(
            duration=convert_time_units_to_days(duration, model.modeltime.time_units),
            type=ModflowStepType.from_bool(is_steady_state),
        )
        for is_steady_state, duration in zip(model.modeltime.steady_state, model.modeltime.perlen)
    ]
    model_metadata = ModflowMetadata(modflow_id,
                                     rows=model_shape[0], cols=model_shape[1],
                                     row_cells=model.dis.delc.array.tolist(),
                                     col_cells=model.dis.delr.array.tolist(),
                                     grid_unit=LengthUnit.map_from_alias(model.modelgrid.units),
                                     steps_info=model_steps)
    rch_shape_data, inactive_cells_data = get_shapes_from_rch(model_path=tmp_dir, model_shape=model_shape)
    ssm_shape_data = get_shapes_from_ssm(model_path=tmp_dir, model_shape=model_shape)
    extra_data = ModflowExtraData(
        **extract_extra_from_model(model),
        rch_shapes=rch_shape_data,
        ssm_shapes=ssm_shape_data,
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


def get_shapes_from_ssm(model_path: str, model_shape: Tuple[int, int]) -> List[np.ndarray]:
    logger.debug(f"Extracting SSM shapes for MT3DMS under path: {model_path}")
    mf_nam_file_name = scan_for_modflow_file(model_path)
    mt3dms_nam_file_name = scan_for_modflow_file(model_path, ext=".mt_nam")
    if not mt3dms_nam_file_name:
        logger.debug(f"SSM file not found, solute shapes not generated")
        return []

    modflow_model = flopy.modflow.Modflow.load(mf_nam_file_name,
                                               model_ws=model_path,
                                               load_only=["rch", "bas6"],
                                               )

    mt3dms_model = flopy.mt3d.Mt3dms.load(
        mt3dms_nam_file_name,
        modflowmodel=modflow_model,
        model_ws=model_path,
        load_only=["ssm"],
    )

    ssm_package = mt3dms_model.get_package("ssm")
    stress_period = 0
    layer = 0
    crch_array = ssm_package.crch[0].array[stress_period][layer]
    crch_solute_masks = dfs_shapes(model_shape, crch_array, ignore_zeros=True)
    return crch_solute_masks


def get_shapes_from_rch(model_path: str, model_shape: Tuple[int, int]) -> Tuple[List[np.ndarray], np.ndarray]:
    """
    Defines shapes masks for uploaded Modflow model based on recharge

    @param model_path: Path of Modflow model
    @param model_shape: Tuple representing size of the Modflow project (rows, cols)
    @return: List of shapes read from Modflow project
    """

    logger.debug(f"Extracting RCH shapes for Modflow model under path: {model_path}")
    nam_file_name = scan_for_modflow_file(model_path)
    modflow_model = flopy.modflow.Modflow.load(nam_file_name,
                                               model_ws=model_path,
                                               load_only=["rch", "bas6"],
                                               forgive=True)

    stress_period = 0
    layer = 0
    recharge_array = modflow_model.rch.rech.array[stress_period][layer]
    recharge_masks = dfs_shapes(model_shape, recharge_array, ignore_zeros=True)

    ibound = next(pkg for pkg in modflow_model.packagelist if isinstance(pkg, ModflowBas)).ibound[0].array
    inactive_cells = np.where(ibound == 0, 1, 0)
    return recharge_masks, inactive_cells


def dfs_shapes(model_shape: tuple[int, int], input_array, ignore_zeros: bool = False) -> list[np.ndarray]:
    shape_masks = []
    is_checked_array = np.full(model_shape, False)
    modflow_rows, modflow_cols = model_shape

    for row in range(modflow_rows):
        for col in range(modflow_cols):
            if not is_checked_array[row][col]:
                if ignore_zeros and input_array[row][col] == 0.0:
                    continue

                shape_masks.append(np.zeros(model_shape))
                __fill_mask_iterative(mask=shape_masks[-1], recharge_array=input_array,
                                      is_checked_array=is_checked_array,
                                      project_shape=model_shape,
                                      row=row, col=col,
                                      value=input_array[row][col])
    return shape_masks


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
    swn_file_name = scan_for_modflow_file(model_path, ext=".swn")
    if not nam_file_name and not swn_file_name:
        raise ModflowMissingFileError(description="Invalid Modflow model - .nam file not found!")  # Error doesn't show

    if swn_file_name and not nam_file_name:
        swn_file_path = os.path.join(model_path, swn_file_name)
        nam_file = swn_file_name.replace('.swn', '.nam').replace('.SWN', '.nam')
        renamed_nam_file_path = os.path.join(model_path, nam_file)
        os.rename(swn_file_path, renamed_nam_file_path)
        __fix_seawat_nam_file(renamed_nam_file_path)
        nam_file_name = renamed_nam_file_path

    try:
        # load whole model and validate it
        m = flopy.modflow.Modflow.load(nam_file_name,
                                       model_ws=model_path,
                                       forgive=True,
                                       check=True)
        if m.rch is None:
            raise ModflowMissingFileError(description="Invalid Modflow model - .rch file not found!")
        m.rch.check()
    except (IOError, AttributeError) as e:
        raise ModflowMissingFileError(
            description=f"Invalid Modflow model - validation detected missing files (needed BAS and DIS packages)! ({str(e)})")
    except KeyError as e:
        raise ModflowCommonError(
            description=f"Invalid Modflow model - validation detected an unspecified error! ({str(e)})")

    mt3dms_nam_file = scan_for_modflow_file(model_path, ext=".mt_nam")
    if mt3dms_nam_file:
        mt3dms_model = flopy.mt3d.Mt3dms.load(
            mt3dms_nam_file,
            model_ws=model_path,
            modflowmodel=m,
            forgive=True,
            load_only=["ssm"],
        )
        ssm_package = mt3dms_model.get_package("ssm")
        if not ssm_package:
            ssm_filename = scan_for_modflow_file(model_path, ext=".ssm")
            ssm_file = os.path.join(model_path, ssm_filename)
            __fix_mt3dms_ssm_file(ssm_file)


def __fix_mt3dms_ssm_file(ssm_file: str):
    with open(ssm_file, 'r+', encoding='utf-8') as fp:
        lines = fp.readlines()
        potential_flags_lines_idx = 0
        flags_found = False
        for i in range(len(lines)):
            line = lines[i]
            if line.strip().startswith("#"):
                potential_flags_lines_idx += 1

            flags_search = re.search(r'\s*([TF]\s){3,}\s*', line)
            if flags_search:
                flags_found = True

        fp.seek(0)
        if not flags_found:
            predefined_default_flopy_flags = " F F T F F F F F F F F F F F F F\n"
            lines.insert(potential_flags_lines_idx, predefined_default_flopy_flags)
            fp.writelines(lines)
            fp.truncate()


# Dedicated for GMS
def __fix_seawat_nam_file(swn_file_path: str):
    with open(swn_file_path, 'r+', encoding='utf-8') as fp:
        lines = fp.readlines()
        for i in range(len(lines)):
            line = lines[i]
            quote_match = re.search(r'".+"', line)
            if quote_match:
                found_path = quote_match.group()
                direct_file = os.path.basename(found_path)
                if direct_file == found_path:
                    direct_file = direct_file.split('\\')[-1]
                replaced_line = re.sub(r'".+"', direct_file, line)
                lines[i] = replaced_line
        fp.seek(0)
        fp.writelines(lines)
        fp.truncate()


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


__TIME_UNIT_CONVERSION = {
    'hours': 1.0 / 24.0,
    'days': 1,
}


def find_head_file(modflow_dir: str):
    hed_file = scan_for_modflow_file(modflow_dir, ext=".fhd")
    if not hed_file:
        hed_file = scan_for_modflow_file(modflow_dir, ext=".hed")
    if not hed_file:
        hed_file = scan_for_modflow_file(modflow_dir, ext=".hds")
    return hed_file


def convert_time_units_to_days(duration: float, dur_unit: str) -> int:
    ratio = __TIME_UNIT_CONVERSION.get(dur_unit, 0)
    if ratio == 0:
        raise KeyError(f"Unknown Modflow time unit: {dur_unit}")
    return int(duration * ratio)
