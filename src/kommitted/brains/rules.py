"""Rule-based brain: explicit heuristics, no model, no network, no API key.

Fast, free, offline, completely explainable - every answer carries the rules
that produced it.

--------------------------------------------------------------------------
ROADMAP - this module is the weakest part of the project and needs work
--------------------------------------------------------------------------

Signals we HAVE and use:
  * file paths          -> test / docs / chore                (reliable)
  * line counts         -> feat / fix / refactor              (weak guesses)
  * diff body symbols   -> new vs moved functions             (decent)

Signals we DON'T have yet, roughly in order of value:

  1. FILE STATUS (A/M/D/R). `git diff --staged --name-status` gives this.
     Numstat cannot distinguish a brand-new file from an appended one - both
     print "40  0  file". With status we could say "add" vs "update"
     correctly, call all-D commits `chore`, and detect renames as `refactor`.
     This is the single biggest win available and it is cheap.

  2. BRANCH NAME. gitrunner.current_branch() already exists and is unused.
     `fix/login-crash` is stronger evidence than any line count. Needs a
     precedence rule: does the branch beat the path rules, or lose to them?

  3. IMPORT/DEPENDENCY CHANGES. Touching go.mod, requirements.txt or
     package.json alongside code usually means `build` or `chore(deps)`.

  4. TEST-TO-SOURCE RATIO. Source + its matching test in one commit is
     almost always `feat` or `fix`, never `chore`.

  5. COMMIT HISTORY. `git log` shows how THIS team writes messages. Learning
     their conventions instead of imposing ours is the difference between a
     tool people use and one they turn off.

Known ceiling: distinguishing `feat` from `fix` needs semantic understanding
of *what the code now does differently*. Symbol names get us closer, but a
null check added to fix a crash and a null check added as part of a new
feature look identical here. That gap is the LLM brain's whole reason to
exist - not because "AI is better", but because this specific judgement
requires reading code, and regex cannot read.

Every threshold and confidence value below is an UNVALIDATED GUESS. They
should be tuned against a labelled set of real commits, not adjusted by feel.
"""

from .. import constants as c
from ..diffcontent import parse_diff
from ..models import Classification, NumStat


def is_test(path: str) -> bool:
    p = path.lower()
    return any(marker in p for marker in c.TEST_MARKERS)


def is_doc(path: str) -> bool:
    p = path.lower()
    return p.endswith(c.DOC_EXTENSIONS) or any(d in p for d in c.DOC_DIRS)


def is_config(path: str) -> bool:
    p = path.lower()
    name = p.rsplit("/", 1)[-1]
    return name in c.CONFIG_NAMES or any(d in p for d in c.CONFIG_DIRS)


class RuleBrain:
    name = "rules"

    def classify(self, stats: list[NumStat], diff: str = "") -> Classification:
        if not stats:
            return Classification(
                c.TYPE_CHORE, c.CONFIDENCE_NONE, (c.REASON_NOTHING_STAGED,)
            )

        paths = [st.path for st in stats]
        added = sum(st.added_lines or 0 for st in stats)
        deleted = sum(st.deleted_lines or 0 for st in stats)

        # --- Tier 1: rules by path -----------------------------------------
        # The reliable ones. Order matters: a change touching only tests is a
        # test commit even if it adds 200 lines.

        if all(is_test(p) for p in paths):
            return Classification(
                c.TYPE_TEST,
                c.CONFIDENCE_PATH_STRONG,
                (c.REASON_ALL_TESTS.format(count=len(paths)),),
            )

        if all(is_doc(p) for p in paths):
            return Classification(
                c.TYPE_DOCS, c.CONFIDENCE_PATH_STRONG, (c.REASON_ONLY_DOCS,)
            )

        if all(is_config(p) for p in paths):
            return Classification(
                c.TYPE_CHORE, c.CONFIDENCE_PATH_WEAK, (c.REASON_ONLY_CONFIG,)
            )

        # --- Tier 2: rules by diff content ---------------------------------
        # Only available when the caller passed the diff body. Better than
        # line counts because a symbol name carries meaning.

        if diff:
            verdict = self._classify_by_content(diff)
            if verdict is not None:
                return verdict

        # --- Tier 3: rules by shape ----------------------------------------
        # Pure guesswork. Line counts carry no meaning, and the low
        # confidence values say so out loud.

        if deleted == 0 and added > 0:
            return Classification(
                c.TYPE_FEAT,
                c.CONFIDENCE_SHAPE_ADDITIVE,
                (
                    c.REASON_PURELY_ADDITIVE.format(added=added),
                    c.REASON_NEW_CODE_IS_FEATURE,
                ),
            )

        if added == 0 and deleted > 0:
            return Classification(
                c.TYPE_CHORE,
                c.CONFIDENCE_SHAPE_DELETIONS,
                (
                    c.REASON_PURELY_DELETIONS.format(deleted=deleted),
                    c.REASON_COULD_BE_CLEANUP,
                ),
            )

        total = added + deleted
        if total > 0 and abs(added - deleted) / total < c.BALANCED_EDIT_RATIO:
            return Classification(
                c.TYPE_REFACTOR,
                c.CONFIDENCE_SHAPE_BALANCED,
                (
                    c.REASON_BALANCED_EDIT.format(added=added, deleted=deleted),
                    c.REASON_SIMILAR_IN_OUT,
                ),
            )

        if added > deleted:
            return Classification(
                c.TYPE_FEAT,
                c.CONFIDENCE_SHAPE_MOSTLY_ADD,
                (c.REASON_MOSTLY_ADDITIONS.format(added=added, deleted=deleted),),
            )

        return Classification(
            c.TYPE_FIX,
            c.CONFIDENCE_SHAPE_FALLBACK,
            (
                c.REASON_MOSTLY_DELETIONS.format(added=added, deleted=deleted),
                c.REASON_NEEDS_DIFF_CONTENT,
            ),
        )

    def _classify_by_content(self, diff: str) -> Classification | None:
        content = parse_diff(diff)
        new = content.new_symbols
        moved = content.moved_symbols

        # Brand-new named things and nothing removed -> genuinely new code.
        if new and not moved:
            first = new[0]
            return Classification(
                type=c.TYPE_FEAT,
                confidence=c.CONFIDENCE_CONTENT_NEW_SYMBOL,
                reasons=(
                    c.REASON_NEW_SYMBOLS.format(
                        names=", ".join(s.name for s in new[:3]),
                        kind=first.kind,
                    ),
                ),
                # Complete subject, not a bare name - see Classification.subject.
                subject=f"{c.VERBS[c.TYPE_FEAT]} {first.name}",
            )

        # The same names removed and re-added -> code moved, not grew.
        if moved and not new:
            return Classification(
                type=c.TYPE_REFACTOR,
                confidence=c.CONFIDENCE_CONTENT_MOVED_SYMBOL,
                reasons=(
                    c.REASON_MOVED_SYMBOLS.format(
                        names=", ".join(s.name for s in moved[:3])
                    ),
                ),
                subject=f"{c.VERBS[c.TYPE_REFACTOR]} {moved[0].name}",
            )

        # No new names, but error handling appeared -> probably a fix.
        if content.error_handling_added and not new:
            return Classification(
                type=c.TYPE_FIX,
                confidence=c.CONFIDENCE_CONTENT_ERROR_HANDLING,
                reasons=(
                    c.REASON_ERROR_HANDLING.format(
                        count=content.error_handling_added
                    ),
                ),
            )

        return None
