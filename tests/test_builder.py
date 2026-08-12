"""Tests for builder. All pure functions - no fixtures, no git."""

from kommitted.builder import build, format_file_line, scope, subject
from kommitted.constants import MAX_SUBJECT_LEN
from kommitted.models import Classification, NumStat

from .conftest import stat

# ---------------------------------------------------------------------------
# scope
# ---------------------------------------------------------------------------


def test_scope_empty_list():
    assert scope([]) == ""


def test_scope_single_file_in_a_directory():
    assert scope([stat("model/classifier.py")]) == "model"


def test_scope_root_file_has_no_scope():
    # 'README.md' has no directory - there's no component to name.
    assert scope([stat("README.md")]) == ""


def test_scope_shared_directory():
    assert scope([stat("model/a.py"), stat("model/b.py")]) == "model"


def test_scope_uses_last_segment_only():
    # Scopes are component names, not paths: 'internal/git' -> 'git'.
    assert scope([stat("internal/git/git.go"), stat("internal/git/errors.go")]) == "git"


def test_scope_diverging_directories():
    assert scope([stat("model/a.py"), stat(".github/ci.yml")]) == ""


def test_scope_partial_overlap_takes_common_parent():
    assert scope([stat("src/api/a.py"), stat("src/db/b.py")]) == "src"


def test_scope_survives_a_trivial_root_file():
    # 300 lines in model/, 2 in .gitignore. This is a commit about model.
    stats = [stat("model/a.py", 200, 100), stat(".gitignore", 2, 0)]
    assert scope(stats) == "model"


def test_scope_lost_when_root_file_dominates():
    stats = [stat("model/a.py", 1, 0), stat("README.md", 200, 0)]
    assert scope(stats) == ""


def test_scope_all_files_at_root():
    assert scope([stat("README.md"), stat("setup.py")]) == ""


def test_scope_zero_churn_mixed_files_is_safe():
    # Every file empty -> division by zero if unguarded.
    stats = [stat("model/a.py", 0, 0), stat("README.md", 0, 0)]
    assert scope(stats) == ""


# ---------------------------------------------------------------------------
# subject
# ---------------------------------------------------------------------------


def test_subject_single_file_uses_filename_stem():
    c = Classification("feat", 0.6, [])
    assert subject(c, [stat("model/classifier.py")]) == "add classifier"


def test_subject_verb_matches_type():
    stats = [stat("model/a.py")]
    assert subject(Classification("fix", 0.3, []), stats).startswith("fix ")
    assert subject(Classification("docs", 0.9, []), stats).startswith("update ")
    assert subject(Classification("test", 0.9, []), stats).startswith("add tests for ")
    assert subject(Classification("refactor", 0.45, []), stats).startswith("refactor ")


def test_subject_unknown_type_does_not_crash():
    # A typo'd or future type must degrade, not raise.
    assert subject(Classification("banana", 0.1, []), [stat("model/a.py")]) == "update a"


def test_subject_multiple_files_uses_scope():
    c = Classification("feat", 0.6, [])
    assert subject(c, [stat("model/a.py"), stat("model/b.py")]) == "add model"


def test_subject_multiple_files_without_scope_counts_them():
    c = Classification("feat", 0.6, [])
    assert subject(c, [stat("README.md"), stat("setup.py")]) == "add 2 files"


# ---------------------------------------------------------------------------
# format_file_line
# ---------------------------------------------------------------------------


def test_format_file_line():
    assert format_file_line(stat("model/a.py", 42, 3)) == "- model/a.py (+42 -3)"


def test_format_file_line_binary():
    # Binary files carry None, not 0 - saying "+0 -0" would be a lie.
    binary = NumStat(added_lines=None, deleted_lines=None, path="logo.png")
    assert format_file_line(binary) == "- logo.png (binary)"


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


def test_build_full_message():
    c = Classification("feat", 0.6, [])
    stats = [stat("model/classifier.py", 120, 0), stat("model/gitrunner.py", 3, 1)]

    assert build(c, stats) == (
        "feat(model): add model\n"
        "\n"
        "- model/classifier.py (+120 -0)\n"
        "- model/gitrunner.py (+3 -1)"
    )


def test_build_omits_empty_scope_parens():
    # 'feat(): ...' would be malformed Conventional Commits.
    result = build(Classification("feat", 0.6, []), [stat("README.md")])
    assert result.startswith("feat: ")
    assert "()" not in result


def test_build_has_blank_line_between_subject_and_body():
    # Git requires it: line 1 is the summary, line 2 must be empty.
    lines = build(Classification("feat", 0.6, []), [stat("model/a.py")]).split("\n")
    assert lines[1] == ""


def test_build_subject_line_is_first_line_only():
    c = Classification("feat", 0.6, [])
    msg = build(c, [stat("model/a.py"), stat("model/b.py")])
    assert msg.split("\n")[0] == "feat(model): add model"


def test_build_truncates_long_subject():
    # A deep path alone isn't enough - only the last segment becomes scope.
    long_path = "pkg/an_extremely_long_module_name_that_overflows_the_line.py"
    header = build(Classification("feat", 0.6, []), [stat(long_path)]).split("\n")[0]
    assert len(header) <= MAX_SUBJECT_LEN
    assert header.endswith("...")


def test_build_does_not_truncate_a_normal_subject():
    header = build(Classification("feat", 0.6, []), [stat("model/a.py")]).split("\n")[0]
    assert header == "feat(model): add a"
    assert "..." not in header


def test_build_with_no_stats_returns_header_only():
    c = Classification("chore", 0.0, ["nothing staged"])
    assert build(c, []) == "chore: update 0 files"


def test_build_output_is_a_valid_git_message_shape():
    msg = build(Classification("fix", 0.3, []), [stat("model/a.py", 2, 5)])
    first = msg.split("\n")[0]
    assert len(first) <= MAX_SUBJECT_LEN
    assert not first.endswith(".")
