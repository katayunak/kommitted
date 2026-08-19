"""Renames, as git actually reports them.

Every RAW string here was captured from real `git diff --staged --numstat`
output, not written from memory. Git picks between four notations depending
on what the two paths share, and all four appear in normal use.
"""

import pytest

from kommitted.brains.rules.commit_type import CommitType
from kommitted.brains.rules.context import Context
from kommitted.brains.rules.scorers import score_all, score_by_renames
from kommitted.git.diffparser import parse_numstat, split_rename
from kommitted.git.models import NumStat

# ---------------------------------------------------------------------------
# The four notations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "column, new_path, old_path",
    [
        # shared prefix, empty old middle - a directory level was inserted
        ("src/kommitted/{ => git}/builder.py",
         "src/kommitted/git/builder.py", "src/kommitted/builder.py"),
        # shared prefix and suffix, both middles present
        ("deep/{nested => other}/q.go", "deep/other/q.go", "deep/nested/q.go"),
        # brace at the very start - nothing shared at the front
        ("{old => new/sub}/z.go", "new/sub/z.go", "old/z.go"),
        # nothing shared at all
        ("a/b/x.go => pkg/renamed.go", "pkg/renamed.go", "a/b/x.go"),
        # top level, no directory on either side
        ("plain.go => toplevel.go", "toplevel.go", "plain.go"),
        # spaces are legal in paths and must survive
        ("sp ace.go => c/b/x.go", "c/b/x.go", "sp ace.go"),
    ],
)
def test_every_rename_notation_is_unpacked(column, new_path, old_path):
    assert split_rename(column) == (new_path, old_path)


def test_a_plain_path_is_left_alone():
    assert split_rename("src/normal/file.py") == ("src/normal/file.py", None)


def test_an_arrow_inside_a_filename_is_not_a_rename():
    # Unlikely, but " => " is legal in a filename and the plain form would
    # happily split it. Documented as a known limit rather than pretended.
    new, old = split_rename("weird => name.py")
    assert (new, old) == ("name.py", "weird")


# ---------------------------------------------------------------------------
# Reading it back out
# ---------------------------------------------------------------------------


def test_numstat_keeps_counts_and_both_paths():
    stat = parse_numstat("0\t0\tsrc/{ => git}/builder.py\n")[0]
    assert stat.path == "src/git/builder.py"
    assert stat.old_path == "src/builder.py"
    assert stat.is_rename


def test_binary_files_still_parse():
    stat = parse_numstat("-\t-\timage.png\n")[0]
    assert stat.added_lines is None
    assert stat.total_lines_changed == 0
    assert not stat.is_rename


def test_moving_directory_differs_from_renaming_in_place():
    moved = NumStat(0, 0, "b/x.go", old_path="a/x.go")
    renamed = NumStat(0, 0, "a/y.go", old_path="a/x.go")

    assert moved.moved_directory and not moved.renamed_in_place
    assert renamed.renamed_in_place and not renamed.moved_directory


def test_a_top_level_rename_is_not_a_directory_move():
    stat = NumStat(0, 0, "toplevel.go", old_path="plain.go")
    assert stat.renamed_in_place


# ---------------------------------------------------------------------------
# What it buys the classifier
# ---------------------------------------------------------------------------


def test_moved_files_score_refactor():
    context = Context(
        files=[
            NumStat(0, 0, "src/git/builder.py", old_path="src/builder.py"),
            NumStat(0, 0, "src/git/models.py", old_path="src/models.py"),
        ]
    )
    score_by_renames(context)
    assert context.scores[CommitType.REFACTOR] > 0


def test_a_package_reorganisation_is_a_refactor():
    # The case that started this: files moved into a new subpackage, with
    # some edits alongside. Before renames were parsed, this came out `fix`.
    raw = (
        "0\t0\tsrc/kommitted/{ => git}/builder.py\n"
        "0\t0\tsrc/kommitted/{ => git}/models.py\n"
        "0\t0\tsrc/kommitted/{ => git}/gitrunner.py\n"
        "3\t3\tsrc/kommitted/cli.py\n"
    )
    result = score_all(Context.collect(parse_numstat(raw))).classify()
    assert result.type == CommitType.REFACTOR.value


def test_no_renames_means_no_rename_score():
    context = Context(files=[NumStat(10, 2, "src/a.py")])
    score_by_renames(context)
    assert context.scores == {}
