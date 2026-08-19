"""Tests for Change - the paired before/after unit the parser now produces."""

from kommitted.git.diffcontent import parse_diff
from kommitted.tokens.edit import EditType

OFF_BY_ONE = "+++ b/a.go\n-\tif retries < max {\n+\tif retries <= max {\n"
RENAME = (
    "+++ b/a.go\n"
    "-func parseNumstat(raw string) error {\n"
    "+func parseNumStat(raw string) error {\n"
)
ADDED_GUARD = (
    "+++ b/a.go\n \tx := f()\n+\tif x == nil {\n+\t\treturn ErrNil\n+\t}\n"
)
PURE_MOVE = (
    "+++ b/a.go\n"
    "-func Handle(r *Request) error {\n-\treturn nil\n-}\n"
    "+func Handle(r *Request) error {\n+\treturn nil\n+}\n"
)


# ---------------------------------------------------------------------------
# Pairing
# ---------------------------------------------------------------------------


def test_a_modified_line_becomes_one_change_with_both_sides():
    changes = parse_diff(OFF_BY_ONE).changes
    assert len(changes) == 1
    assert changes[0].before.text.strip() == "if retries < max {"
    assert changes[0].after.text.strip() == "if retries <= max {"


def test_a_pure_addition_has_an_empty_before_side():
    changes = parse_diff("+++ b/a.go\n \tctx := f()\n+\tdefer cancel()\n").changes
    added = [ch for ch in changes if not ch.before]
    assert len(added) == 1
    assert added[0].after.text.strip() == "defer cancel()"
    assert EditType.ADDED in added[0].edits


def test_a_pure_deletion_has_an_empty_after_side():
    changes = parse_diff("+++ b/a.go\n \tctx := f()\n-\tlog.Println(ctx)\n").changes
    removed = [ch for ch in changes if not ch.after]
    assert len(removed) == 1
    assert EditType.DELETED in removed[0].edits


def test_uneven_blocks_pair_positionally_then_spill():
    # Two lines out, three in: two paired edits and one pure addition.
    diff = "+++ b/a.go\n-\ta := 1\n-\tb := 2\n+\ta := 10\n+\tb := 20\n+\tc := 30\n"
    changes = parse_diff(diff).changes
    assert len(changes) == 3
    assert [EditType.LITERAL in ch.edits for ch in changes[:2]] == [True, True]
    assert EditType.ADDED in changes[2].edits


def test_changes_carry_their_file_and_language():
    ch = parse_diff(OFF_BY_ONE).changes[0]
    assert ch.path == "a.go"
    assert ch.language == "go"


def test_separate_edit_blocks_do_not_pair_across_context():
    # A context line between them means these are unrelated edits, not a
    # substitution. Pairing across it would invent a rename.
    diff = "+++ b/a.go\n-\tx := 1\n \tuntouched()\n+\ty := 2\n"
    edits = [ch.edits for ch in parse_diff(diff).changes]
    assert edits == [{EditType.DELETED}, {EditType.ADDED}]


# ---------------------------------------------------------------------------
# What the pairing buys: fix vs refactor on identical line counts
# ---------------------------------------------------------------------------


def test_off_by_one_reads_as_an_operator_edit():
    assert parse_diff(OFF_BY_ONE).with_edit(EditType.OPERATOR)


def test_rename_reads_as_a_rename():
    content = parse_diff(RENAME)
    assert content.with_edit(EditType.RENAMED)
    assert not content.with_edit(EditType.OPERATOR)


def test_both_are_invisible_to_behaviour_counts_alone():
    # The point of the whole module: behaviour deltas cannot separate these
    # two, and each is +1 -1. Only the edit kind can.
    assert parse_diff(OFF_BY_ONE).behavior_preserved
    assert parse_diff(RENAME).behavior_preserved


# ---------------------------------------------------------------------------
# Behaviour deltas
# ---------------------------------------------------------------------------


def test_an_added_guard_moves_conditionals():
    content = parse_diff(ADDED_GUARD)
    assert content.behavior_delta("conditionals") == 1
    assert not content.behavior_preserved


def test_a_pure_move_preserves_every_behaviour():
    content = parse_diff(PURE_MOVE)
    assert content.behavior_preserved
    assert [s.name for s in content.moved_definitions] == ["Handle"]
    assert content.new_definitions == []


def test_behaviors_keep_the_text_they_matched():
    # "a conditional was added" is weak. "`if x == nil` was added" says what
    # is being checked, which is what a commit message wants.
    guard = parse_diff(ADDED_GUARD).changes[0].after.behaviors
    assert [(b.kind, b.text) for b in guard] == [("conditionals", "if x == nil {")]


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


def test_a_reworded_comment_is_a_comment_on_both_sides():
    content = parse_diff("+++ b/a.go\n-// stale note\n+// fresh note\n")
    assert content.added_comments == 1
    assert content.removed_comments == 1
    assert content.changes[0].touches_comment
    assert content.added_definitions == []
