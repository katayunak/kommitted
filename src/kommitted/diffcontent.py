"""Extract meaning from the raw diff text, not just line counts.

`--numstat` tells you 40 lines changed. It cannot tell you whether those
lines added a function, renamed one, or wrapped something in a try/except.
That information only exists in the diff body - so this module reads it.

Patterns are selected per file, by extension (see languages.py). The parser
tracks which file each hunk belongs to as it walks the diff, so a `.py` hunk
is never matched against Go patterns.

Deliberately regex-based, not a real parser. A proper approach would use a
per-language AST, but a diff is a *fragment* - half a function, no imports,
often unbalanced braces - so most parsers refuse to parse it at all. Regex
degrades gracefully where a parser fails outright. That is the trade.
"""

import re
from dataclasses import dataclass, field

from . import languages

# `+++ b/path/to/file.py` or `+++ /dev/null` for a deleted file.
FILE_HEADER = re.compile(r"^\+\+\+ (?:b/)?(.+)$")


@dataclass(frozen=True)
class Symbol:
    """A named thing found in the diff, e.g. ('func', 'parse_numstat')."""

    kind: str
    name: str
    language: str = "unknown"


@dataclass
class DiffContent:
    """What the diff body says, beyond how many lines moved."""

    added: list[Symbol] = field(default_factory=list)
    removed: list[Symbol] = field(default_factory=list)
    error_handling_added: int = 0
    # Which languages this changeset actually touched.
    languages_seen: set[str] = field(default_factory=set)
    manifest_changed: bool = False

    @property
    def new_symbols(self) -> list[Symbol]:
        """Symbols that appear only on the + side - genuinely new code.

        A symbol on both sides was edited or moved, not created. That
        distinction is the difference between `feat` and `refactor`.
        """
        removed_names = {s.name for s in self.removed}
        return [s for s in self.added if s.name not in removed_names]

    @property
    def moved_symbols(self) -> list[Symbol]:
        """Symbols present on both sides - the signature of a refactor."""
        removed_names = {s.name for s in self.removed}
        return [s for s in self.added if s.name in removed_names]


def symbols_in(line: str, language: languages.Language) -> list[Symbol]:
    """Find declarations in one source line, using one language's rules."""
    found = []
    for kind, pattern in language.symbols:
        match = pattern.search(line)
        if match:
            found.append(Symbol(kind, match.group(1), language.name))
    return found


def parse_diff(diff: str) -> DiffContent:
    """Read a unified diff and pull out what changed semantically."""
    content = DiffContent()
    current = languages.UNKNOWN

    for line in diff.split("\n"):
        # Track which file we're inside. '+++ b/x.py' starts with '+' but is
        # a header, not a change - it must be handled before the '+' branch
        # or every filename would look like added code.
        header = FILE_HEADER.match(line)
        if header:
            path = header.group(1)
            current = languages.for_path(path)
            if current is not languages.UNKNOWN:
                content.languages_seen.add(current.name)
            if languages.is_manifest(path):
                content.manifest_changed = True
            continue

        # '--- a/x.py' is the other header half.
        if line.startswith("---"):
            continue

        if line.startswith("+"):
            body = line[1:]
            content.added.extend(symbols_in(body, current))
            if any(p.search(body) for p in current.error_handling):
                content.error_handling_added += 1
        elif line.startswith("-"):
            content.removed.extend(symbols_in(line[1:], current))

    return content
