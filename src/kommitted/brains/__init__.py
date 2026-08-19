from collections.abc import Callable

from .base import Brain
from .llm import LLMBrain, LLMError
from .rules.rules import RuleBrain

# Factories, not classes, because `llm` and `auto` are the same class with
# different failure behaviour: `llm` raises when the model is unreachable,
# `auto` quietly uses the rules instead.
#
# Fallback is a property of `auto`, never of failure. Once any mode is
# allowed to degrade quietly, the flags stop meaning anything.
BRAINS: dict[str, Callable[[], Brain]] = {
    "rules": RuleBrain,
    "llm": lambda: LLMBrain(strict=True),
    "auto": lambda: LLMBrain(strict=False),
    # "ollama": OllamaBrain,   <- next
}

DEFAULT_BRAIN = "rules"
BRAINS_NEEDING_DIFF = frozenset({"rules", "llm", "auto"})


def get_brain(name: str = DEFAULT_BRAIN) -> Brain:
    """Look up a brain by name. Raises KeyError listing the valid options."""
    try:
        factory = BRAINS[name]
    except KeyError:
        raise KeyError(
            f"unknown brain {name!r}; available: {', '.join(sorted(BRAINS))}"
        ) from None
    return factory()


__all__ = [
    "BRAINS",
    "BRAINS_NEEDING_DIFF",
    "DEFAULT_BRAIN",
    "Brain",
    "LLMBrain",
    "LLMError",
    "RuleBrain",
    "get_brain",
]
