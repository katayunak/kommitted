import json
import sys as s
from dataclasses import asdict, dataclass


@dataclass
class NumStat:
    added_lines: int | None
    deleted_lines: int | None
    path: str
    # TODO: renames are not handled. git --numstat emits renames in two forms:
    #   "0\t0\told.go => new.go"        and
    #   "0\t0\tinternal/{git => brain}/x.go"
    # Both currently land in `path` verbatim, so `path` is not always a real
    # file path. Decide later whether to parse these into old_path/new_path
    # fields, or pass -M/--no-renames to git to sidestep it entirely.

def listen_on_stdin() -> str:
    return s.stdin.read()  # it blocks until data arrives or EOF

def parse_count(field: str) -> int | None:
    if field == "-":
        return None
    return int(field)

def num_stat_parser(diff_num_stat: str) -> list[NumStat]:
    """Pure function: numstat text in, structured data out.

    Takes the text as an argument instead of reading stdin itself. That one
    change is what makes this testable - a test can hand it any string it
    likes without faking a pipe.
    """
    separated_by_line = diff_num_stat.split("\n")

    word_batches: list[list[str]] = []
    for batch in separated_by_line:
        if len(batch) == 0:
            continue

        new_word_batch = batch.split("\t")
        word_batches.append(new_word_batch)

    stats: list[NumStat] = []
    for words in word_batches:
        new_stat = NumStat(
            added_lines=parse_count(words[0]),
            deleted_lines=parse_count(words[1]),
            path=words[2],
        )
        stats.append(new_stat)

    return stats

def main() -> None:
    """All the I/O lives here: read stdin, print JSON to stdout."""
    raw = listen_on_stdin()
    stats = num_stat_parser(raw)
    print(json.dumps([asdict(stat) for stat in stats]))

if __name__ == "__main__":
    main()
