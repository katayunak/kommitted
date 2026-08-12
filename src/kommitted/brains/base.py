from typing import Protocol

from ..models import Classification, NumStat


class Brain(Protocol):
    """Anything that can classify a set of staged changes."""

    name: str

    def classify(self, stats: list[NumStat], diff: str = "") -> Classification:
        pass
