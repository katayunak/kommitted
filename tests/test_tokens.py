"""Tests for reading one changed line.

Every case here is `+1 -1`. Line counts cannot separate any of them - that
is the whole reason this module exists.
"""

import pytest

from kommitted.tokens.edit import EditType, classify_edit
from kommitted.tokens.token import TokenType, tokenize

# ---------------------------------------------------------------------------
# Tokenizing
# ---------------------------------------------------------------------------


def test_multichar_operators_are_one_token():
    operators = [t.text for t in tokenize("a <= b && c != d") if t.type is TokenType.OP]
    assert operators == ["<=", "&&", "!="]


def test_whitespace_is_discarded():
    assert tokenize("if x{") == tokenize("if   x  {")


def test_strings_are_not_read_as_code():
    types = [t.type for t in tokenize('x = "a // b && c"')]
    assert types == [TokenType.NAME, TokenType.OP, TokenType.STRING]


@pytest.mark.parametrize("word", ["and", "or", "not", "is", "in"])
def test_word_operators_are_operators(word):
    # Python writes `and` where Go writes `&&`. If these stayed NAME tokens,
    # a logic fix would be read as a rename.
    assert tokenize(f"a {word} b")[1].type is TokenType.OP


# ---------------------------------------------------------------------------
# Fix evidence: operators and literals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "before, after",
    [
        ("if retries < max {", "if retries <= max {"),  # off by one
        ("if a == b {", "if a != b {"),  # test flipped
        ("if a && b {", "if a || b {"),  # wrong connective
        ("    if a and b:", "    if a or b:"),  # ...written as words
        ("    if x is None:", "    if x is not None:"),
    ],
)
def test_operator_changes_are_found(before, after):
    assert EditType.OPERATOR in classify_edit(before, after)


@pytest.mark.parametrize(
    "before, after",
    [
        ("timeout := 30", "timeout := 60"),
        ('mode := "r"', 'mode := "rw"'),
        ("return 0", "return 1"),
    ],
)
def test_literal_changes_are_found(before, after):
    assert EditType.LITERAL in classify_edit(before, after)


# ---------------------------------------------------------------------------
# Refactor evidence: names only
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "before, after",
    [
        ("func parseNumstat(raw string) {", "func parseNumStat(raw string) {"),
        ("    def parse_numstat(self, raw):", "    def parse_num_stat(self, raw):"),
        ("result := w.fetch()", "outcome := w.fetch()"),
    ],
)
def test_name_only_changes_are_renames(before, after):
    assert classify_edit(before, after) == {EditType.RENAMED}


def test_formatting_only_changes_nothing():
    # Whitespace is not behaviour. gofmt churn must not read as an edit.
    assert classify_edit("\tif x{", "\tif  x {") == {EditType.UNCHANGED}


# ---------------------------------------------------------------------------
# More than one thing can change at once
# ---------------------------------------------------------------------------


def test_a_line_can_have_two_edits():
    # A name AND an operator moved. Returning only the "strongest" one would
    # throw away the other; the scorer wants to count both.
    edits = classify_edit("if retries < maxTries {", "if attempts <= maxTries {")
    assert edits == {EditType.RENAMED, EditType.OPERATOR}


def test_a_literal_and_a_name_can_both_move():
    edits = classify_edit("wait := 30", "delay := 60")
    assert edits == {EditType.RENAMED, EditType.LITERAL}


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


def test_a_missing_side_is_an_add_or_a_delete():
    assert classify_edit("", "x := 1") == {EditType.ADDED}
    assert classify_edit("x := 1", "") == {EditType.DELETED}


def test_two_empty_sides_say_nothing():
    assert classify_edit("", "") == frozenset()


def test_a_heavy_rewrite_is_rewritten():
    # REWRITTEN means "we could not tell", not "nothing changed" and not
    # "no behaviour changed".
    edits = classify_edit("return nil", 'return fmt.Errorf("fetch %s: %w", n, err)')
    assert edits == {EditType.REWRITTEN}


def test_a_small_change_of_shape_still_gets_read():
    # `x < 10` -> `x < n` changes the token shape, but only one small run
    # moved, so we can still name it instead of shrugging.
    assert EditType.REWRITTEN not in classify_edit("if x < 10 {", "if x < n {")
