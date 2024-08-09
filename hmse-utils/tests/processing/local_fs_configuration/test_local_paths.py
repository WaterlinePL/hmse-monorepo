import os.path

import pytest

from hmse_utils.processing.local_fs_configuration import local_paths
from hmse_utils.processing.local_fs_configuration.path_constants import get_workspace_local_path, SIMULATION_DIR


@pytest.mark.parametrize(
    "project_id,simulation_mode,expected_root_path",
    [
        ("project1", False, os.path.join(get_workspace_local_path(), "project1")),
        ("project1", True, os.path.join(get_workspace_local_path(), "project1", SIMULATION_DIR)),
        ("project-2", True, os.path.join(get_workspace_local_path(), "project-2", SIMULATION_DIR)),
        ("project3333", False, os.path.join(get_workspace_local_path(), "project3333")),
    ]
)
def test_get_root_dir(project_id: str, simulation_mode: bool, expected_root_path: str):
    assert local_paths.get_root_dir(project_id, simulation_mode) == expected_root_path



@pytest.mark.parametrize(
    "model_name,expect_fixed_model_name",
    [
        ("modflow .1.zip", "modflow--1.zip"),
        ("model name 123.zip", "model-name-123.zip"),
        ("very long model name that exceeds 44 characters.zip", "very-long-model-name-that-exceeds-44-cha.zip"),
    ]
)
def test_fix_model_name(model_name: str, expect_fixed_model_name: str):
    assert local_paths.fix_model_name(model_name) == expect_fixed_model_name
