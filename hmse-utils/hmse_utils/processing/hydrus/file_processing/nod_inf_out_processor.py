import logging
import re
from dataclasses import dataclass
from typing import List

from hmse_utils.processing.hydrus.file_processing.text_file_processor import TextFileProcessor

logger = logging.getLogger(__name__)


@dataclass
class NodInfOutProcessor(TextFileProcessor):

    def read_node_pressure(self) -> List[float]:
        logger.debug(f"Reading output node pressure in Hydrus profile")
        pressure_data = []
        for line in self.fp.readlines():
            line = line.replace('\t', ' ')
            if line.strip().startswith("[L]"):
                pressure_data = []
            elif re.match(r'^\d+ ', line.strip()):
                pressure_value, _ = TextFileProcessor._read_value_from_col(line, col_idx=2)
                pressure_data.append(float(pressure_value))
        return pressure_data
