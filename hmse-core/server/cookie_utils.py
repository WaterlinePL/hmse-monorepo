from __future__ import annotations

import datetime as dt
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict

from server.typing_help import UserID
from simulations.projects.project_exceptions import ProjectNotFound
from simulations.projects.typing_help import ProjectID

COOKIE_NAME = 'user_id'
COOKIE_AGE = 60 * 60 * 24 * 365
__project_accesses: Dict[ProjectID, CookieInfo] = defaultdict()

logger = logging.getLogger(__name__)


@dataclass
class CookieInfo:
    user_id: UserID
    valid_until: dt.datetime


def set_project_id_for_user(user_id: UserID, project_id: str):
    logger.debug(f"Assigning project {project_id} user {user_id}")
    __project_accesses[project_id] = CookieInfo(
        user_id,
        valid_until=dt.datetime.now() + dt.timedelta(minutes=1)
    )


def is_project_used_by_another_user(project_id: ProjectID, user_id: UserID) -> bool:
    logger.debug(f"Check access for use {user_id} to project {project_id}")
    project_user_info = __project_accesses.get(project_id)
    if project_user_info is None:
        return False
    if project_user_info.user_id == user_id:
        return False
    return dt.datetime.now() <= project_user_info.valid_until


def refresh_user_access(project_id: ProjectID) -> None:
    logger.debug(f"Refreshing user's access to project {project_id}")
    project_user_info = __project_accesses.get(project_id)
    if project_user_info is None:
        raise ProjectNotFound()
    project_user_info.valid_until = dt.datetime.now() + dt.timedelta(minutes=1)
