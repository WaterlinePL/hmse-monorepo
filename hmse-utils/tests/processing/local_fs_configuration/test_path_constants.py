from hmse_utils.processing.local_fs_configuration import path_constants

DEFAULT_WORKSPACE = 'workspace'


def test_workspace_path_update():
    assert path_constants.get_workspace_local_path() == DEFAULT_WORKSPACE
    new_workspace = "./test/workspace"
    path_constants.update_workspace_local_path(new_workspace)
    assert path_constants.get_workspace_local_path() == new_workspace
