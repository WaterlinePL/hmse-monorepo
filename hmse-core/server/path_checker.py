import logging
from typing import Optional

from flask import Response, redirect, url_for

from config import app_config
from config.app_config import ApplicationDeployment
from server import cookie_utils, endpoints
from server.typing_help import UserID
from simulations.projects import project_service
from simulations.projects.project_exceptions import UnsetModflowModelError, ProjectInUse
from simulations.projects.typing_help import ProjectID

logger = logging.getLogger(__name__)


def path_check_cookie(cookie: UserID) -> Optional[Response]:
    """
    @param cookie: Cookie with user ID.
    @return: Optional redirect to main page with getting cookie.
    """
    logger.debug(f"Checking cookie for user: {cookie}")
    if cookie is None:
        return redirect(url_for("base.start"))
    return None


def path_check_simulate_access(cookie: UserID) -> Optional[Response]:
    """
    @param cookie: Cookie with user ID.
    @return: Optional redirect to configuration if no paths for Hydrus and Modflow are specified.
    """
    check_previous = path_check_cookie(cookie)
    if check_previous:
        return check_previous

    config = app_config.get_config()
    if config.deployment == ApplicationDeployment.DESKTOP:
        logger.debug(f"Checking simulation programs config for user: {cookie}")
        # Here carry out check for local executables or delete for other deployments
        if not (app_config.get_config().hydrus_program_path and app_config.get_config().modflow_program_path):
            return redirect(endpoints.CONFIGURATION)

    return None


def path_check_for_accessing_selected_project(user_id: UserID, project_id: ProjectID):
    check_previous = path_check_simulate_access(user_id)
    if check_previous:
        return check_previous

    config = app_config.get_config()
    check_for_user_project_collision = config.deployment == ApplicationDeployment.K8S
    if check_for_user_project_collision and cookie_utils.is_project_used_by_another_user(project_id, user_id):
        logger.debug(f"Checking access to project {project_id} for user: {user_id}")
        return redirect(url_for('projects.project_list', error=ProjectInUse.query_param))

    return None


def path_check_for_modflow_model(cookie: UserID, project_id: ProjectID) -> Optional[Response]:
    """
    @param cookie: Cookie with user ID.
    @param project_id: Projects ID from url.
    @return: Optional redirect to first incorrect step up to upload_hydrus.
    """

    check_previous = path_check_for_accessing_selected_project(cookie, project_id)
    if check_previous:
        return check_previous

    metadata = project_service.get(project_id)
    logger.debug(f"Checking modflow model for user: {cookie}")
    if not metadata.modflow_metadata:
        raise UnsetModflowModelError()

    return None
