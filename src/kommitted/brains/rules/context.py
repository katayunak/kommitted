from dataclasses import dataclass, field

from ...git.diffcontent import Change, DiffContent, parse_diff
from ...git.models import Classification, NumStat
from .commit_type import CommitType, Score

CONFIDENT_SCORE = 30.0

# Last resort when two types score the same AND have the same number of
# reasons. Ordered most specific first: claiming `feat` when it was really
# `chore` is a smaller error than the reverse, because `chore` is where
# anything unrecognised already lands.
TIE_BREAK_ORDER: tuple[CommitType, ...] = (
    CommitType.FIX,
    CommitType.FEAT,
    CommitType.REFACTOR,
    CommitType.TEST,
    CommitType.DOCS,
    CommitType.CHORE,
)


@dataclass
class Context:
    files: list[NumStat] = field(default_factory=list)
    diff: DiffContent | None = None
    branch: str = ""

    scores: dict[CommitType, float] = field(default_factory=dict)
    reasons: dict[CommitType, list[str]] = field(default_factory=dict)

    @classmethod
    def collect(
        cls, files: list[NumStat], diff_text: str = "", branch: str = ""
    ) -> "Context":
        return cls(
            files=files,
            diff=parse_diff(diff_text) if diff_text else None,
            branch=branch,
        )

    @property
    def changes(self) -> list[Change]:
        return self.diff.changes if self.diff else []

    @property
    def paths(self) -> list[str]:
        return [f.path for f in self.files]

    @property
    def added_lines(self) -> int:
        return sum(f.added_lines or 0 for f in self.files)

    @property
    def deleted_lines(self) -> int:
        return sum(f.deleted_lines or 0 for f in self.files)

    @property
    def total_lines(self) -> int:
        return self.added_lines + self.deleted_lines

    # --- Scoring -----------------------------------------------------------

    def add(self, commit_type: CommitType, score: Score | float, reason: str) -> None:
        self.scores[commit_type] = self.scores.get(commit_type, 0.0) + float(score)
        self.reasons.setdefault(commit_type, []).append(reason)

    @property
    def total_score(self) -> float:
        return sum(self.scores.values())

    @property
    def best_type(self) -> CommitType | None:
        """Ties break on how many separate rules agreed, then a fixed order.

        Without this, `max()` returns whichever key was inserted first -
        which means THE ORDER SCORERS RUN IN silently decides close calls.
        That is exactly the coupling the voting design exists to remove.
        """
        if not self.scores:
            return None

        def rank(commit_type: CommitType) -> tuple[float, int, int]:
            return (
                self.scores[commit_type],
                len(self.reasons.get(commit_type, [])),
                -TIE_BREAK_ORDER.index(commit_type),
            )

        return max(self.scores, key=rank)

    def classify(self) -> Classification:
        winner = self.best_type
        if winner is None or self.total_score <= 0:
            return Classification(
                type=CommitType.CHORE.value,
                confidence=0.0,
                reasons=("no rule matched :(",),
            )

        best = self.scores[winner]
        agreement = best / self.total_score
        strength = min(1.0, best / CONFIDENT_SCORE)

        return Classification(
            type=winner.value,
            confidence=agreement * strength,
            reasons=tuple(self.reasons.get(winner, [])),
        )
