import logging
import re
import sys

DOCKER_CONST_PATH = "/run/desktop/mnt/host"

logger = logging.getLogger(__name__)


def format_path_to_docker(abs_dir_path: str) -> str:
    """
    Format windows paths to docker format "/run/desktop/mnt/host/c/..."
    @param abs_dir_path: Path to modflow/hydrus project directory
    @return: Formatted path -> str
    """

    if sys.platform in ("linux", "linux2", "linux3", "darwin"):
        return abs_dir_path
    path_split = re.split("\\\\|:\\\\", abs_dir_path)
    path_split[0] = path_split[0].lower()
    linux_path = DOCKER_CONST_PATH + '/' + '/'.join(path_split)
    logger.debug(f"Formatting path {abs_dir_path} to docker volume: {linux_path}")
    return linux_path


def convert_backslashes_to_slashes(path: str):
    return path.replace('\\', "/")
