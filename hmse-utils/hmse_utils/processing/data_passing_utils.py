import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Union, List

import flopy
import numpy as np
import pandas as pd
from flopy.modflow import Modflow
from flopy.mt3d import Mt3dms
from flopy.mt3d.mtssm import Mt3dSsm
from flopy.utils import Transient2d, MfList

import phydrus as ph
from hmse_utils.processing import unit_manager
from hmse_utils.processing.hydrus import hydrus_utils, hydrus_model_management
from hmse_utils.processing.hydrus.file_processing.selector_in_processor import SelectorInProcessor
from hmse_utils.processing.local_fs_configuration import local_paths
from hmse_utils.processing.local_fs_configuration.feedback_loop_file_management import find_previous_simulation_step_dir
from hmse_utils.processing.local_fs_configuration.path_constants import get_feedback_loop_hydrus_name
from hmse_utils.processing.modflow import modflow_utils, modflow_model_management
from hmse_utils.processing.modflow.modflow_metadata import ModflowMetadata
from hmse_utils.processing.unit_manager import LengthUnit
from hmse_utils.processing.weather_data import weather_util

logger = logging.getLogger(__name__)


class DataProcessingException(RuntimeError):
    pass


def recharge_from_hydrus_to_modflow(project_id: str,
                                    modflow_metadata: ModflowMetadata,
                                    spin_up: int,
                                    model_to_shapes_mapping: Dict[Union[str, float], List[str]],
                                    feedback_loop: bool = False) -> None:
    """
    @param model_to_shapes_mapping: Hydrus model/float value -> list of shape_id assigned to that shape
    """

    prev_step_dir = find_previous_simulation_step_dir(project_id)
    if prev_step_dir is not None:
        spin_up = 0

    for mapping_val, assigned_shape_ids in model_to_shapes_mapping.items():
        __process_hydrus_shapes(assigned_shape_ids, mapping_val, modflow_metadata,
                                project_id, spin_up)


def solute_recharge_from_hydrus_to_mt3dms(project_id: str,
                                          modflow_metadata: ModflowMetadata,
                                          spin_up: int,
                                          model_to_solute_shapes_mapping: Dict[Union[str, float], List[str]]):
    modflow_path = local_paths.get_modflow_model_path(project_id, modflow_metadata.modflow_id, simulation_mode=True)
    mf_nam_file = modflow_utils.scan_for_modflow_file(modflow_path, ext=".nam")
    mt3dms_nam_file = modflow_utils.scan_for_modflow_file(modflow_path, ext=".mt_nam")

    # load SSM package
    mf_model = flopy.modflow.Modflow.load(mf_nam_file, model_ws=modflow_path)
    mt3dms_model = flopy.mt3d.mt.Mt3dms.load(
        mt3dms_nam_file,
        model_ws=modflow_path,
        modflowmodel=mf_model,
    )
    ssm_package = mt3dms_model.get_package("ssm")

    hydrus5_model = list(model_to_solute_shapes_mapping.keys())[0]
    assigned_ssm_shape_ids = list(model_to_solute_shapes_mapping.values())[0]

    updated_crch = __get_crch_concenration_from_hydrus_per_stress_period(
        project_id,
        ssm_package=ssm_package,
        mapping_val=hydrus5_model,
        modflow_unit=modflow_metadata.grid_unit,
        assigned_ssm_shape_ids=assigned_ssm_shape_ids,
        mt3dms_model=mt3dms_model,
        spin_up=spin_up,
    )

    updated_crch_arr = Transient2d.from_4d(
        model=mt3dms_model,
        pak_name="crch1",
        m4ds={"crch1": updated_crch},
    )

    original_crch = ssm_package.crch[0]
    updated_crch_arr.array_free_format = original_crch.array_free_format
    updated_crch_arr.locat = original_crch.locat

    for i, updated_crch_period in updated_crch_arr.transient_2ds.items():
        original_crch_period = original_crch.transient_2ds[i]
        updated_crch_period.locat = original_crch_period.locat
        updated_crch_period.format = original_crch_period.format

    ssm_package.crch[0] = updated_crch_arr
    ssm_package.write_file()


