import pytest

from cdp_scrapers.scraper_utils import str_simplified


@pytest.mark.parametrize(
    "input_string, expected_output",
    [
        (
            "   test   ",
            "test",
        ),
        ("    test", "test"),
        ("test     ", "test"),
        ("test\r\n\ftest", "test\ntest"),
        ("test \t\vtest", "test test"),
        ("M. Lorena Gonz\u00e1lez", "M. Lorena González"),
        (5, 5),
        ("Hello", "There")
    ],
)
def test_str_simplifed(input_string: str, expected_output: str):
    # Validate that both methods work the same
    assert str_simplified(input_string) == expected_output
