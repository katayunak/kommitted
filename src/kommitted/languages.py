"""Per-language rules for reading a diff body.

Why this file exists: applying Go's `if err != nil` to a Python diff is
noise, and matching `func` inside a `.py` file is simply wrong. Selecting
patterns by file extension makes each match both *more accurate* and
*cheaper* - we try 3 patterns instead of 12.

Adding a language means adding one entry here. Nothing else changes.

Deliberately a plain Python dict, not a database. These rules are known at
write time, never change at runtime, and load in microseconds. If they ever
become user-editable, a TOML file in the repo is the next step - a network
service would add a daemon and a failure mode to solve a problem that
doesn't exist.
"""

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Language:
    """How to read one language's source lines."""

    name: str
    extensions: tuple[str, ...]
    # (kind, pattern) - each pattern must capture the identifier in group 1.
    symbols: tuple[tuple[str, re.Pattern[str]], ...] = ()
    # Constructs whose appearance suggests a bug was being handled.
    error_handling: tuple[re.Pattern[str], ...] = ()
    # Files that mean "dependencies changed" in this ecosystem.
    manifests: tuple[str, ...] = field(default=())


PYTHON = Language(
    name="python",
    extensions=(".py", ".pyi"),
    symbols=(
        ("func", re.compile(r"^\s*(?:async\s+)?def\s+(\w+)")),
        ("class", re.compile(r"^\s*class\s+(\w+)")),
        ("const", re.compile(r"^([A-Z][A-Z0-9_]{2,})\s*[:=]")),
    ),
    error_handling=(
        re.compile(r"^\s*except\b"),
        re.compile(r"^\s*raise\b"),
        re.compile(r"^\s*try\s*:"),
        re.compile(r"\bis\s+(?:not\s+)?None\b"),
    ),
    manifests=("requirements.txt", "pyproject.toml", "setup.py", "poetry.lock"),
)

GO = Language(
    name="go",
    extensions=(".go",),
    symbols=(
        # `func Name(...)` and `func (r *Recv) Name(...)` - the optional
        # receiver group must not be captured, hence (?:...).
        ("func", re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?(\w+)")),
        ("type", re.compile(r"^\s*type\s+(\w+)\s+(?:struct|interface)")),
        ("const", re.compile(r"^\s*(?:const\s+)?([A-Z][A-Za-z0-9_]*)\s*=")),
    ),
    error_handling=(
        re.compile(r"if\s+err\s*!=\s*nil"),
        re.compile(r"errors\.(?:Is|As|New)\b"),
        re.compile(r"==\s*nil\b"),
        re.compile(r"\bpanic\("),
    ),
    manifests=("go.mod", "go.sum"),
)

JAVASCRIPT = Language(
    name="javascript",
    extensions=(".js", ".jsx", ".ts", ".tsx", ".mjs"),
    symbols=(
        ("func", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)")),
        ("class", re.compile(r"^\s*(?:export\s+)?class\s+(\w+)")),
        # const foo = (...) => ... — the dominant modern function form.
        ("func", re.compile(r"^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(")),
        ("type", re.compile(r"^\s*(?:export\s+)?(?:interface|type)\s+(\w+)")),
    ),
    error_handling=(
        re.compile(r"^\s*catch\b"),
        re.compile(r"^\s*try\s*\{"),
        re.compile(r"\bthrow\b"),
        re.compile(r"!==?\s*(?:null|undefined)\b"),
    ),
    manifests=("package.json", "package-lock.json", "yarn.lock"),
)

LANGUAGES: tuple[Language, ...] = (PYTHON, GO, JAVASCRIPT)

# extension -> Language, built once at import.
_BY_EXTENSION: dict[str, Language] = {
    ext: lang for lang in LANGUAGES for ext in lang.extensions
}

# Fallback for files we don't have rules for. Empty pattern sets mean we
# find nothing rather than guessing wrong - silence beats noise.
UNKNOWN = Language(name="unknown", extensions=())


def for_path(path: str) -> Language:
    """Pick the rules for a file, by extension. Never raises."""
    dot = path.rfind(".")
    if dot == -1:
        return UNKNOWN
    return _BY_EXTENSION.get(path[dot:].lower(), UNKNOWN)


def is_manifest(path: str) -> bool:
    """True for dependency files like go.mod or package.json."""
    name = path.rsplit("/", 1)[-1].lower()
    return any(name in lang.manifests for lang in LANGUAGES)
