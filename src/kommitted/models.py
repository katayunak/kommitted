from dataclasses import dataclass, field


@dataclass(frozen=True)
class NumStat:
    """One changed file, as reported by `git diff --numstat`.
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
    def total_lines_changed(self) -> int:
        """Total lines touched. Binary files count as 0."""
        return (self.added_lines or 0) + (self.deleted_lines or 0)


@dataclass(frozen=True)
class Classification:
    """A brain's verdict on what kind of commit this is.
    """

    type: str
    confidence: float  # 0.0 - 1.0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    subject: str | None = None

    def with_reason(self, reason: str) -> "Classification":
        """A copy with `reason` at the front. Used by the LLM fallback path."""
        return Classification(
            type=self.type,
            confidence=self.confidence,
            reasons=(reason, *self.reasons),
            subject=self.subject,
        )
