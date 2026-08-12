import os

from . import constants as c
from .models import Classification, NumStat


def scope(stats: list[NumStat]) -> str:
    if not stats:
        return ""

    nested = [st for st in stats if os.path.dirname(st.path)]
    if not nested:
        return ""  # everything sits at the repo root

    if len(nested) < len(stats):
        # Mixed: some files at the root, some nested. Only claim a scope if
        # the nested files carry most of the weight.
        total_changed = sum(st.total_lines_changed for st in stats)
        nested_changed = sum(st.total_lines_changed for st in nested)

        if total_changed == 0 or nested_changed / total_changed < c.SCOPE_DOMINANCE:
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

    if classification.subject:
        # Complete subject, verb included. Used verbatim - the builder makes
        # no decisions about its shape.
        return classification.subject.strip()

    if len(stats) == 1:
        # One file has changed
        name = os.path.basename(stats[0].path)
        stem = os.path.splitext(name)[0]
        return f"{verb} {stem}"

    changed_scope = scope(stats)
    if changed_scope:
        return f"{verb} {changed_scope}"

    # todo: this may sound silly, needs to be stronger
    return f"{verb} {len(stats)} files"


def format_file_line(st: NumStat) -> str:
    if st.added_lines is None or st.deleted_lines is None:
        return f"- {st.path} (binary)"
    return f"- {st.path} (+{st.added_lines} -{st.deleted_lines})"


def build(classification: Classification, stats: list[NumStat]) -> str:
    """
    Format:
        <type>(<scope>): <subject>
        <BLANK LINE>
        - file (+a -d)
    """
    changed_scope = scope(stats)
    head = classification.type

    if changed_scope:
        head = f"{classification.type}({changed_scope})"
    header = f"{head}: {subject(classification, stats)}"

    if len(header) > c.MAX_SUBJECT_LEN:
        header = header[: c.MAX_SUBJECT_LEN - 3] + "..."

    if not stats:
        return header

    body = "\n".join(format_file_line(st) for st in stats)
    return f"{header}\n\n{body}"
