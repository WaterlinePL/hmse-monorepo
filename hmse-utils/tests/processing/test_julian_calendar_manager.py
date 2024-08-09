import pytest

from hmse_utils.processing import julian_calendar_manager


@pytest.mark.parametrize(
    "timestep_float,expected_julian_timestep",
    [
        (10.0, 10.0),
        (25.99, 25.99),
        (364.99, 364.99),
        (365, 0),
        (365.99, 0.99),
        (366, 1),  # No leap years handling - a simplification
        (370, 5),
        (380.10, 15.10),
        (750, 20),
        (755.99, 25.99),
    ]
)
def test_rounding_float_to_julian(timestep_float: float, expected_julian_timestep: float):
    assert julian_calendar_manager.float_to_julian(timestep_float) == expected_julian_timestep


@pytest.mark.parametrize(
    "input_date,expected_julian_day",
    [
        # Format is: M/D/YYYY, e.g. 4/1/2024 is April 1st 2024
        ('1/1/2024', 0),
        ('8/20/2019', 231),
        ('4/1/2022', 90),
        ('4/1/2020', 91),
        ('12/31/2023', 364),  # No leap year
        ('12/31/2024', 365),  # Leap year - here we detect it
    ]
)
def test_date_conversion_to_julian(input_date: str, expected_julian_day: float):
    assert julian_calendar_manager.date_to_julian(input_date) == pytest.approx(expected_julian_day, 0.01)
