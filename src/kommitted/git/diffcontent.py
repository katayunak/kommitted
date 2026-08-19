import re
from collections import Counter
from dataclasses import dataclass, field

from .. import languages
from ..languages.base import BEHAVIOR_FIELDS, DEFINITION_FIELDS
from ..tokens.edit import EditType, classify_edit

# `+++ b/path/to/file.py` or `+++ /dev/null` for a deleted file.
Diff_HEADER = re.compile(r"^\+\+\+ (?:b/)?(.+)$")


@dataclass(frozen=True)
class Symbol:
    """A named thing found in the diff, e.g. ('func', 'parse_numstat')."""

    kind: str
    name: str
    language: str = "unknown"


@dataclass(frozen=True)
class Behavior:
    """A construct that says something about what the code DOES.

    Carries the text it matched, not just the category. "a conditional was
    added" is weak; "`if err != nil` was added" tells you what is being
    checked, and that is what a commit message wants to say.
    """

    kind: str  # which category, e.g. "conditionals"
    text: str  # the line it was found on, e.g. "if err != nil {"

    # TODO(scope): this says WHAT happened but not TO WHOM. "a conditional
    # was added inside Worker.Run" is what a commit message really wants,
    # and that needs the parser to track which function each line sits in.
    # A diff hunk header often carries it - `@@ -12,3 +12,7 @@ func (w *Worker) Run(`
    # - so the cheapest version is to read that, not to parse scope.


@dataclass(frozen=True)
class Line:
    text: str = ""

    definitions: tuple[Symbol, ...] = ()
    declarations: tuple[Symbol, ...] = ()
    behaviors: tuple[Behavior, ...] = ()

    error_handling: bool = False # ?
    is_comment: bool = False

    def __bool__(self) -> bool:
        return bool(self.text.strip())


@dataclass(frozen=True)
class Change:
    path: str
    language: str

    before: Line = field(default_factory=Line)
    after: Line = field(default_factory=Line)

    @property
    def edits(self) -> frozenset[EditType]:
        """Every way this line changed. A line can change in several ways."""
        return classify_edit(self.before.text, self.after.text)

    @property
    def touches_comment(self) -> bool:
        return self.before.is_comment or self.after.is_comment

    def has_edit(self, edit_type: EditType) -> bool:
        return edit_type in self.edits


@dataclass
class DiffContent:
    changes: list[Change] = field(default_factory=list)
    languages_seen: set[str] = field(default_factory=set)
    manifest_changed: bool = False

    # --- Named things ------------------------------------------------------

    @property
    def added_definitions(self) -> list[Symbol]:
        return [s for ch in self.changes for s in ch.after.definitions]

    @property
    def removed_definitions(self) -> list[Symbol]:
        return [s for ch in self.changes for s in ch.before.definitions]

    @property
    def added_declarations(self) -> list[Symbol]:
        return [s for ch in self.changes for s in ch.after.declarations]

    @property
    def removed_declarations(self) -> list[Symbol]:
        return [s for ch in self.changes for s in ch.before.declarations]

    # only on + side, so purely new; a feat sign
    @property
    def new_definitions(self) -> list[Symbol]:
        removed = {s.name for s in self.removed_definitions}
        return [s for s in self.added_definitions if s.name not in removed]

    # on both sides, something moved; a refactore?fix?
    @property
    def moved_definitions(self) -> list[Symbol]:
        removed = {s.name for s in self.removed_definitions}
        return [s for s in self.added_definitions if s.name in removed]

    # --- Behaviors ---------------------------------------------------------

    @property
    def added_behaviors(self) -> Counter[str]:
        return Counter(b.kind for ch in self.changes for b in ch.after.behaviors)

    @property
    def removed_behaviors(self) -> Counter[str]:
        return Counter(b.kind for ch in self.changes for b in ch.before.behaviors)

    def behavior_delta(self, name: str) -> int:
        """Net change in one behavior: positive means the construct appeared.

        This is the number the fix/refactor question actually needs. A pure
        refactor moves code, so its deltas sit near zero even when hundreds
        of lines changed; a fix that adds a nil check moves `conditionals`
        up without moving anything else.
        """
        return self.added_behaviors[name] - self.removed_behaviors[name]

    @property
    def behavior_preserved(self) -> bool:
        """True when no behavior category moved at all.

        Fowler's definition of refactoring, as far as regex can approximate
        it: the structure changed, what the program does did not. Necessary
        evidence for `refactor`, nowhere near sufficient - a changed literal
        moves nothing here and still changes behavior.
        """
        return all(self.behavior_delta(name) == 0 for name in BEHAVIOR_FIELDS)

    # --- Edits -------------------------------------------------------------

    def with_edit(self, edit_type: EditType) -> list[Change]:
        """Every line that changed in this way. The fix/refactor workhorse."""
        return [change for change in self.changes if change.has_edit(edit_type)]

    @property
    def edit_counts(self) -> Counter[str]:
        """How many lines had each kind of edit. One line can count twice."""
        return Counter(
            edit.value for change in self.changes for edit in change.edits
        )

    # --- Comments ----------------------------------------------------------

    @property
    def added_comments(self) -> int:
        return sum(1 for ch in self.changes if ch.after.is_comment)

    @property
    def removed_comments(self) -> int:
        return sum(1 for ch in self.changes if ch.before.is_comment)

    @property
    def comments_changed(self) -> int:
        """How many comment lines this diff touched, either side."""
        return self.added_comments + self.removed_comments

    # --- Legacy ------------------------------------------------------------

    @property
    def error_handling_added(self) -> int:
        return sum(1 for ch in self.changes if ch.after.error_handling)


