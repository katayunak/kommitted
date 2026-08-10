import os

from . import constants as c
from .models import Classification, NumStat


def scope(stats: list[NumStat]) -> str:
    if not stats:
        return ""

    nested = [st for st in stats if os.path.dirname(st.path)]

    # Everything sits at the repo root - there is no component to name.
    if not nested:
        return ""

    if len(nested) < len(stats):
        # Mixed: some files at the root, some nested. Only claim a scope if
        # the nested files carry most of the weight.
        total = sum(st.churn for st in stats)
        nested_churn = sum(st.churn for st in nested)
        # total == 0 means every file was empty or binary; no basis to judge.
        if total == 0 or nested_churn / total < c.SCOPE_DOMINANCE:
            return ""

    # commonpath finds the deepest shared directory. It raises on an empty
    # list and on mixed absolute/relative paths, so guard both.
    try:
        common = os.path.commonpath([os.path.dirname(st.path) for st in nested])
    except ValueError:
        return ""  # can't determine a safe scope, so use no scope

    # Use only the last segment: 'internal/git' -> 'git'. Scopes are component
    # names, not paths.
    return os.path.basename(common)


def subject(classification: Classification, stats: list[NumStat]) -> str:
    verb = c.VERBS.get(classification.type, c.DEFAULT_VERB)

    if len(stats) == 1:
        # One file -> name it. 'model/classifier.py' -> 'classifier'
        name = os.path.basename(stats[0].path)
        stem = os.path.splitext(name)[0]
        return f"{verb} {stem}"

    component = scope(stats)
    if component:
        return f"{verb} {component}"

    return f"{verb} {len(stats)} files"


def format_file_line(st: NumStat) -> str:
    if st.added_lines is None or st.deleted_lines is None:
        return f"- {st.path} (binary)"
    return f"- {st.path} (+{st.added_lines} -{st.deleted_lines})"


def build(classification: Classification, stats: list[NumStat]) -> str:
    """Assemble the full message.

    Format:
        <type>(<scope>): <subject>
        <BLANK LINE>
        - file (+a -d)

    The blank line is mandatory. Git treats line 1 as the summary and
    everything after the blank line as the body; without it, `git log
    --oneline` prints the entire message as the subject.
    """
    component = scope(stats)
    head = f"{classification.type}({component})" if component else classification.type
    header = f"{head}: {subject(classification, stats)}"

    # Truncate rather than emit an oversized subject. Rare, but a 200-char
    # subject line is worse than a clipped one.
    if len(header) > c.MAX_SUBJECT_LEN:
        header = header[: c.MAX_SUBJECT_LEN - 3] + "..."

    if not stats:
        return header

    body = "\n".join(format_file_line(st) for st in stats)
    return f"{header}\n\n{body}"
