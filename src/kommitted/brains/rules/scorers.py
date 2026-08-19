from ...languages.base import BEHAVIOR_FIELDS
from ...tokens.edit import EditType
from . import constants as c
from .commit_type import CommitType, Score
from .context import Context

# --- Path rules: the reliable ones -----------------------------------------


def is_test(path: str) -> bool:
    lowered = path.lower()
    return any(marker in lowered for marker in c.TEST_MARKERS)


def is_doc(path: str) -> bool:
    lowered = path.lower()
    return lowered.endswith(c.DOC_EXTENSIONS) or any(d in lowered for d in c.DOC_DIRS)


def is_config(path: str) -> bool:
    lowered = path.lower()
    name = lowered.rsplit("/", 1)[-1]
    return name in c.CONFIG_NAMES or any(d in lowered for d in c.CONFIG_DIRS)


def score_by_path(context: Context) -> None:
    paths = context.paths
    if not paths:
        return

    if all(is_test(path) for path in paths):
        context.add(
            CommitType.TEST,
            Score.STRONG,
            c.REASON_ALL_TESTS.format(count=len(paths)),
        )

    if all(is_doc(path) for path in paths):
        context.add(CommitType.DOCS, Score.STRONG, c.REASON_ONLY_DOCS)

    if all(is_config(path) for path in paths):
        context.add(CommitType.CHORE, Score.MEDIUM, c.REASON_ONLY_CONFIG)


# --- Branch name ------------------------------------------------------------


def score_by_branch(context: Context) -> None:
    branch = context.branch.lower()
    if not branch:
        return

    prefix = branch.split("/", 1)[0].split("-", 1)[0]
    commit_type = c.BRANCH_PREFIXES.get(prefix)
    if commit_type is None:
        return

    context.add(
        CommitType(commit_type),
        Score.MEDIUM,
        c.REASON_BRANCH.format(branch=context.branch, prefix=prefix),
    )


# --- What the diff body says ------------------------------------------------


def score_by_definitions(context: Context) -> None:
    """New functions and types mean new code. Moved ones mean moved code."""
    diff = context.diff
    if diff is None:
        return

    new = diff.new_definitions
    moved = diff.moved_definitions

    if new:
        # A new function inside a test file is a new TEST, not a new
        # feature. Without this the two rules tie at STRONG and the answer
        # depends on tie-breaking, which is no way to decide anything.
        paths = context.paths
        target = (
            CommitType.TEST
            if paths and all(is_test(path) for path in paths)
            else CommitType.FEAT
        )
        context.add(
            target,
            Score.STRONG,
            c.REASON_NEW_DEFINITIONS.format(
                kind=new[0].kind, names=", ".join(s.name for s in new[:3])
            ),
        )

    if moved and not new:
        context.add(
            CommitType.REFACTOR,
            Score.MEDIUM,
            c.REASON_MOVED_DEFINITIONS.format(
                names=", ".join(s.name for s in moved[:3])
            ),
        )


def score_by_renames(context: Context) -> None:
    """Files that moved. The clearest structural refactor evidence we get.

    Git already ran rename detection and told us in the numstat - this rule
    just stops throwing the answer away.

    Moving a file between directories is stronger than renaming it in place:
    the first is reorganising a package, the second could be fixing a typo
    in a filename. So they score differently.
    """
    moved = [f for f in context.files if f.moved_directory]
    renamed = [f for f in context.files if f.renamed_in_place]

    if moved:
        context.add(
            CommitType.REFACTOR,
            Score.STRONG,
            c.REASON_FILES_MOVED.format(
                count=len(moved),
                examples=", ".join(f"{f.old_path} -> {f.path}" for f in moved[:2]),
            ),
        )

    if renamed:
        context.add(
            CommitType.REFACTOR,
            Score.MEDIUM,
            c.REASON_FILES_RENAMED.format(count=len(renamed)),
        )


