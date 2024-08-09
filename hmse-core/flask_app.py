import json
import os.path
import sys
from http.client import HTTPException

from flask import Flask

from config.app_config import URL_PREFIX
from server.api.base.base_router import base
from server.api.projects.projects_router import projects
from server.api.simulation.simulation_router import simulations


def create_app():
    template_folder = os.path.join("server", "templates")
    static_folder = os.path.join("server", "static")

    if getattr(sys, 'frozen', False):
        # For PyInstaller
        template_folder = os.path.join(sys._MEIPASS, template_folder)
        static_folder = os.path.join(sys._MEIPASS, static_folder)

    app = Flask("App",
                template_folder=template_folder,
                static_folder=static_folder)
    app.register_blueprint(base, url_prefix=URL_PREFIX)
    app.register_blueprint(projects, url_prefix=URL_PREFIX)
    app.register_blueprint(simulations, url_prefix=URL_PREFIX)

    @app.errorhandler(HTTPException)
    def api_error_handler(e):
        """Return JSON instead of HTML for HTTP errors."""
        # start with the correct headers and status code from the error
        response = e.get_response()
        # replace the body with JSON
        response.data = json.dumps({
            "code": e.code,
            "name": e.name,
            "description": e.description,
        })
        response.content_type = "application/json"
        return response

    return app
