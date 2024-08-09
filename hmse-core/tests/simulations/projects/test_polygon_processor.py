from typing import List

import numpy as np
import pytest

from config import app_config
from simulations.projects import polygon_processor

TEST_SHAPE_SIZE = (4, 4)

# input:        processed as:
# 0 0 0 0       0 0 0 0 0 0 0 0 0
# 0 0 0 0       0 0 0 0 0 0 0 0 0
# 1 1 1 0       0 0 0 0 0 0 0 0 0
# 0 0 0 0       0 0 0 0 0 0 0 0 0
#               0 0 0 0 0 0 0 0 0
#               0 0 0 0 0 0 0 0 0
#               1 1 1 1 1 1 1 0 0
#               1 1 1 1 1 1 1 0 0
#               0 0 0 0 0 0 0 0 0
SHAPE_1D_HORIZONTAL = np.zeros(TEST_SHAPE_SIZE)
SHAPE_1D_HORIZONTAL[2, :3] = 1
EXPECTED_SHAPE_1D_HORIZONTAL = [
    [0, 4], [0, 5], [0, 6],
    [1, 6], [2, 6], [3, 6], [4, 6], [5, 6], [6, 6],
    [6, 5], [6, 4], [5, 4], [4, 4], [3, 4], [2, 4], [1, 4]
]
EXPECTED_SCALED_SHAPE_1D_HORIZONTAL = [
    [200, 300], [200, 325], [200, 350], [225, 350],
    [250, 350], [275, 350], [300, 350], [325, 350],
    [350, 350], [350, 325], [350, 300], [325, 300],
    [300, 300], [275, 300], [250, 300], [225, 300]
]

# input:        processed as:
# 0 0 1 0       0 0 0 0 0 1 1 0 0
# 0 0 1 0       0 0 0 0 0 1 1 0 0
# 0 0 1 0       0 0 0 0 0 1 1 0 0
# 0 0 1 0       0 0 0 0 0 1 1 0 0
#               0 0 0 0 0 1 1 0 0
#               0 0 0 0 0 1 1 0 0
#               0 0 0 0 0 1 1 0 0
#               0 0 0 0 0 1 1 0 0
#               0 0 0 0 0 1 1 0 0
SHAPE_1D_VERTICAL = np.zeros(TEST_SHAPE_SIZE)
SHAPE_1D_VERTICAL[:, 2] = 1
EXPECTED_SHAPE_1D_VERTICAL = [
    [4, 0], [4, 1], [4, 2], [4, 3], [4, 4],
    [4, 5], [4, 6], [4, 7], [4, 8], [5, 8],
    [6, 8], [6, 7], [6, 6], [6, 5], [6, 4],
    [6, 3], [6, 2], [6, 1], [6, 0], [5, 0]
]
EXPECTED_SCALED_SHAPE_1D_VERTICAL = [
    [300, 200], [300, 225], [300, 250], [300, 275], [300, 300],
    [300, 325], [300, 350], [300, 375], [300, 400], [325, 400],
    [350, 400], [350, 375], [350, 350], [350, 325], [350, 300],
    [350, 275], [350, 250], [350, 225], [350, 200], [325, 200]
]

# input:        processed as:
# 0 0 0 0       0 0 0 0 0 0 0 0 0
# 0 1 1 0       0 0 0 0 0 0 0 0 0
# 0 1 1 0       0 0 1 1 1 1 1 0 0
# 0 0 0 0       0 0 1 1 1 1 1 0 0
#               0 0 1 1 1 1 1 0 0
#               0 0 1 1 1 1 1 0 0
#               0 0 0 0 0 0 0 0 0
#               0 0 0 0 0 0 0 0 0
SHAPE_SQUARE = np.zeros((4, 4))
SHAPE_SQUARE[1:3, 1:3] = 1
EXPECTED_SHAPE_SQUARE = [
    [2, 2], [2, 3], [2, 4], [2, 5],
    [2, 6], [3, 6], [4, 6], [5, 6],
    [6, 6], [6, 5], [6, 4], [6, 3],
    [6, 2], [5, 2], [4, 2], [3, 2],
]
EXPECTED_SCALED_SHAPE_SQUARE = [
    [250, 250], [250, 275], [250, 300], [250, 325],
    [250, 350], [275, 350], [300, 350], [325, 350],
    [350, 350], [350, 325], [350, 300], [350, 275],
    [350, 250], [325, 250], [300, 250], [275, 250]
]


@pytest.fixture(autouse=True)
def app_configuration():
    config = app_config.get_config()
    config.draw_grid_height = 600
    config.draw_grid_width = 600
    config.draw_max_cell_height = 50
    config.draw_max_cell_width = 50


@pytest.mark.parametrize(
    "input_shape,expected_polygon",
    [
        (SHAPE_1D_HORIZONTAL, EXPECTED_SHAPE_1D_HORIZONTAL),
        (SHAPE_1D_VERTICAL, EXPECTED_SHAPE_1D_VERTICAL),
        (SHAPE_SQUARE, EXPECTED_SHAPE_SQUARE),
    ]
)
def test_polygon_extraction(input_shape: np.ndarray, expected_polygon: List):
    polygon, repeats = polygon_processor.get_polygons_from_mask(input_shape)
    assert repeats == [2, 2]
    assert polygon.tolist() == expected_polygon


@pytest.mark.parametrize(
    "input_polygon,expected_scaled_polygon",
    [
        (EXPECTED_SHAPE_1D_HORIZONTAL, EXPECTED_SCALED_SHAPE_1D_HORIZONTAL),
        (EXPECTED_SHAPE_1D_VERTICAL, EXPECTED_SCALED_SHAPE_1D_VERTICAL),
        (EXPECTED_SHAPE_SQUARE, EXPECTED_SCALED_SHAPE_SQUARE),
    ]
)
def test_polygon_scaling(input_polygon: np.ndarray, expected_scaled_polygon: List):
    repeats = [2, 2]
    polygon = np.array(input_polygon, dtype=int)
    scaled_polygon = polygon_processor.scale_polygon(polygon, TEST_SHAPE_SIZE, repeats)
    assert scaled_polygon.tolist() == expected_scaled_polygon