def score_by_edits(context: Context) -> None:
    diff = context.diff
    if diff is None:
        return

    operators = diff.with_edit(EditType.OPERATOR)
    literals = diff.with_edit(EditType.LITERAL)
    renames = diff.with_edit(EditType.RENAMED)

    if operators:
        context.add(
            CommitType.FIX,
            Score.STRONG,
            c.REASON_OPERATOR_EDIT.format(count=len(operators)),
        )

    if literals:
        context.add(
            CommitType.FIX,
            Score.MEDIUM,
            c.REASON_LITERAL_EDIT.format(count=len(literals)),
        )

    if renames and not operators and not literals:
        context.add(
            CommitType.REFACTOR,
            Score.MEDIUM,
            c.REASON_RENAME_EDIT.format(count=len(renames)),
        )


def score_by_behaviors(context: Context) -> None:
    diff = context.diff
    if diff is None or not diff.changes:
        return

    grew = [name for name in BEHAVIOR_FIELDS if diff.behavior_delta(name) > 0]

    if grew:
        # A guard appearing is fix evidence ONLY in a small change that
        # added no new definitions. Any commit that writes 4000 lines has
        # more conditionals than before - that is new code existing, not a
        # bug being guarded against.
        #
        # And it scores ONCE. Awarding per category counted "this commit
        # contains code" four times over, which is how a 74-file
        # restructure came out as `fix`.
        if diff.new_definitions or context.total_lines > c.SMALL_CHANGE_LINES:
            return

        context.add(
            CommitType.FIX,
            Score.WEAK,
            c.REASON_BEHAVIOR_ADDED.format(
                kinds=", ".join(
                    f"{name} {diff.behavior_delta(name):+d}" for name in grew
                )
            ),
        )
        return

    # "Behaviour was preserved" only means something if there WAS behaviour.
    # A brand new file of plain assignments has no loops or branches on
    # either side, so every delta is zero and behavior_preserved is
    # vacuously true - it would score `refactor` on code that never existed
    # before. Require something to actually have been preserved.
    if diff.added_behaviors or diff.removed_behaviors:
        context.add(CommitType.REFACTOR, Score.WEAK, c.REASON_BEHAVIOR_PRESERVED)


def score_by_comments(context: Context) -> None:
    diff = context.diff
    if diff is None or not diff.comments_changed:
        return

    # i hate this, we should work on this
    touched_code = any(
        change.after.definitions
        or change.after.declarations
        or change.after.behaviors
        or change.before.definitions
        or change.before.declarations
        or change.before.behaviors
        for change in diff.changes
    )
    if not touched_code:
        context.add(CommitType.DOCS, Score.MEDIUM, c.REASON_COMMENTS_ONLY)


# --- Shape: the weakest evidence, kept last --------------------------------


def score_by_shape(context: Context) -> None:
    added, deleted = context.added_lines, context.deleted_lines
    total = added + deleted
    if total == 0:
        # ?
        return

    if deleted == 0:
        context.add(
            CommitType.FEAT,
            Score.WEAK,
            c.REASON_PURELY_ADDITIVE.format(added=added),
        )
        return

    if added == 0:
        context.add(
            CommitType.CHORE,
            Score.WEAK,
            c.REASON_PURELY_DELETIONS.format(deleted=deleted),
        )
        return

    if abs(added - deleted) / total < c.BALANCED_EDIT_RATIO:
        context.add(
            CommitType.REFACTOR,
            Score.WEAK,
            c.REASON_BALANCED_EDIT.format(added=added, deleted=deleted),
        )
    elif added > deleted:
        context.add(
            CommitType.FEAT,
            Score.WEAK,
            c.REASON_MOSTLY_ADDITIONS.format(added=added, deleted=deleted),
        )
    else:
        # More out than in...
        context.add(
            CommitType.FIX,
            Score.WEAK,
            c.REASON_MOSTLY_DELETIONS.format(added=added, deleted=deleted),
        )


SCORERS = (
    score_by_path,
    score_by_branch,
    score_by_renames,
    score_by_definitions,
    score_by_edits,
    score_by_behaviors,
    score_by_comments,
    score_by_shape,
)


def score_all(context: Context) -> Context:
    for scorer in SCORERS:
        scorer(context)
    return context
