import logging
from typing import Tuple, List

import cv2
import numpy as np
import scipy

from config import app_config

logger = logging.getLogger(__name__)


# Produces a single polygon for a shape
def get_polygons_from_mask(mask: np.ndarray) -> Tuple[np.ndarray, List[int]]:
    logger.debug(f"Creating polygon for mask with following shape: {mask.shape}")
    processed_mask = mask.astype(int)
    rep_cnt = [2, 2]
    processed_mask = processed_mask.repeat(2, axis=0)
    processed_mask = processed_mask.repeat(2, axis=1)

    # Add additional row & col
    padded_mask = np.zeros((processed_mask.shape[0] + 1, processed_mask.shape[1] + 1), dtype=int)
    padded_mask[1:, :processed_mask.shape[1]] = processed_mask
    conv_kernel = np.array([[1, 1],
                            [1, 1]])

    # Make all shapes overlap so that shape detection makes better over overlap while drawing adjacent shapes
    flip_axis = 0
    processed_mask = scipy.signal.convolve2d(np.flip(padded_mask, flip_axis), conv_kernel, boundary='symm', mode='same')
    processed_mask[(processed_mask == 2) | (processed_mask == 3) | (processed_mask == 4)] = 1
    processed_mask = np.flip(processed_mask, flip_axis)

    polygons, _ = cv2.findContours(processed_mask, cv2.RETR_FLOODFILL, cv2.CHAIN_APPROX_NONE)
    if polygons:
        shape_polygon = polygons[-1].reshape((-1, 2))
    else:
        shape_polygon = np.array([[0, 0]])
    logger.debug(f"Created polygon with {shape_polygon.shape[0]} points and scaling factors {rep_cnt}")
    return shape_polygon, rep_cnt


def scale_polygon(polygon_arr: np.ndarray, original_shape: Tuple[int, ...], repeats: List[int]) -> np.ndarray:
    logger.debug(f"Scaling polygon with {polygon_arr.shape[0]} points using scaling factors {repeats}")

    config = app_config.get_config()
    grid_width = config.draw_grid_width
    grid_height = config.draw_grid_height
    cell_max_width = config.draw_max_cell_width
    cell_max_height = config.draw_max_cell_height

    actual_draw_grid_width = min(grid_width, cell_max_width * original_shape[1])
    actual_draw_grid_height = min(grid_height, cell_max_height * original_shape[0])

    # Centering offset
    horizontal_offset, vertical_offset = __calculate_draw_offset(grid_width, grid_height,
                                                                 actual_draw_grid_width, actual_draw_grid_height)

    polygon_arr[:, 0] = polygon_arr[:, 0] / (repeats[1] * original_shape[1]) * actual_draw_grid_width + horizontal_offset
    polygon_arr[:, 1] = polygon_arr[:, 1] / (repeats[0] * original_shape[0]) * actual_draw_grid_height + vertical_offset
    polygon_arr.round()
    return polygon_arr.astype(int)


def __calculate_draw_offset(grid_width: int, grid_height: int, actual_draw_grid_width: int, actual_draw_grid_height: int):
    vertical_offset = (grid_height - actual_draw_grid_height) / 2
    horizontal_offset = (grid_width - actual_draw_grid_width) / 2
    return horizontal_offset, vertical_offset
