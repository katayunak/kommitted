"""Go.

Note on regex vs the real grammar: these run against *diff lines*, which are
fragments - half a function, no imports, unbalanced braces. A real Go parser
refuses to parse that. So every pattern below is anchored where it can be
(`^\\s*` for statement keywords) and deliberately loose where it can't. Where
a pattern is known to over-match, the comment says so rather than pretending.
"""

import re

from .base import Comment, Language

GO = Language(
    name="go",
    extensions=(".go",),
    functions=(
        # `func Name(...)` and `func (r *Recv) Name(...)` - the optional
        # receiver group must not be captured, hence (?:...).
        ("func", re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?(\w+)")),
    ),
    types=(
        ("type", re.compile(r"^\s*type\s+(\w+)\s+(?:struct|interface)")),
        # `type UserID string` - a named alias is still a new concept.
        ("type", re.compile(r"^\s*type\s+(\w+)\s+(?!struct|interface)\w")),
    ),
    declarations=(
        # `var x int`, `var x = f()`. Requires a name directly after `var`,
        # which is exactly what excludes the `var (` group form below.
        ("var", re.compile(r"^\s*var\s+(\w+)")),
        ("const", re.compile(r"^\s*const\s+(\w+)")),
        # Exported package-level binding, `MaxRetries = 3`, including the
        # bare form inside a const block.
        ("const", re.compile(r"^\s*([A-Z][A-Za-z0-9_]*)\s*=(?!=)")),
        # `x := f()` and `x, err := f()` - captures the first name only.
        # This is the dominant binding form in real Go code, so it will fire
        # a lot; treat its count as texture, not as a strong signal.
        ("short", re.compile(r"^\s*(\w+)(?:\s*,\s*\w+)*\s*:=")),
        # TODO(grouped-decls): `var (` / `const (` blocks put the names on
        # following lines, indented, with no keyword:
        #     var (
        #         timeout = 5 * time.Second
        #     )
        # Matching bare `name = value` outside a block would swallow every
        # struct-literal field and assignment in the file, so we skip these
        # entirely for now. Catching them needs the parser to track "am I
        # inside a decl block", which is real state diffcontent.py does not
        # have yet. Same fix would also handle multi-line `import (`.
    ),
    error_handling=(
        re.compile(r"if\s+err\s*!=\s*nil"),
        re.compile(r"errors\.(?:Is|As|New)\b"),
        re.compile(r"==\s*nil\b"),
        re.compile(r"\bpanic\("),
    ),
    # `go f()`, channels, the sync package, and select. `select` lives here
    # rather than in `switches` on purpose: syntactically it resembles a
    # switch, but a select statement is *always* about channels, so counting
    # it as concurrency is what actually carries meaning.
    concurrency=re.compile(
        r"\bgo\s+\w"
        r"|\bchan\b"
        r"|<-"
        r"|\bselect\s*\{"
        r"|\bsync\.(?:WaitGroup|Mutex|RWMutex|Once|Map|Pool)\b"
        r"|\bsync/atomic\b|\batomic\.(?:Add|Load|Store|Swap|Compare)"
        r"|\bcontext\.(?:Context|WithCancel|WithTimeout|WithDeadline)\b"
        r"|\berrgroup\."
    ),
    # Over-matches by construction: `*` is also multiplication and `&` is
    # also bitwise-and. Each alternative is shaped to prefer the pointer
    # reading (a `*` glued to an identifier in a type position, `&` before a
    # composite literal) but this count is noisy and should never be the
    # deciding signal on its own.
    pointers=re.compile(
        r"\*\s*\w+\s*\)"  # func (r *Recv) / param `x *T)`
        r"|\(\s*\w+\s+\*\w+"  # `(cfg *Config`
        r"|\s\*\w+\s*[,)]"  # `, x *T,`
        r"|&\w+\{"  # &Struct{...}
        r"|&\w+\b(?!\s*&)"  # &x, but not the && operator
        r"|\bnew\("
        r"|\bunsafe\.Pointer\b"
    ),
    panics=re.compile(
        r"\bpanic\(" r"|\brecover\(\)" r"|\blog\.(?:Fatal|Fatalf|Fatalln|Panic)" r"|\bos\.Exit\("
    ),
    # Go has exactly one loop keyword. `for cond {}` IS the while loop and
    # `for {}` is the infinite loop, so there is deliberately no `while`
    # pattern here - inventing one would only ever match zero lines.
    loops=re.compile(r"^\s*for\b|\brange\b"),
    conditionals=re.compile(r"^\s*if\b|^\s*\}?\s*else\b"),
    switches=re.compile(r"^\s*switch\b|^\s*case\b|^\s*default\s*:|^\s*fallthrough\b"),
    comments=Comment(line=("//",), block=(("/*", "*/"),)),
    manifests=("go.mod", "go.sum"),
)