def __get_crch_concenration_from_hydrus_per_stress_period(project_id: str,
                                                          ssm_package: Mt3dSsm,
                                                          mt3dms_model: Mt3dms,
                                                          assigned_ssm_shape_ids: list[str],
                                                          mapping_val: Union[str, float],
                                                          modflow_unit: LengthUnit,
                                                          spin_up: int):
    per_stress_period_crch = ssm_package.crch[0].array

    hydrus_model_dir = local_paths.get_hydrus_model_path(project_id,
                                                         hydrus_id=mapping_val,
                                                         simulation_mode=True)

    selector_path = hydrus_utils.find_hydrus_file_path(hydrus_model_dir, file_name="selector.in")
    with open(selector_path, 'r', encoding='utf-8') as fp:
        hydrus_len_unit = SelectorInProcessor(fp).get_model_length()
    assert hydrus_len_unit == modflow_unit, "Modflow and Hydrus models have different length units!"

    hydrus_recharge_path = hydrus_utils.find_hydrus_file_path(hydrus_model_dir, file_name="solute1.out")
    solute_out_cbot = ph.read.read_solute(path=hydrus_recharge_path)["cBot"]

    # calc difference for each day (excluding spin_up period)
    if spin_up >= len(solute_out_cbot):
        raise DataProcessingException('Spin up is longer than hydrus model time')

    solute_out_cbot = solute_out_cbot.iloc[spin_up:]
    cbot_unit_aligned = solute_out_cbot

    shapes_for_model = [np.load(local_paths.get_shape_path(project_id, shape_id))
                        for shape_id in assigned_ssm_shape_ids]
    shape = np.amax(shapes_for_model, axis=0) if len(shapes_for_model) > 1 else shapes_for_model[0]
    mask = (shape == 1)  # Frontend sets explicitly 1


    for idx, stress_period_duration in enumerate(mt3dms_model.mf.modeltime.perlen):
        period_duration = int(stress_period_duration)
        period_duration_in_days = modflow_utils.convert_time_units_to_days(
            period_duration,
            mt3dms_model.mf.modeltime.time_units,
        )
        assert period_duration_in_days == 1, "Stress period duration must be equal to 1 for MT3DMS concentration integration!"

        cbot_val = cbot_unit_aligned[idx]
        per_stress_period_crch[idx, ..., mask] = cbot_val  # TODO
        ssm_package.stress_period_data.data[idx][0][3] = cbot_val   # CSS
        ssm_package.stress_period_data.data[idx][0][4] = -1   # ISSTYPE

    return per_stress_period_crch


def __get_crch_flux_from_hydrus(project_id: str,
                                mt3dms_model: Mt3dms,
                                assigned_ssm_shape_ids: list[str],
                                per_stress_period_crch: np.ndarray,
                                mapping_val: Union[str, float],
                                modflow_unit: LengthUnit,
                                spin_up: int):
    hydrus_model_dir = local_paths.get_hydrus_model_path(project_id,
                                                         hydrus_id=mapping_val,
                                                         simulation_mode=True)

    selector_path = hydrus_utils.find_hydrus_file_path(hydrus_model_dir, file_name="selector.in")
    with open(selector_path, 'r', encoding='utf-8') as fp:
        hydrus_len_unit = SelectorInProcessor(fp).get_model_length()

    hydrus_solute_path = hydrus_utils.find_hydrus_file_path(hydrus_model_dir, file_name="solute1.out")
    solute_out = ph.read.read_solute(path=hydrus_solute_path)["Sum(cvBot)"]

    # calc difference for each day (excluding spin_up period)
    if spin_up >= len(solute_out):
        raise DataProcessingException('Spin up is longer than hydrus model time')

    solute_out = solute_out.iloc[spin_up:]

    modflow_unit_coef = unit_manager.convert_units(value=1,
                                                   from_unit=hydrus_len_unit,
                                                   to_unit=modflow_unit)
    # Sign opposite to the Hydrus and in modflow units
    sum_cv_bot = -solute_out * modflow_unit_coef

    shapes_for_model = [np.load(local_paths.get_shape_path(project_id, shape_id))
                        for shape_id in assigned_ssm_shape_ids]

    shape = np.amax(shapes_for_model, axis=0) if len(shapes_for_model) > 1 else shapes_for_model[0]
    mask = (shape == 1)  # Frontend sets explicitly 1
    stress_period_duration_iter = 0

    for idx, stress_period_duration in enumerate(mt3dms_model.mf.modeltime.perlen):
        period_duration = int(stress_period_duration)
        period_duration_in_days = modflow_utils.convert_time_units_to_days(
            period_duration,
            mt3dms_model.mf.modeltime.time_units,
        )

        final_sp_recharge = sum_cv_bot.values[
            min(stress_period_duration_iter + period_duration_in_days, len(sum_cv_bot) - 1)]
        starting_sp_recharge = sum_cv_bot.values[stress_period_duration_iter]
        avg_sum_cv_bot = (final_sp_recharge - starting_sp_recharge) / period_duration  # Keeping old time units
        per_stress_period_crch[idx, ..., mask] = avg_sum_cv_bot  # TODO

        # update stress period duration iterator
        stress_period_duration_iter += period_duration_in_days
    return per_stress_period_crch


