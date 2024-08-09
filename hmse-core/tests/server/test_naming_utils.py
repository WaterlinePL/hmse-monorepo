import pytest

from server import naming_utils


@pytest.mark.parametrize(
    "input_project_id,expected_project_id",
    [
        ("my project", "my-project"),
        ("another_project", "another-project"),
        ("multi  space   name", "multi--space---name"),
    ]
)
def test_validate_project_id(input_project_id: str, expected_project_id: str):
    assert naming_utils.validate_project_id(input_project_id) == expected_project_id
