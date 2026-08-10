from .base import Brain
from .rules import RuleBrain

# The registry the CLI resolves --brain against.
BRAINS: dict[str, type] = {
    "rules": RuleBrain,
    # "llm": LLMBrain,
}

DEFAULT_BRAIN = "rules"


def get_brain(name: str = DEFAULT_BRAIN) -> Brain:
    try:
        return BRAINS[name]()
    except KeyError:
        raise KeyError(
            f"unknown brain {name!r}; available: {', '.join(sorted(BRAINS))}"
        ) from None


__all__ = ["Brain", "RuleBrain", "BRAINS", "DEFAULT_BRAIN", "get_brain"]
