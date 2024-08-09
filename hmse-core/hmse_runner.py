import logging
from argparse import ArgumentParser
from time import sleep

import hmse_utils.processing.local_fs_configuration.path_constants as path_consts
from config import app_config, deployment_config
from config.app_config import ApplicationDeployment
from simulations import simulation_service
from simulations.projects import project_service

logger = logging.getLogger(__name__)


def __create_parser() -> ArgumentParser:
    arg_parser = ArgumentParser(
        prog="HMSE runner CLI",
        description="Command line interface for running HMSE simulation projects",
    )
    arg_parser.add_argument(
        "-p", "--project-id",
        dest="project_id",
        required=True,
        help="ID (name) of project to run"
    )
    arg_parser.add_argument(
        "-w", "--workspace",
        dest="workspace",
        required=True,
        help="Local path to workspace"
    )
    arg_parser.add_argument(
        "-d", "--deployment",
        help="Application version that should be launched (for particular deployment)",
        choices=["desktop", "docker"],
        default="desktop"
    )
    arg_parser.add_argument(
        "--with-hydrus",
        dest="with_hydrus",
        help="Path to Hydrus executable that should be set for HMSE (desktop only, precedence over config.json), "
                 "e.g. --with-hydrus=\"C:\\modflow\\bin\\mf2005.exe\"",
    )
    arg_parser.add_argument(
        "--with-modflow",
        dest="with_modflow",
        help="Path to Modflow executable that should be set for HMSE (desktop only, precedence over config.json), "
             "e.g. --with-modflow=\"C:\\Hydrus-1D 4.xx\\H1D_CALC.exe\"",
    )
    arg_parser.add_argument(
        "--with-config",
        dest="with_config",
        help="Path to HMSE config file (config.json), which contains paths to "
             "hydrus and modflow executables (desktop only), e.g. --with-config=.\\config.json",
    )
    arg_parser.add_argument(
        "-l", "--log",
        help="Application logging level",
        choices=["debug", "info", "warn", "error"],
        default="info"
    )
    return arg_parser


def main():
    parser = __create_parser()
    cli_kwargs = parser.parse_args()
    project_id = cli_kwargs.project_id
    logging.basicConfig(level=cli_kwargs.log.upper())
    logger.debug(f"Started HMSE runner with following parameters: {cli_kwargs}")

    # validate and setup deployment
    if cli_kwargs.with_config:
        app_config.set_config_location(cli_kwargs.with_config)
    config = app_config.get_config()
    config.deployment = ApplicationDeployment.map_from_str(cli_kwargs.deployment)
    logger.info(f"Launched HMSE runner as {config.deployment} deployment")
    deployment_config.init_deployment_components()

    path_consts.update_workspace_local_path(cli_kwargs.workspace)

    if config.deployment == ApplicationDeployment.DOCKER:
        config.docker_volume_overwrite = cli_kwargs.workspace

    if cli_kwargs.with_hydrus:
        config.hydrus_program_path = cli_kwargs.with_hydrus
    if cli_kwargs.with_modflow:
        config.hydrus_program_path = cli_kwargs.with_hydrus

    metadata = project_service.get(project_id)
    simulation_service.get().run_simulation(metadata)

    sim_finished = False
    while not sim_finished:
        sleep(1)
        all_chapter_statuses = simulation_service.get().check_simulation_status(metadata.project_id)
        sim_finished = all_chapter_statuses[-1].get_stages_statuses()[-1].status.is_finished()


if __name__ == "__main__":
    main()
