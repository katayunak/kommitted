from enum import Enum


class CommitType(str, Enum):
    FEAT = "feat"
    FIX = "fix"
    REFACTOR = "refactor"
    DOCS = "docs"
    TEST = "test"
    CHORE = "chore"


class Score(int, Enum):
    WEAK = 5  # could easily mean something else
    MEDIUM = 10  # usually right
    STRONG = 15  # hard to explain any other way
