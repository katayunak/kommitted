from .base import Brain
from .llm import LLMBrain
from .rules import RuleBrain

# The registry the CLI resolves --brain against.
BRAINS: dict[str, type] = {
    "rules": RuleBrain,
    "llm": LLMBrain,
    # "ollama": OllamaBrain,   <- next
}

# Rules stay the default: free, offline, instant, and never surprises you.
DEFAULT_BRAIN = "rules"

# Brains that need the full diff text, not just the file stats. The CLI uses
# this to avoid fetching a large diff the rule brain would ignore.
BRAINS_NEEDING_DIFF = frozenset({"rules", "llm"})


def get_brain(name: str = DEFAULT_BRAIN) -> Brain:
    """Look up a brain by name. Raises KeyError listing the valid options."""
    try:
        return BRAINS[name]()
    except KeyError:
        raise KeyError(
            f"unknown brain {name!r}; available: {', '.join(sorted(BRAINS))}"
        ) from None


__all__ = [
    "BRAINS",
    "BRAINS_NEEDING_DIFF",
    "DEFAULT_BRAIN",
    "Brain",
    "LLMBrain",
    "RuleBrain",
    "get_brain",
]
