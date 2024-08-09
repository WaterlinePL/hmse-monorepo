import os.path
from datetime import datetime
from pathlib import Path

import pytest

from hmse_utils.processing.weather_data import weather_util

WEATHER_TEST_DIR = Path(__file__).resolve().parent


@pytest.mark.parametrize(
    "start_date,records_to_read, expected_lines",
    [
        (None, None, 31),  # Read whole
        (datetime(day=13, month=1, year=2000), None, 19),  # Read starting from 1/13/2000 till end of file
        (datetime(day=10, month=1, year=2000), 15, 15),  # Read 15 rows starting from 1/10/2000
    ]
)
def test_reading_swat_csv_whole(start_date: datetime, records_to_read: int, expected_lines: int):
    test_csv_file = os.path.join(WEATHER_TEST_DIR, 'test_weatherdata.csv')
    read_data = weather_util.read_weather_csv(test_csv_file, start_date, records_to_read)
    assert len(read_data) == 10  # 10 columns

    expected_cols = [
        "Date",
        "Longitude",
        "Latitude",
        "Elevation",
        "Max Temperature",
        "Min Temperature",
        "Precipitation",
        "Wind",
        "Relative Humidity",
        "Solar",
    ]

    for col in expected_cols:
        assert col in read_data

        col_data = read_data[col]
        assert len(col_data) == expected_lines

    assert read_data["Date"][0] == (start_date.timetuple().tm_yday - 1 if start_date else 0)

# def test_adapting_data()
