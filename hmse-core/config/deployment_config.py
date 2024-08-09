import logging
from typing import Callable, Union

from config.app_config import get_config, ApplicationDeployment

__DEPLOYMENT_CLASSES = None
__REQUIRED_CLASSES = set()
__PRE_INIT_CLASSES = {
    ApplicationDeployment.DESKTOP: {},
    ApplicationDeployment.DOCKER: {},
    ApplicationDeployment.K8S: {},
}


__DEPLOYMENT_FUNCTIONS = None
__REQUIRED_FUNCTIONS = set()
__PRE_INIT_FUNCTIONS = {
    ApplicationDeployment.DESKTOP: {},
    ApplicationDeployment.DOCKER: {},
    ApplicationDeployment.K8S: {},
}

logger = logging.getLogger(__name__)


def get_deployment_class(identification: str):
    logger.debug(f"Getting deployment class identified by: {identification}")
    if identification not in __DEPLOYMENT_CLASSES:
        config = get_config()
        raise RuntimeError(f"No {identification} class present in {config.deployment} deployment!")
    found_class = __DEPLOYMENT_CLASSES[identification]
    logger.debug(f"Found class: {found_class.__name__}")
    return found_class


def get_deployment_function(identification: str):
    logger.debug(f"Getting deployment function identified by: {identification}")
    if identification not in __DEPLOYMENT_FUNCTIONS:
        config = get_config()
        raise RuntimeError(f"No {identification} function present in {config.deployment} deployment!")
    found_func = __DEPLOYMENT_FUNCTIONS[identification]
    logger.debug(f"Found function: {found_func.__name__}")
    return found_func


def required(identification: str):
    def class_decorator(cls: type):
        __REQUIRED_CLASSES.add(identification)
        return cls

    return class_decorator


def required_function(identification: str):
    def func_decorator(function: Callable):
        __REQUIRED_FUNCTIONS.add(identification)
        return function

    return func_decorator


def desktop(identification: str):
    def class_decorator(component: Union[type, Callable]):
        return __deployment_component(component, deployment_name=ApplicationDeployment.DESKTOP,
                                      identification=identification)

    return class_decorator


def docker(identification: str):
    def class_decorator(component: Union[type, Callable]):
        return __deployment_component(component, deployment_name=ApplicationDeployment.DOCKER,
                                      identification=identification)

    return class_decorator


def k8s(identification: str):
    def class_decorator(component: Union[type, Callable]):
        return __deployment_component(component, deployment_name=ApplicationDeployment.K8S, identification=identification)

    return class_decorator


def init_deployment_components():
    global __DEPLOYMENT_CLASSES, __DEPLOYMENT_FUNCTIONS
    config = get_config()

    logger.debug(f"Required deployment classes: {__REQUIRED_CLASSES}")
    __DEPLOYMENT_CLASSES = __PRE_INIT_CLASSES[config.deployment]
    for ident in __REQUIRED_CLASSES:
        if ident not in __DEPLOYMENT_CLASSES:
            raise RuntimeError(f"Class identified by '{ident}' is not initialized for this deployment!")

    logger.debug(f"Required deployment functions: {__REQUIRED_FUNCTIONS}")
    __DEPLOYMENT_FUNCTIONS = __PRE_INIT_FUNCTIONS[config.deployment]
    for ident in __REQUIRED_FUNCTIONS:
        if ident not in __DEPLOYMENT_FUNCTIONS:
            raise RuntimeError(f"Function identified by '{ident}' is not initialized for this deployment!")


def __deployment_component(component: Union[type, Callable], deployment_name: ApplicationDeployment, identification: str):
    if isinstance(component, type):
        logger.debug(f"Assigning deployment class: {component.__name__} to ID: {identification}")
        __PRE_INIT_CLASSES[deployment_name][identification] = component
    if isinstance(component, Callable):
        logger.debug(f"Assigning deployment function: {component.__name__} to ID: {identification}")
        __PRE_INIT_FUNCTIONS[deployment_name][identification] = component
    return component
