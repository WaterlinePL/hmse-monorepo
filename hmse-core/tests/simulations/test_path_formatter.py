import sys

import pytest

from simulations import path_formatter


@pytest.mark.parametrize(
    "abs_dir_path,expected_docker_volume_path,simulated_platform",
    [
        (
                "/home/sample_user/Documents/workspace",
                "/home/sample_user/Documents/workspace",
                "linux"
        ),
        (
                "/Users/SampleUser/Documents/hmse_workspace",
                "/Users/SampleUser/Documents/hmse_workspace",
                "darwin"
        ),
        (
                "C:\\Users\\SampleUser\\Desktop\\hmse\\workspace",
                "/run/desktop/mnt/host/c/Users/SampleUser/Desktop/hmse/workspace",
                "win32"
        ),
    ]
)
def test_formatting_path_to_docker(abs_dir_path: str, expected_docker_volume_path: str, simulated_platform: str):
    sys.platform = simulated_platform  # Platform variable injection
    assert path_formatter.format_path_to_docker(abs_dir_path) == expected_docker_volume_path
