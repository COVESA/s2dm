import pytest

from s2dm.deps.naming import sanitize_prefix


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("foo_bar", "foo_bar", id="passthrough_already_valid"),
        pytest.param("", "", id="empty_input"),
        pytest.param("_foo", "_foo", id="leading_underscore_preserved"),
        pytest.param("@@@", "_", id="all_invalid_collapses_to_single_underscore"),
        pytest.param("a-b.c", "a_b_c", id="non_consecutive_invalid_chars_stay_separate"),
        pytest.param("1foo", "_1foo", id="leading_digit_gets_prefixed"),
        pytest.param("@1foo", "_1foo", id="leading_digit_check_runs_after_substitution"),
        pytest.param("vé", "v_", id="unicode_letter_treated_as_invalid"),
    ],
)
def test_sanitize_prefix(raw: str, expected: str) -> None:
    assert sanitize_prefix(raw) == expected
