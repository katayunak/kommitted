"""Parse `git diff --numstat` text into structured data.

The third column is usually a plain path. When git detects a rename it puts
the rename *inside* that column instead, in one of two shapes:

    old/path.go => new/path.go              no shared prefix or suffix
    src/{ => git}/builder.py                shared prefix and suffix
    deep/{nested => other}/q.go             both sides non-empty
    {old => new/sub}/z.go                   nothing shared at the front

Parsing these is worth doing because a moved file is the clearest structural
refactor evidence there is - git already ran the detection, and ignoring it
means feeding a string like `src/{ => git}/builder.py` to code that expects
a real path.
"""

import re

from .models import NumStat

# The braced form: everything before the brace, the two sides, everything
# after. Non-greedy on the inside so `{a => b}` inside a longer path still
# splits at the right arrow.
_BRACED_RENAME = re.compile(r"^(.*)\{(.*?) => (.*?)\}(.*)$")

# The plain form. Checked only after the braced one, because a braced path
# also contains " => ".
_PLAIN_RENAME = re.compile(r"^(.+) => (.+)$")


def parse_count(field: str) -> int | None:
    """`-` means binary, where a line count is meaningless."""
    if field == "-":
        return None
    return int(field)


def split_rename(column: str) -> tuple[str, str | None]:
    """Return (new_path, old_path). old_path is None when nothing moved.

    Collapses the doubled slash that the empty-side form would otherwise
    leave behind: `src/{ => git}/x.py` builds `src//x.py` for the old side.
    """
    braced = _BRACED_RENAME.match(column)
    if braced:
        prefix, old_middle, new_middle, suffix = braced.groups()
        return (
            _join(prefix, new_middle, suffix),
            _join(prefix, old_middle, suffix),
        )

    plain = _PLAIN_RENAME.match(column)
    if plain:
        old, new = plain.groups()
        return new.strip(), old.strip()

    return column, None


def _join(prefix: str, middle: str, suffix: str) -> str:
    """Glue the three parts back together without leaving empty segments."""
    joined = f"{prefix}{middle}{suffix}"
    while "//" in joined:
        joined = joined.replace("//", "/")
    return joined.strip("/") if joined.startswith("/") else joined


def parse_numstat(raw: str) -> list[NumStat]:
    stats: list[NumStat] = []

    for line in raw.split("\n"):
        # split("\n") on text ending in a newline yields a trailing "".
        if not line:
            continue

        columns = line.split("\t")
        if len(columns) < 3:
            continue

        # A rename with no edits prints as three columns; a rename WITH edits
        # can print the paths in columns 3 and 4 instead. Rejoin the tail so
        # both land in the same parser.
        path_column = "\t".join(columns[2:]) if len(columns) > 3 else columns[2]
        new_path, old_path = split_rename(path_column)

        stats.append(
            NumStat(
                added_lines=parse_count(columns[0]),
                deleted_lines=parse_count(columns[1]),
                path=new_path,
                old_path=old_path,
            )
        )

    return stats
