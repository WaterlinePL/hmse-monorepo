import logging
from dataclasses import dataclass
from typing import Tuple

from hmse_utils.processing.hydrus.file_processing.line_by_line_processor import LineByLineProcessor

logger = logging.getLogger(__name__)


@dataclass
class AtmosphInProcessor(LineByLineProcessor):

    def truncate_file(self, data_start_idx: int, data_count: int) -> Tuple[float, float]:
        logger.debug(f"Truncating data in Atmosph.in file preserving {data_count} records starting from {data_start_idx}")
        return self._perform_truncating(data_content_line_prefix="tAtm",
                                        total_record_count_line_prefix="MaxAL",
                                        data_start_idx=data_start_idx,
                                        data_count=data_count)
