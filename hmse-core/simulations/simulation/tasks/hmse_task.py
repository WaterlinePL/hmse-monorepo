# Decorator for checking metadata in function
from functools import wraps
from typing import Callable

from simulations.projects.project_metadata import ProjectMetadata
from simulations.simulation.simulation_enums import SimulationStageName

__TASK_TO_NAME_MAPPING = {}


def hmse_task(stage_name: SimulationStageName):
    def hmse_decorator(func: Callable):
        @wraps(func)
        def checking_wrapper(*args, **kwargs):
            total_args = list(args) + list(kwargs.values())
            if not any(map(lambda arg: isinstance(arg, ProjectMetadata), total_args)):
                raise RuntimeError("HMSE task requires ProjectMetadata as an argument")
            kwargs["stage_name"] = stage_name
            return func(*args, **kwargs)

        __TASK_TO_NAME_MAPPING[func.__name__] = stage_name
        return checking_wrapper

    return hmse_decorator


def get_stage_name(task: Callable):
    return __TASK_TO_NAME_MAPPING[task.__name__]
