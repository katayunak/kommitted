from difflib import SequenceMatcher
from enum import Enum

from .token import Token, TokenType, tokenize


class EditType(str, Enum):
    ADDED = "added"  # there was no before side
    DELETED = "deleted"  # there is no after side
    UNCHANGED = "unchanged"  # only whitespace moved

    RENAMED = "renamed"  # a name changed -> refactor evidence
    OPERATOR = "operator"  # an operator changed -> strong fix evidence
    LITERAL = "literal"  # a number or string changed -> fix evidence

    # We compared the two lines and could not say what happened. NOT the
    # same as "nothing changed" and NOT the same as "no behavior changed" 
    # it means the line was rewritten too heavily to read token by token.
    REWRITTEN = "rewritten"


# Which kind of token, when it changes, means which kind of edit.
_TOKEN_TYPE_TO_EDIT_TYPE = {
    TokenType.OP: EditType.OPERATOR,
    TokenType.NUMBER: EditType.LITERAL,
    TokenType.STRING: EditType.LITERAL,
    TokenType.NAME: EditType.RENAMED,
}

# A changed run bigger than this is a rewrite, not a tweak.
_MAX_TWEAK_SIZE = 2


def classify_edit(before: str, after: str) -> frozenset[EditType]:
    """Everything that changed between two versions of one line.

    Returns a SET, not one answer, because one line can change in more than
    one way at the same time:

        - if retries < maxTries {
        + if attempts <= maxTries {

    A name changed AND an operator changed. Picking only the "strongest" of
    the two throws away real evidence - the scorer wants to count both.
    """
    if not before.strip():
        return frozenset({EditType.ADDED}) if after.strip() else frozenset()

    if not after.strip():
        return frozenset({EditType.DELETED})

    old_tokens = tokenize(before)
    new_tokens = tokenize(after)

    if old_tokens == new_tokens:
        # Same tokens means only whitespace moved. Formatting is not a change.
        return frozenset({EditType.UNCHANGED})

    old_shape = [token.type for token in old_tokens]
    new_shape = [token.type for token in new_tokens]

    if old_shape == new_shape:
        return _edits_from_swapped_tokens(old_tokens, new_tokens)

    return _edits_from_reshaped_line(old_tokens, new_tokens)


def _edits_from_swapped_tokens(
    old_tokens: list[Token], new_tokens: list[Token]
) -> frozenset[EditType]:
    """Both lines have the same shape, so tokens were swapped one for one."""
    changed_types = {
        old.type
        for old, new in zip(old_tokens, new_tokens)
        if old.text != new.text
    }
    return _to_edit_types(changed_types)


def _edits_from_reshaped_line(
    old_tokens: list[Token], new_tokens: list[Token]
) -> frozenset[EditType]:
    """The lines have different shapes, so something was added or removed.

    If exactly one small run of tokens moved we can still name it - swapping
    `10` for `n` in `if x < 10` changes the shape but is clearly a literal
    edit. Anything larger we refuse to guess about.
    """
    matcher = SequenceMatcher(
        a=[token.text for token in old_tokens],
        b=[token.text for token in new_tokens],
    )
    edits = [
        opcode
        for opcode in matcher.get_opcodes()
        if opcode[0] in ("replace", "insert", "delete")
    ]

    if len(edits) != 1:
        return frozenset({EditType.REWRITTEN})

    _, old_start, old_end, new_start, new_end = edits[0]

    if (old_end - old_start) + (new_end - new_start) > _MAX_TWEAK_SIZE:
        return frozenset({EditType.REWRITTEN})

    touched_types = {token.type for token in old_tokens[old_start:old_end]}
    touched_types |= {token.type for token in new_tokens[new_start:new_end]}
    return _to_edit_types(touched_types)


def _to_edit_types(token_types: set[TokenType]) -> frozenset[EditType]:
    """Turn the token types that moved into the edits they represent."""
    edits = {
        _TOKEN_TYPE_TO_EDIT_TYPE[token_type]
        for token_type in token_types
        if token_type in _TOKEN_TYPE_TO_EDIT_TYPE
    }
    # Only punctuation moved, which we have no reading for.
    return frozenset(edits) if edits else frozenset({EditType.REWRITTEN})
