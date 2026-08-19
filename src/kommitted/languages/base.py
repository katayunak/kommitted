import re
from dataclasses import dataclass, field

# A (kind, pattern) pair
NamedPattern = tuple[str, re.Pattern[str]]


@dataclass(frozen=True)
class Comment:
    line: tuple[str, ...] = ()
    block: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Language:
    name: str

    #  .go, .py
    extensions: tuple[str, ...]

    # func, def, method, arrow function
    functions: tuple[NamedPattern, ...] = ()

    # class, struct, interface, type alias
    types: tuple[NamedPattern, ...] = ()

    # var, const, let, :=. a new local
    declarations: tuple[NamedPattern, ...] = ()

    # ?
    error_handling: tuple[re.Pattern[str], ...] = ()

    concurrency: re.Pattern[str] | None = None
    pointers: re.Pattern[str] | None = None
    panics: re.Pattern[str] | None = None
    loops: re.Pattern[str] | None = None
    conditionals: re.Pattern[str] | None = None
    switches: re.Pattern[str] | None = None

    comments: Comment = field(default_factory=Comment)

    manifests: tuple[str, ...] = ()


BEHAVIOR_FIELDS: tuple[str, ...] = (
    "concurrency",
    "pointers",
    "panics",
    "loops",
    "conditionals",
    "switches",
)


NAMED_FIELDS: tuple[str, ...] = ("functions", "types", "declarations")


DEFINITION_FIELDS: tuple[str, ...] = ("functions", "types")
