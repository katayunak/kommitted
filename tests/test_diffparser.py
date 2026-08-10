"""Tests for the numstat parser."""

import pytest

from committed.diffparser import parse_count, parse_numstat
from committed.models import NumStat

# ---------------------------------------------------------------------------
# parse_count - pure, so these are the cheapest tests in the project
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("0", 0),
        ("1", 1),
        ("34", 34),
        ("999999", 999999),
        ("-", None),  # git's marker for a binary file
    ],
)
def test_parse_count_valid(raw, expected):
    assert parse_count(raw) == expected


def test_parse_count_rejects_garbage():
    # Deliberately not swallowed. Unexpected input from git means our
    # assumptions are wrong, and failing loudly beats inventing a number.
    with pytest.raises(ValueError):
        parse_count("abc")


def test_parse_count_zero_is_not_none():
    # Guards a real bug: `if not count` treats 0 and None the same.
    # 0 lines changed and "unknown" are different facts.
    assert parse_count("0") == 0
    assert parse_count("0") is not None


# ---------------------------------------------------------------------------
# parse_numstat
# ---------------------------------------------------------------------------


def test_single_line():
    assert parse_numstat("34\t0\t.gitignore\n") == [
        NumStat(added_lines=34, deleted_lines=0, path=".gitignore")
    ]


def test_multiple_lines():
    raw = "34\t0\t.gitignore\n3\t0\tgo.mod\n26\t0\tmain.go\n"
    result = parse_numstat(raw)
    assert [st.path for st in result] == [".gitignore", "go.mod", "main.go"]
    assert result[2].added_lines == 26


def test_empty_input_returns_empty_list():
    assert parse_numstat("") == []


def test_trailing_newline_does_not_create_a_phantom_entry():
    # "a\n".split("\n") == ["a", ""] - that "" must not become a NumStat.
    assert len(parse_numstat("1\t2\ta.txt\n")) == 1


def test_missing_trailing_newline_still_parses():
    assert len(parse_numstat("1\t2\ta.txt")) == 1


def test_binary_file_yields_none_not_zero():
    assert parse_numstat("-\t-\tlogo.png\n") == [
        NumStat(added_lines=None, deleted_lines=None, path="logo.png")
    ]


def test_binary_and_text_files_mixed():
    result = parse_numstat("34\t0\t.gitignore\n-\t-\tlogo.png\n")
    assert result[0].added_lines == 34
    assert result[1].added_lines is None


def test_path_with_spaces_survives():
    # Columns are tab-separated, so spaces inside a path are safe.
    result = parse_numstat("5\t2\tmy folder/some file.py\n")
    assert result[0].path == "my folder/some file.py"


def test_deletion_only_file():
    result = parse_numstat("0\t17\tremoved.go\n")
    assert result[0].added_lines == 0
    assert result[0].deleted_lines == 17


def test_blank_lines_are_skipped():
    assert len(parse_numstat("1\t1\ta.txt\n\n\n2\t2\tb.txt\n")) == 2


# ---------------------------------------------------------------------------
# NumStat.churn
# ---------------------------------------------------------------------------


def test_churn_sums_both_columns():
    assert NumStat(10, 5, "a.py").churn == 15


def test_churn_of_binary_is_zero():
    assert NumStat(None, None, "logo.png").churn == 0
