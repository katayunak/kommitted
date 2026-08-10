from dataclasses import dataclass, field


@dataclass
class NumStat:
    """One changed file, as reported by `git diff --numstat`.

    added_lines/deleted_lines are None for binary files - git prints "-"
    """

    added_lines: int | None
    deleted_lines: int | None
    path: str

    # TODO: renames are not handled. git --numstat emits renames in two forms:
    #   "0\t0\told.go => new.go"        and
    #   "0\t0\tinternal/{git => brain}/x.go"
    # Both currently land in `path` verbatim, so `path` is not always a real
    # file path. Decide later whether to parse these into old_path/new_path
    # fields, or pass --no-renames to git to sidestep it entirely.

    @property
    def churn(self) -> int:
        """Total lines touched. Binary files count as 0."""
        return (self.added_lines or 0) + (self.deleted_lines or 0)


@dataclass
class Classification:
    """A brain's verdict on what kind of commit this is.

    `confidence` and `reasons` are how you debug a wrong answer, and how you compare one brain against another - which is
    the whole point of having a Brain interface.
    """

    type: str
    confidence: float  # 0.0 - 1.0
    reasons: list[str] = field(default_factory=list)
