import logging

__WORKSPACE_PATH = "workspace"
SIMULATION_DIR = "simulation"

METADATA_FILENAME = "metadata.json"
MODFLOW_OUTPUT_JSON = "results.json"

logger = logging.getLogger(__name__)


def get_feedback_loop_hydrus_name(hydrus_id: str, shape_id: str) -> str:
    return f"{hydrus_id}--{shape_id}"


def update_workspace_local_path(new_path: str):
    global __WORKSPACE_PATH
    logger.debug(f"Updating workspace path from {__WORKSPACE_PATH} to {new_path}")
    __WORKSPACE_PATH = new_path


def get_workspace_local_path():
    return __WORKSPACE_PATH
