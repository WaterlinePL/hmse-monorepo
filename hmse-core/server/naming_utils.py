import logging
from typing import List

MAX_LENGTH = 20

logger = logging.getLogger(__name__)


def validate_project_id(id_to_parse: str):
    logger.debug(f"Validating project id: {id_to_parse}")
    id_without_spaces = '-'.join(__words_without_spaces(id_to_parse))
    return id_without_spaces.replace('_', '-')


def __words_without_spaces(id_to_parse: str) -> List[str]:
    return [word.lower().strip() for word in id_to_parse.split(' ')]
