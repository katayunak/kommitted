"""Tests for the numstat parser.

Run from the project root:   python3 -m pytest model/ -v
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from diffparser import NumStat, num_stat_parser, parse_count


# ---------------------------------------------------------------------------
# parse_count - a pure function, so these are the cheapest tests in the project
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
    # We deliberately do NOT swallow this. Unexpected input from git means our
    # assumptions are wrong, and failing loudly beats inventing a number.
    with pytest.raises(ValueError):
        parse_count("abc")


def test_parse_count_zero_is_not_none():
    # Guards a real bug: `if not count` treats 0 and None the same.
    # 0 lines changed and "unknown" are different facts.
    assert parse_count("0") == 0
    assert parse_count("0") is not None


# ---------------------------------------------------------------------------
# num_stat_parser - the parsing logic
# ---------------------------------------------------------------------------

def test_single_line():
    result = num_stat_parser("34\t0\t.gitignore\n")
    assert result == [NumStat(added_lines=34, deleted_lines=0, path=".gitignore")]


def test_multiple_lines():
    raw = "34\t0\t.gitignore\n3\t0\tgo.mod\n26\t0\tmain.go\n"
    result = num_stat_parser(raw)
    assert len(result) == 3
    assert [st.path for st in result] == [".gitignore", "go.mod", "main.go"]
    assert result[2].added_lines == 26


def test_empty_input_returns_empty_list():
    # Nothing staged. Must not crash, must not return None.
    assert num_stat_parser("") == []


def test_trailing_newline_does_not_create_a_phantom_entry():
    # The bug we hunted: "a\n".split("\n") == ["a", ""] - that "" must not
    # become a NumStat.
    assert len(num_stat_parser("1\t2\ta.txt\n")) == 1


def test_missing_trailing_newline_still_parses():
    # Defensive: don't depend on git always terminating the last line.
    assert len(num_stat_parser("1\t2\ta.txt")) == 1


def test_binary_file_yields_none_not_zero():
    result = num_stat_parser("-\t-\tlogo.png\n")
    assert result == [NumStat(added_lines=None, deleted_lines=None, path="logo.png")]


def test_binary_and_text_files_mixed():
    raw = "34\t0\t.gitignore\n-\t-\tlogo.png\n"
    result = num_stat_parser(raw)
    assert result[0].added_lines == 34
    assert result[1].added_lines is None


def test_path_with_spaces_survives():
    # Columns are tab-separated, so spaces inside a path are safe.
    result = num_stat_parser("5\t2\tmy folder/some file.py\n")
    assert result[0].path == "my folder/some file.py"


def test_deletion_only_file():
    result = num_stat_parser("0\t17\tremoved.go\n")
    assert result[0].added_lines == 0
    assert result[0].deleted_lines == 17


def test_blank_lines_are_skipped():
    result = num_stat_parser("1\t1\ta.txt\n\n\n2\t2\tb.txt\n")
    assert len(result) == 2


# ---------------------------------------------------------------------------
# End-to-end: run the script as a real subprocess over a real pipe.
# This is the contract the Go side depends on - stdout must be pure JSON.
# ---------------------------------------------------------------------------

SCRIPT = Path(__file__).parent / "diffparser.py"


def run_script(stdin_text: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=stdin_text,
        capture_output=True,
        text=True,
    )


def test_stdout_is_valid_json():
    proc = run_script("34\t0\t.gitignore\n3\t0\tgo.mod\n")
    assert proc.returncode == 0
    parsed = json.loads(proc.stdout)  # raises if stdout is polluted
    assert parsed == [
        {"added_lines": 34, "deleted_lines": 0, "path": ".gitignore"},
        {"added_lines": 3, "deleted_lines": 0, "path": "go.mod"},
    ]


def test_binary_file_serializes_as_json_null():
    # Go must unmarshal this into *int, not int.
    proc = run_script("-\t-\tlogo.png\n")
    assert json.loads(proc.stdout)[0]["added_lines"] is None
    assert '"added_lines": null' in proc.stdout


def test_empty_stdin_produces_empty_json_array():
    proc = run_script("")
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == []


def test_nothing_but_json_on_stdout():
    # If any debug print sneaks back onto stdout, this fails and the Go side
    # would have broken in production instead.
    proc = run_script("1\t1\ta.txt\n")
    assert proc.stdout.strip().startswith("[")
    assert proc.stdout.strip().endswith("]")
    assert proc.stderr == ""
