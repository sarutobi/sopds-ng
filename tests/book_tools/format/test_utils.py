from book_tools.format.util import normalize_string
import pytest


@pytest.mark.parametrize(
    "text,expected",
    [
        (None, None),
        ("test data with spaces", "test data with spaces"),
        ("test  data    with     spaces", "test data with spaces"),
        ("test data with lf\r", "test data with lf"),
        ("test data with cr\n", "test data with cr"),
        ("test data with lf and cr\r\n", "test data with lf and cr"),
        (
            "test  data   with spaces,     lf  and   cr\r\n",
            "test data with spaces, lf and cr",
        ),
        ("test data with cr\n in middle", "test data with cr in middle"),
    ],
)
def test_normalize_string(text, expected) -> None:
    actual = normalize_string(text)
    assert actual == expected
