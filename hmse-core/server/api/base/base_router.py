import uuid
from http import HTTPStatus

import flask
from flask import make_response, render_template, request, Blueprint, url_for
from werkzeug.utils import redirect

from config import app_config
from config.app_config import URL_PREFIX, ApplicationDeployment
from server import endpoints, cookie_utils, template, path_checker

base = Blueprint('base', __name__)


@base.route('/')
def start():
    res = make_response(redirect(url_for("projects.project_list")))
    if not request.cookies.get(cookie_utils.COOKIE_NAME):
        cookie = str(uuid.uuid4())
        res.set_cookie(cookie_utils.COOKIE_NAME, cookie, max_age=cookie_utils.COOKIE_AGE)
    return res


@base.route(endpoints.CONFIGURATION, methods=['GET', 'PUT'])
def configuration():
    check_previous_steps = path_checker.path_check_cookie(request.cookies.get(cookie_utils.COOKIE_NAME))
    if check_previous_steps:
        return check_previous_steps
    if request.method == 'PUT' and app_config.get_config().deployment == ApplicationDeployment.DESKTOP:
        # Config needed only for desktop deployment
        cur_config = app_config.get_config()
        json_config = cur_config.to_json()

        for field, new_val in request.json.items():
            if field in json_config:
                cur_config.__setattr__(field, new_val)

        cur_config.save()
        return flask.Response(status=HTTPStatus.OK)

    return render_template(template.CONFIGURATION, app_config=app_config.get_config(), endpoint_prefix=URL_PREFIX)
