from typing import Protocol

from ..git.models import Classification, NumStat


class Brain(Protocol):
    """What every brain must look like.

    A Protocol is checked by type checkers, NOT at runtime - Python will
    happily call a brain whose signature drifted from this one and only fail
    when the argument count stops matching. `test_brains.py` walks the
    registry and calls every brain through the full signature, which is what
    actually enforces this.
    """

    name: str

    def classify(
        self, stats: list[NumStat], diff: str = "", branch: str = ""
    ) -> Classification:
        ...
