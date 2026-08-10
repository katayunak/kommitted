"""Rule-based brain: explicit heuristics, no model, no network, no API key.

Fast, free, offline, and completely explainable - every answer carries the
rules that produced it. Its ceiling is real though: line counts cannot
distinguish a feature from a bug fix, because that difference lives in the
*content* of the diff. The low confidence values below say so honestly.
"""

from .. import constants as c
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
    """Implements the Brain protocol without inheriting from it."""

    name = "rules"

    def classify(self, stats: list[NumStat], diff: str = "") -> Classification:
        # `diff` is accepted and ignored - rules work on structure only.
        if not stats:
            return Classification(
                c.TYPE_CHORE, c.CONFIDENCE_NONE, [c.REASON_NOTHING_STAGED]
            )

        paths = [st.path for st in stats]
        added = sum(st.added_lines or 0 for st in stats)
        deleted = sum(st.deleted_lines or 0 for st in stats)

        # --- Rules by path: the reliable ones ------------------------------
        # Order matters. A change touching only tests is a test commit even
        # if it adds 200 lines.

        if all(is_test(p) for p in paths):
            return Classification(
                c.TYPE_TEST,
                c.CONFIDENCE_PATH_STRONG,
                [c.REASON_ALL_TESTS.format(count=len(paths))],
            )

        if all(is_doc(p) for p in paths):
            return Classification(
                c.TYPE_DOCS, c.CONFIDENCE_PATH_STRONG, [c.REASON_ONLY_DOCS]
            )

        if all(is_config(p) for p in paths):
            return Classification(
                c.TYPE_CHORE, c.CONFIDENCE_PATH_WEAK, [c.REASON_ONLY_CONFIG]
            )

        # --- Rules by shape: these are guesses ------------------------------

        if deleted == 0 and added > 0:
            return Classification(
                c.TYPE_FEAT,
                c.CONFIDENCE_SHAPE_ADDITIVE,
                [
                    c.REASON_PURELY_ADDITIVE.format(added=added),
                    c.REASON_NEW_CODE_IS_FEATURE,
                ],
            )

        if added == 0 and deleted > 0:
            return Classification(
                c.TYPE_CHORE,
                c.CONFIDENCE_SHAPE_DELETIONS,
                [
                    c.REASON_PURELY_DELETIONS.format(deleted=deleted),
                    c.REASON_COULD_BE_CLEANUP,
                ],
            )

        total = added + deleted
        if total > 0 and abs(added - deleted) / total < c.BALANCED_EDIT_RATIO:
            return Classification(
                c.TYPE_REFACTOR,
                c.CONFIDENCE_SHAPE_BALANCED,
                [
                    c.REASON_BALANCED_EDIT.format(added=added, deleted=deleted),
                    c.REASON_SIMILAR_IN_OUT,
                ],
            )

        if added > deleted:
            return Classification(
                c.TYPE_FEAT,
                c.CONFIDENCE_SHAPE_MOSTLY_ADD,
                [c.REASON_MOSTLY_ADDITIONS.format(added=added, deleted=deleted)],
            )

        return Classification(
            c.TYPE_FIX,
            c.CONFIDENCE_SHAPE_FALLBACK,
            [
                c.REASON_MOSTLY_DELETIONS.format(added=added, deleted=deleted),
                c.REASON_NEEDS_DIFF_CONTENT,
            ],
        )