def __process_hydrus_shapes(assigned_shape_ids, mapping_val, modflow_metadata: ModflowMetadata,
                            project_id: str, spin_up: int):
    modflow_path = local_paths.get_modflow_model_path(project_id, modflow_metadata.modflow_id, simulation_mode=True)
    nam_file = modflow_utils.scan_for_modflow_file(modflow_path)

    # load MODFLOW model - basic info and RCH package
    modflow_model = flopy.modflow.Modflow.load(nam_file, model_ws=modflow_path,
                                               load_only=["rch"],
                                               forgive=True)

    shapes_for_model = [np.load(local_paths.get_shape_path(project_id, shape_id))
                        for shape_id in assigned_shape_ids]

    sum_v_bot = __get_sum_vbot(project_id, mapping_val, modflow_metadata.grid_unit, spin_up)
    __recharge_update(modflow_model, shapes_for_model, sum_v_bot)

    new_recharge = modflow_model.rch.rech
    rch_package = modflow_model.get_package("rch")  # get the RCH package
    # generate and save new RCH (same properties, different recharge)
    flopy.modflow.ModflowRch(modflow_model, nrchop=rch_package.nrchop, ipakcb=rch_package.ipakcb,
                             rech=new_recharge,
                             irch=rch_package.irch).write_file(check=False)


def __get_sum_vbot(project_id: str,
                   mapping_val: Union[str, float],
                   modflow_unit: LengthUnit,
                   spin_up: int) -> Union[pd.DataFrame, float]:
    logger.debug(f"Getting sum(vBot) for project {project_id} using hydrus model/static value: {mapping_val}")
    hydrus_model_dir = local_paths.get_hydrus_model_path(project_id,
                                                         hydrus_id=mapping_val,
                                                         simulation_mode=True)

    selector_path = hydrus_utils.find_hydrus_file_path(hydrus_model_dir, file_name="selector.in")
    with open(selector_path, 'r', encoding='utf-8') as fp:
        hydrus_len_unit = SelectorInProcessor(fp).get_model_length()

    assert hydrus_len_unit == modflow_unit, "Modflow and Hydrus models have different length units!"

    if isinstance(mapping_val, str):
        hydrus_recharge_path = hydrus_utils.find_hydrus_file_path(hydrus_model_dir, file_name="t_level.out")
        sum_v_bot = ph.read.read_tlevel(path=hydrus_recharge_path)['sum(vBot)']

        if math.isnan(sum_v_bot.iloc[-1]):
            sum_v_bot = sum_v_bot.iloc[:-1]

        # calc difference for each day (excluding spin_up period)
        if spin_up >= len(sum_v_bot):
            raise DataProcessingException('Spin up is longer than hydrus model time')

        sum_v_bot = sum_v_bot.iloc[spin_up:]

        # modflow_unit_coef = unit_manager.convert_units(value=1,
        #                                                from_unit=hydrus_len_unit,
        #                                                to_unit=modflow_unit)
        # Sign opposite to the Hydrus and in modflow units
        return -sum_v_bot  # * modflow_unit_coef
    elif isinstance(mapping_val, float):
        return mapping_val
    else:
        raise DataProcessingException("Unknown mapping in simulation!")


