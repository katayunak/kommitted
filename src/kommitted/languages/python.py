"""Python."""

import re

from .base import Comment, Language

PYTHON = Language(
    name="python",
    extensions=(".py", ".pyi"),
    functions=(("func", re.compile(r"^\s*(?:async\s+)?def\s+(\w+)")),),
    types=(
        ("class", re.compile(r"^\s*class\s+(\w+)")),
        # `UserId = NewType(...)` and `Handler: TypeAlias = ...`
        ("type", re.compile(r"^\s*(\w+)\s*(?::\s*TypeAlias\s*)?=\s*NewType\(")),
    ),
    declarations=(
        # Module-level SCREAMING_CASE. Listed first so the const reading wins
        # over the generic binding pattern below.
        ("const", re.compile(r"^([A-Z][A-Z0-9_]{2,})\s*[:=]")),
        # Annotated binding: `timeout: int = 5`. Requiring the annotation
        # makes this precise - it cannot match a plain reassignment.
        ("var", re.compile(r"^\s*(\w+)\s*:\s*[A-Za-z_\[\"']")),
        # Plain binding: `timeout = 5`. Python does not distinguish
        # declaration from assignment, so this fires on every reassignment
        # too. Kept because it is the only way to see a new module-level
        # name, but it is the noisiest pattern in this file by a wide margin.
        ("var", re.compile(r"^\s*(\w+)\s*=(?!=)")),
        ("global", re.compile(r"^\s*(?:global|nonlocal)\s+(\w+)")),
    ),
    error_handling=(
        re.compile(r"^\s*except\b"),
        re.compile(r"^\s*raise\b"),
        re.compile(r"^\s*try\s*:"),
        re.compile(r"\bis\s+(?:not\s+)?None\b"),
    ),
    concurrency=re.compile(
        r"\basync\s+(?:def|with|for)\b"
        r"|\bawait\b"
        r"|\basyncio\."
        r"|\bthreading\.|\bmultiprocessing\.|\bconcurrent\.futures\b"
        r"|\bThread\(|\bProcess\(|\bLock\(|\bQueue\(|\bSemaphore\("
        r"|\byield\s+from\b"
    ),
    # Python has no pointers. Nothing here is a pointer - these are the
    # constructs where *reference semantics* become the programmer's
    # explicit problem, which is the nearest thing worth counting. Writing
    # None would also have been defensible; this is a judgement call, and if
    # the count turns out to be useless noise, delete it.
    pointers=re.compile(
        r"\bweakref\.|\bWeakValueDictionary\b|\bWeakKeyDictionary\b"
        r"|\bcopy\.(?:copy|deepcopy)\b"
        r"|\bid\(\w+\)"
        r"|\bmemoryview\(|\bctypes\."
    ),
    panics=re.compile(
        r"^\s*raise\b" r"|^\s*assert\b" r"|\bsys\.exit\(" r"|\bSystemExit\b" r"|\bos\._exit\("
    ),
    loops=re.compile(r"^\s*(?:async\s+)?for\b|^\s*while\b"),
    # `elif` before `if` in the alternation would be pointless here since
    # both are anchored, but note `else` also catches `else:` on try/for.
    conditionals=re.compile(r"^\s*if\b|^\s*elif\b|^\s*else\b|\bif\b.+\belse\b"),
    # structural pattern matching, 3.10+. `match` and `case` are soft
    # keywords, so `match = re.match(...)` is a real false positive - the
    # trailing `:` requirement below rules most of those out.
    switches=re.compile(r"^\s*match\s+.+:\s*$|^\s*case\s+.+:\s*$"),
    # Python has no block comment. Triple quotes are string literals that
    # happen to be used as docstrings; they are counted here because in a
    # diff they play the same role - prose, not logic.
    comments=Comment(line=("#",), block=(('"""', '"""'), ("'''", "'''"))),
    manifests=("requirements.txt", "pyproject.toml", "setup.py", "poetry.lock"),
)
