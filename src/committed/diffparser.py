"""Parse `git diff --numstat` text into structured data."""

from .models import NumStat


def parse_count(field: str) -> int | None:
    if field == "-":
        return None
    return int(field)


def parse_numstat(raw: str) -> list[NumStat]:
    stats: list[NumStat] = []

    for line in raw.split("\n"):
        # split("\n") on text ending in a newline yields a trailing "".
        if len(line) == 0:
            continue

        columns = line.split("\t")
        stats.append(
            NumStat(
                added_lines=parse_count(columns[0]),
                deleted_lines=parse_count(columns[1]),
                path=columns[2],
            )
        )

    return stats