def __recharge_update(modflow_model: Modflow, shapes_for_model: List[np.ndarray], sum_v_bot: pd.Series):
    logger.debug(f"Updating modflow RCH package")
    shape = np.amax(shapes_for_model, axis=0) if len(shapes_for_model) > 1 else shapes_for_model[0]
    mask = (shape == 1)  # Frontend sets explicitly 1
    stress_period_duration_iter = 0

    for idx, stress_period_duration in enumerate(modflow_model.modeltime.perlen):
        if not modflow_model.modeltime.steady_state[idx]:
            # modflow rch array for given stress period
            recharge_modflow_array = modflow_model.rch.rech[idx].array

            # add calculated hydrus average sum(vBot) to modflow recharge array
            period_duration = int(stress_period_duration)
            period_duration_in_days = modflow_utils.convert_time_units_to_days(
                period_duration,
                modflow_model.modeltime.time_units,
            )

            # Hydrus is in days
            if period_duration == 1 and idx == 0:
                rch_update = sum_v_bot.values[stress_period_duration_iter]
            else:
                final_sp_recharge = sum_v_bot.values[stress_period_duration_iter]
                starting_sp_recharge = sum_v_bot.values[stress_period_duration_iter - 1]
                rch_update = (final_sp_recharge - starting_sp_recharge) / period_duration  # Keeping old time units

            recharge_modflow_array[mask] = rch_update

            # save calculated recharge to modflow model
            modflow_model.rch.rech[idx] = recharge_modflow_array

            # update stress period duration iterator
            stress_period_duration_iter += period_duration_in_days


def transfer_water_level_to_hydrus(project_id: str,
                                   hydrus_id: str,
                                   modflow_metadata: ModflowMetadata,
                                   shape_id: str,
                                   use_modflow_results: bool = True) -> None:
    logger.debug(f"Transferring water level to hydrus model {hydrus_id} in project: {project_id}")
    compound_hydrus_id = get_feedback_loop_hydrus_name(hydrus_id, shape_id)
    water_avg_depth = modflow_model_management.get_avg_water_depth_for_shape(project_id=project_id,
                                                                             modflow_id=modflow_metadata.modflow_id,
                                                                             shape_id=shape_id,
                                                                             use_modflow_results=use_modflow_results)
    hydrus_profile_depth, hydrus_depth_unit = hydrus_model_management.get_profile_depth(project_id,
                                                                                        hydrus_id=compound_hydrus_id)

    assert modflow_metadata.grid_unit == hydrus_depth_unit, "Modflow and Hydrus models have different length units!"
    water_avg_depth = unit_manager.convert_units(water_avg_depth,
                                                 from_unit=modflow_metadata.grid_unit,
                                                 to_unit=hydrus_depth_unit)

    hydrus_model_management.update_bottom_pressure(project_id=project_id,
                                                   hydrus_id=compound_hydrus_id,
                                                   hydrus_profile_depth=hydrus_profile_depth,
                                                   water_avg_depth=water_avg_depth,
                                                   hydrus_unit=hydrus_depth_unit)


def pass_weather_data_to_hydrus(project_id: str, start_date: str, spin_up: int,
                                modflow_metadata: ModflowMetadata,
                                hydrus_to_weather_mapping: Dict[str, str]) -> None:
    for hydrus_id, weather_id in hydrus_to_weather_mapping.items():
        hydrus_path = local_paths.get_hydrus_model_path(project_id, hydrus_id, simulation_mode=True)
        selector_in_path = hydrus_utils.find_hydrus_file_path(hydrus_path, file_name="selector.in")

        with open(selector_in_path, 'r', encoding='utf-8') as fp:
            hydrus_length_unit = SelectorInProcessor(fp).get_model_length()

        data_start_date = datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=spin_up) if start_date else None
        raw_data = weather_util.read_weather_csv(local_paths.get_weather_model_path(project_id, weather_id),
                                                 start_date=data_start_date,
                                                 record_count=1 + modflow_metadata.get_duration() + spin_up)
        ready_data = weather_util.adapt_data(raw_data, hydrus_length_unit)
        success = weather_util.add_weather_to_hydrus_model(hydrus_path, ready_data)
        if not success:
            raise DataProcessingException(f"Error occurred during applying "
                                          f"weather file {weather_id} to hydrus model {hydrus_id}")
