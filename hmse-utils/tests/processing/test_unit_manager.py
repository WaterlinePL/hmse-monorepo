import pytest

from hmse_utils.processing import unit_manager
from hmse_utils.processing.unit_manager import LengthUnit


@pytest.mark.parametrize(
    "input_alias,expected_output",
    [
        ("mm", LengthUnit.mm),
        ("cm", LengthUnit.cm),
        ("m", LengthUnit.m),
        ("meters", LengthUnit.m),
        ("ft", LengthUnit.ft),
        ("Meters", LengthUnit.m),
        ("METERS", LengthUnit.m),
        ("M", LengthUnit.m),
        ("FT", LengthUnit.ft),
        ("MM", LengthUnit.mm),
        ("CM", LengthUnit.cm),
    ]
)
def test_mapping(input_alias: str, expected_output: LengthUnit):
    assert LengthUnit.map_from_alias(input_alias) == expected_output


@pytest.mark.parametrize(
    "source_value,source_unit,expected_value,target_unit",
    [
        (1, LengthUnit.mm, 0.1, LengthUnit.cm),
        (1, LengthUnit.m, 100, LengthUnit.cm),
        (1, LengthUnit.m, 1000, LengthUnit.mm),
        (1, LengthUnit.cm, 10, LengthUnit.mm),
        (34, LengthUnit.m, 34000, LengthUnit.mm),
        (12, LengthUnit.mm, 1.2, LengthUnit.cm),
        (1, LengthUnit.ft, 30.48, LengthUnit.cm),
        (1, LengthUnit.ft, 0.3048, LengthUnit.m),
        (150, LengthUnit.mm, 0.4921, LengthUnit.ft),
    ]
)
def test_unit_conversion(source_value: float, source_unit: LengthUnit, expected_value: float, target_unit: LengthUnit):
    converted_val = unit_manager.convert_units(source_value, from_unit=source_unit, to_unit=target_unit)
    assert converted_val == pytest.approx(expected_value, 0.001)