def named_in(
    line: str, language: languages.Language, fields: tuple[str, ...]
) -> tuple[Symbol, ...]:
    """Find named things in one source line, across the given rule fields."""
    found = []
    for attr in fields:
        for kind, pattern in getattr(language, attr):
            match = pattern.search(line)
            if match:
                found.append(Symbol(kind, match.group(1), language.name))
    return tuple(found)


def _behaviors_in(
    text: str, behavior_patterns: tuple[tuple[str, re.Pattern[str]], ...]
) -> tuple[Behavior, ...]:
    """Find behaviour constructs in one line, keeping what each one matched."""
    found = []
    for kind, pattern in behavior_patterns:
        match = pattern.search(text)
        if match:
            found.append(Behavior(kind=kind, text=text.strip()))
    return tuple(found)


def read_line(
    text: str,
    language: languages.Language,
    behavior_patterns: tuple[tuple[str, re.Pattern[str]], ...],
) -> Line:
    """Match every rule against one source line.

    A comment line is recorded as a comment and nothing else. That is the
    whole rule: if the language's comment syntax matches, the line is prose,
    so matching code patterns against it can only produce lies. A
    commented-out `func Foo()` is not a new function.

    TODO(block-comments): languages.is_comment judges one line at a time, so
    the middle of a `/* ... */` block still reads as code and gets scanned.
    Fixing it needs an "inside a block comment" flag on the parser, reset at
    each `+++` header. Until then C-style block comments are undercounted -
    the safe direction, since the failure is missing a signal rather than
    inventing one.
    """
    if not text.strip():
        return Line(text=text)

    if languages.is_comment(text, language):
        return Line(text=text, is_comment=True)

    return Line(
        text=text,
        definitions=named_in(text, language, DEFINITION_FIELDS),
        declarations=named_in(text, language, ("declarations",)),
        behaviors=_behaviors_in(text, behavior_patterns),
        error_handling=any(p.search(text) for p in language.error_handling),
    )


def parse_diff(diff: str) -> DiffContent:
    content = DiffContent()
    current = languages.UNKNOWN
    behaviors = languages.behavior_patterns(current)
    path = ""

    minus: list[str] = []
    plus: list[str] = []

    def flush() -> None:
        for i in range(max(len(minus), len(plus))):
            before = minus[i] if i < len(minus) else ""
            after = plus[i] if i < len(plus) else ""
            content.changes.append(
                Change(
                    path=path,
                    language=current.name,
                    before=read_line(before, current, behaviors),
                    after=read_line(after, current, behaviors),
                )
            )
        minus.clear()
        plus.clear()

    for line in diff.split("\n"):
        # '+++ b/x.py' starts with '+' but is a header, not a change - it
        # must be handled before the '+' branch or every filename would look
        # like added code.
        header = Diff_HEADER.match(line)
        if header:
            flush()
            path = header.group(1)
            current = languages.for_path(path)
            behaviors = languages.behavior_patterns(current)
            if current is not languages.UNKNOWN:
                content.languages_seen.add(current.name)
            if languages.is_manifest(path):
                content.manifest_changed = True
            continue

        # '--- a/x.py' is the other header half.
        if line.startswith("---"):
            flush()
            continue

        if line.startswith("-"):
            # A '-' after a run of '+' means a new edit block started.
            if plus:
                flush()
            minus.append(line[1:])
        elif line.startswith("+"):
            plus.append(line[1:])
        else:
            # Context line, hunk header, or '\ No newline at end of file'.
            flush()

    flush()
    return content
