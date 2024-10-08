from werkzeug.exceptions import HTTPException


class ProjectNotFound(HTTPException):
    code = 404
    description = "Project not found!"


class ProjectNotSelected(HTTPException):
    code = 403
    description = "Project not selected!"


class ProjectInUse(HTTPException):
    code = 403
    description = ("Project in use by another user or open in another web browser "
                   "(in that case wait around 1 minute after closing).")
    query_param = "project-in-use"


class ProjectSimulationNotFinishedError(HTTPException):
    code = 403
    description = "Cannot download - project simulation not finished!"


class ProjectSimulationInProgressError(HTTPException):
    code = 403
    description = "Cannot download - project simulation not finished!"


class UnknownHydrusModel(HTTPException):
    code = 404
    description = "Unknown Hydrus model!"


class UnknownModflowModel(HTTPException):
    code = 404
    description = "Unknown Modflow model!"


class UnsetModflowModelError(HTTPException):
    code = 409
    description = "Modflow model is not set!"


class UnknownShape(HTTPException):
    code = 404
    description = "Unknown shape!"


class UnknownWeatherFile(HTTPException):
    code = 404
    description = "Unknown weather file!"


class DuplicateHydrusModel(HTTPException):
    code = 409
    description = "Hydrus model with same ID already present in project"


class DuplicateModflowModel(HTTPException):
    code = 409
    description = "Modflow model with same ID already present in project"


class DuplicateWeatherFile(HTTPException):
    code = 409
    description = "Weather file with same ID already present in project"
