from dataclasses import dataclass, field


@dataclass(frozen=True)
class NumStat:
    """One changed file, as reported by `git diff --numstat`."""

    added_lines: int | None
    deleted_lines: int | None

    # Always a real path. When git reported a rename this is the NEW path,
    # already unpacked out of git's `src/{ => git}/x.py` notation.
    path: str

    # Where the file came from, or None if it did not move. Git ran the
    # rename detection for us; throwing the answer away would mean
    # re-deriving it worse.
    old_path: str | None = None

    @property
    def total_lines_changed(self) -> int:
        """Total lines touched. Binary files count as 0."""
        return (self.added_lines or 0) + (self.deleted_lines or 0)

    @property
    def is_rename(self) -> bool:
        return self.old_path is not None

    @property
    def moved_directory(self) -> bool:
        """True when the file changed directory, not just filename.

        Worth separating: `a/x.go -> a/y.go` renames one thing, while
        `a/x.go -> b/x.go` moves code between components. The second is the
        stronger structural signal - it is what "reorganising a package"
        looks like in a diff.
        """
        if self.old_path is None:
            return False
        return _directory(self.old_path) != _directory(self.path)

    @property
    def renamed_in_place(self) -> bool:
        """True when only the filename changed, not the directory."""
        return self.is_rename and not self.moved_directory


def _directory(path: str) -> str:
    """Everything before the last slash, or "" for a top-level file."""
    head, slash, _ = path.rpartition("/")
    return head if slash else ""


@dataclass(frozen=True)
class Classification:
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
