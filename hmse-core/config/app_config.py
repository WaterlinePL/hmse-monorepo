import json
import logging
import os
from copy import copy
from dataclasses import dataclass
from enum import auto
from typing import Optional

from strenum import StrEnum

__CONFIG_FILENAME = "config.json"
URL_PREFIX = os.environ.get("HMSE_URL_PREFIX", "")

logger = logging.getLogger(__name__)


class ApplicationDeployment(StrEnum):
    DESKTOP = auto()
    DOCKER = auto()
    K8S = auto()

    @staticmethod
    def map_from_str(val: str):
        lowercase_val = val.lower()
        if lowercase_val == "desktop":
            return ApplicationDeployment.DESKTOP
        elif lowercase_val == "docker":
            return ApplicationDeployment.DOCKER
        elif lowercase_val == "k8s":
            return ApplicationDeployment.K8S
        else:
            raise KeyError("Unknown deployment type!")


@dataclass
class AppConfig:
    draw_grid_width: int = 600
    draw_grid_height: int = 600
    draw_max_cell_width: int = 50
    draw_max_cell_height: int = 50
    deployment: ApplicationDeployment = ApplicationDeployment.DESKTOP

    # desktop specific config
    modflow_program_path: Optional[str] = None
    hydrus_program_path: Optional[str] = None

    # docker specific config
    docker_volume_overwrite: Optional[str] = None  # Used only for HMSE runner script

    def to_json(self):
        return self.__dict__

    def save(self):
        json_cfg = copy(self.to_json())
        json_cfg.pop("deployment")
        json_cfg.pop("docker_volume_overwrite")
        logger.info(f"Saving app config: {json_cfg}")
        with open(get_config_location(), 'w') as handle:
            json.dump(json_cfg, handle, indent=2)

    @staticmethod
    def setup():
        if not os.path.exists(get_config_location()):
            logger.info("Creating application config")
            with open(get_config_location(), 'w') as handle:
                conf = AppConfig()
                json.dump(conf.to_json(), handle, indent=2)
                return conf

        logger.info(f"Loading application config from file: {get_config_location()}")
        with open(get_config_location(), 'r') as handle:
            return AppConfig(**json.load(handle))


def get_config() -> AppConfig:
    global __app_config_instance
    if __app_config_instance is None:
        __app_config_instance = AppConfig.setup()
    return __app_config_instance


def get_config_location() -> str:
    return __CONFIG_FILENAME


def set_config_location(new_config_location: str) -> None:
    global __CONFIG_FILENAME, __app_config_instance
    logger.info(f"Updating config path from {__CONFIG_FILENAME} to {new_config_location}")
    __CONFIG_FILENAME = new_config_location
    logger.info(f"Refreshing config from file: {new_config_location}")
    new_config = AppConfig.setup()
    old_config = __app_config_instance
    if old_config is not None:
        new_config.deployment = old_config.deployment
        new_config.docker_volume_overwrite = old_config.docker_volume_overwrite
    __app_config_instance = new_config


__app_config_instance = None
