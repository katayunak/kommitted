"""JavaScript and TypeScript.

One Language covers both. They differ in the type system, and none of the
patterns below read types except `interface`/`type`, which simply never
match in a .js file. Splitting them would duplicate every other pattern to
buy nothing.
"""

import re

from .base import Comment, Language

JAVASCRIPT = Language(
    name="javascript",
    extensions=(".js", ".jsx", ".ts", ".tsx", ".mjs"),
    functions=(
        ("func", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)")),
        # const foo = (...) => ... - the dominant modern function form.
        ("func", re.compile(r"^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(")),
    ),
    types=(
        ("class", re.compile(r"^\s*(?:export\s+)?class\s+(\w+)")),
        ("type", re.compile(r"^\s*(?:export\s+)?(?:interface|type)\s+(\w+)")),
    ),
    declarations=(
        # Deliberately overlaps `functions` above: `const f = () => {}` counts
        # as both a func and a const declaration. That is correct - they
        # answer different questions, and the counters are separate.
        ("const", re.compile(r"^\s*(?:export\s+)?const\s+(\w+)")),
        ("let", re.compile(r"^\s*(?:export\s+)?let\s+(\w+)")),
        ("var", re.compile(r"^\s*(?:export\s+)?var\s+(\w+)")),
    ),
    error_handling=(
        re.compile(r"^\s*catch\b"),
        re.compile(r"^\s*try\s*\{"),
        re.compile(r"\bthrow\b"),
        re.compile(r"!==?\s*(?:null|undefined)\b"),
    ),
    concurrency=re.compile(
        r"\basync\b"
        r"|\bawait\b"
        r"|\bPromise\.(?:all|allSettled|race|any)\b|\bnew Promise\b"
        r"|\.then\(|\.catch\(|\.finally\("
        r"|\bnew Worker\(|\bpostMessage\(|\bqueueMicrotask\("
        r"|\bfunction\s*\*|\byield\b"
    ),
    # JavaScript has no pointers and no explicit references - object
    # identity is implicit. These are the places where sharing versus
    # copying is made explicit, which is the closest analogue worth a count.
    pointers=re.compile(
        r"\bWeakRef\b|\bWeakMap\b|\bWeakSet\b"
        r"|\bstructuredClone\(|\bObject\.assign\(|\bObject\.freeze\("
        r"|\.\.\.\w+"  # spread: a shallow copy, i.e. a decision about sharing
    ),
    panics=re.compile(r"\bthrow\b|\bprocess\.exit\(|\bnew Error\(|\bassert\b"),
    loops=re.compile(r"^\s*for\b|^\s*while\b|^\s*do\b|\.forEach\(|\bfor\s+await\b"),
    conditionals=re.compile(
        r"^\s*if\b"
        r"|^\s*\}?\s*else\b"
        r"|\?\?"  # nullish coalescing
        r"|\?\.[\w\[]"  # optional chaining
        r"|\w\s*\?\s*[^:]+\s*:"  # ternary
    ),
    switches=re.compile(r"^\s*switch\b|^\s*case\b|^\s*default\s*:"),
    # JSX wraps comments as {/* ... */}; the inner /* */ pair already
    # matches, so no separate entry is needed.
    comments=Comment(line=("//",), block=(("/*", "*/"),)),
    manifests=("package.json", "package-lock.json", "yarn.lock"),
)
