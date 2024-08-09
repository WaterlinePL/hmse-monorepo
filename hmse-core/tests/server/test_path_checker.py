from typing import Optional

import pytest
from werkzeug.wrappers.response import Response

from config import app_config
from config.app_config import ApplicationDeployment
from flask_app import create_app
from server import path_checker, cookie_utils


@pytest.fixture()
def app():
    test_app = create_app()
    test_app.config.update({
        "TESTING": True,
    })

    yield test_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


def test_path_check_cookie_fail_empty_cookie(app):
    with app.test_request_context():
        assert isinstance(path_checker.path_check_cookie(None), Response)


def test_path_check_cookie_success(app):
    with app.test_request_context():
        assert path_checker.path_check_cookie("test-cookie-uuid") is None


@pytest.mark.parametrize(
    "deployment,expected_access_result",
    [
        ("desktop", Response),
        ("docker", None),
        ("k8s", None)
    ]
)
def test_path_check_simulate_access_fail_no_config(app, deployment: str, expected_access_result: Optional[Response]):
    setup_app_config(deployment)
    with app.test_request_context():
        result = path_checker.path_check_simulate_access("test-cookie-uuid")
        if expected_access_result is not None:
            assert isinstance(result, expected_access_result)
        else:
            assert result is None


@pytest.mark.parametrize(
    "deployment,expected_access_result",
    [
        ("desktop", None),
        ("docker", None),
        ("k8s", None)
    ]
)
def test_path_check_simulate_access_success(app, deployment: str, expected_access_result: Optional[Response]):
    config = setup_app_config(deployment)
    if ApplicationDeployment.map_from_str(deployment) == ApplicationDeployment.DESKTOP:
        config.hydrus_program_path = "C:\\hydrus\\path\\H1D_CALC.exe"
        config.modflow_program_path = "C:\\modflow\\path\\mf2005.exe"
    with app.test_request_context():
        assert path_checker.path_check_simulate_access("test-cookie-uuid") is None


@pytest.mark.parametrize(
    "deployment,expected_access_result",
    [
        ("desktop", None),
        ("docker", None),
        ("k8s", Response)
    ]
)
def test_path_check_for_accessing_selected_project_fail_in_use(app,
                                                               deployment: str,
                                                               expected_access_result: Optional[Response]):
    config = setup_app_config(deployment)
    if ApplicationDeployment.map_from_str(deployment) == ApplicationDeployment.DESKTOP:
        config.hydrus_program_path = "C:\\hydrus\\path\\H1D_CALC.exe"
        config.modflow_program_path = "C:\\modflow\\path\\mf2005.exe"

    test_user_id = "test-cookie-uuid"
    another_test_user_id = "test-cookie-uuid-2"
    test_project_id = "test-project"
    cookie_utils.set_project_id_for_user(test_user_id, test_project_id)
    with app.test_request_context():
        result = path_checker.path_check_for_accessing_selected_project(another_test_user_id, test_project_id)
        if expected_access_result is not None:
            assert isinstance(result, expected_access_result)
        else:
            assert result is None


@pytest.mark.parametrize(
    "deployment,expected_access_result",
    [
        ("desktop", None),
        ("docker", None),
        ("k8s", None)
    ]
)
def test_path_check_for_accessing_selected_project_success(app,
                                                           deployment: str,
                                                           expected_access_result: Optional[Response]):
    config = setup_app_config(deployment)
    if ApplicationDeployment.map_from_str(deployment) == ApplicationDeployment.DESKTOP:
        config.hydrus_program_path = "C:\\hydrus\\path\\H1D_CALC.exe"
        config.modflow_program_path = "C:\\modflow\\path\\mf2005.exe"

    test_user_id = "test-cookie-uuid"
    test_project_id = "test-project"
    cookie_utils.set_project_id_for_user(test_user_id, test_project_id)
    with app.test_request_context():
        assert path_checker.path_check_for_accessing_selected_project(test_user_id, test_project_id) is None


def setup_app_config(deployment: str):
    config = app_config.get_config()
    config.deployment = ApplicationDeployment.map_from_str(deployment)
    return config
