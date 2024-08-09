import logging
import os
from abc import ABC, abstractmethod

import docker as docker
from docker.errors import ImageNotFound

from config.app_config import get_config

logger = logging.getLogger(__name__)


class AbstractDockerDeployer(ABC):

    def __init__(self):
        self.docker_client = docker.APIClient()
        try:
            self.docker_client.inspect_image(self.get_docker_image_name())
            logger.info(f"Detected image: {self.get_docker_image_name()}")
        except ImageNotFound:
            logger.info(f"Pulling image: {self.get_docker_image_name()}")
            logger.info(self.docker_client.pull(repository=self.get_docker_image_name(),
                                                tag=self.get_image_tag()))
        volume_overwrite = get_config().docker_volume_overwrite
        overwritten_volume = os.path.abspath(volume_overwrite) if volume_overwrite else None
        self.workspace_volume = (
            overwritten_volume or     # HMSE runner
            AbstractDockerDeployer._get_workspace_mount(
                self.docker_client.inspect_container(os.environ["HOSTNAME"])['Mounts']  # docker webapp
            )
        )
        logger.debug(f"Using following volume as workspace: {self.workspace_volume}")

        self.container_name = None  # Needed before abstract method attached the name
        self.container_name = self.get_container_name()

    @abstractmethod
    def get_container_name(self):
        ...

    @abstractmethod
    def get_docker_image_name(self):
        ...

    @abstractmethod
    def get_docker_repo_name(self):
        ...

    @abstractmethod
    def run_simulation_image(self):
        ...

    def get_image_tag(self):
        return "latest"

    def wait_for_termination(self):
        self.docker_client.wait(self.get_container_name())
        # self.docker_client.remove_container(self.get_container_name())
        logger.info(f"{self.get_container_name()}: calculations completed successfully")

    @staticmethod
    def _get_workspace_mount(mounts):
        socket_path = "/var/run/docker.sock"
        for mount in mounts:
            if socket_path not in mount['Source']:
                return mount['Source']
