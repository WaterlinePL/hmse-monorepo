import argparse
import logging
import webbrowser

from config import deployment_config, app_config
from config.app_config import ApplicationDeployment
from flask_app import create_app

logger = logging.getLogger(__name__)

app = create_app()


def prepare_launch_cli():
    arg_parser = argparse.ArgumentParser(
        prog="HMSE webserver",
        description="Hydrus-Modflow Synergy Engine webserver",
    )
    arg_parser.add_argument(
        "-d", "--deployment",
        help="Application version that should be launched (for particular deployment)",
        choices=["desktop", "docker", "k8s"],
        default="desktop",
    )
    arg_parser.add_argument(
        "-p", "--port",
        type=int,
        help="Port on which HTTP server will be launched",
        default=8080,
    )
    arg_parser.add_argument(
        "-l", "--log",
        help="Application logging level",
        choices=["debug", "info", "warn", "error"],
        default="info",
    )
    return arg_parser


def main():
    # input argument parsing
    arg_parser = prepare_launch_cli()
    args = arg_parser.parse_args()
    logging.basicConfig(level=args.log.upper())
    logger.debug(f"Started with following parameters: {args}")

    # validate and setup deployment
    config = app_config.get_config()
    config.deployment = ApplicationDeployment.map_from_str(args.deployment)
    logger.info(f"Launched {config.deployment} deployment")
    deployment_config.init_deployment_components()

    # run flask app
    port = args.port
    if args.deployment == "desktop":
        webbrowser.open(f"http://localhost:{port}")
    app.run(host="0.0.0.0", port=port)


if __name__ == '__main__':
    main()
