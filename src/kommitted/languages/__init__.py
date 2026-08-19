import re

from .base import BEHAVIOR_FIELDS, Comment, Language, NamedPattern
from .go import GO
from .javascript import JAVASCRIPT
from .python import PYTHON

__all__ = [
    "BEHAVIOR_FIELDS",
    "GO",
    "JAVASCRIPT",
    "LANGUAGES",
    "PYTHON",
    "UNKNOWN",
    "Comment",
    "Language",
    "NamedPattern",
    "behavior_patterns",
    "for_path",
    "is_comment",
    "is_manifest",
]

LANGUAGES: tuple[Language, ...] = (GO, PYTHON, JAVASCRIPT)

_BY_EXTENSION: dict[str, Language] = {
    ext: lang for lang in LANGUAGES for ext in lang.extensions
}

UNKNOWN = Language(name="unknown", extensions=())

_MANIFEST_NAMES: frozenset[str] = frozenset(
    name.lower() for lang in LANGUAGES for name in lang.manifests
)


def for_path(path: str) -> Language:
    """Pick the rules for a file, by extension. Never raises."""
    dot = path.rfind(".")
    if dot == -1:
        return UNKNOWN
    return _BY_EXTENSION.get(path[dot:].lower(), UNKNOWN)


def is_manifest(path: str) -> bool:
    """True for dependency files like go.mod or package.json."""
    return path.rsplit("/", 1)[-1].lower() in _MANIFEST_NAMES


def is_comment(line: str, language: Language) -> bool:
    """True if this source line is *only* a comment."""
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith(language.comments.line):
        return True
    return any(
        stripped.startswith(open_)
        and stripped.endswith(close)
        and len(stripped) >= len(open_) + len(close)
        for open_, close in language.comments.block
    )


def behavior_patterns(language: Language) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """The (name, pattern) pairs to count for this language.

    Skips categories the language doesn't have - Go has no `while`, Python
    has no pointers - so callers never run a regex that cannot match.
    """
    pairs = []
    for name in BEHAVIOR_FIELDS:
        pattern = getattr(language, name)
        if pattern is not None:
            pairs.append((name, pattern))
    return tuple(pairs)
