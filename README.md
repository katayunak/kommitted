# kommitted

[![CI](https://github.com/katayunak/kommitted/actions/workflows/ci.yml/badge.svg)](https://github.com/katayunak/kommitted/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

Write [Conventional Commits](https://www.conventionalcommits.org/) messages from your staged git changes — and tell you *why* it chose what it chose.

```console
$ git add .
$ kommitted --why
brain: rules  type: fix (confidence 0.60)
  - branch 'fix/retry-boundary' starts with 'fix'
  - 1 line(s) changed an operator

fix(internal): fix worker

- internal/worker.go (+1 -1)
```

Zero runtime dependencies. Python standard library only.

---

## Why this exists

Most commit-message tools do one of two things: paste your diff into an LLM and hope, or count added and deleted lines and guess.

Counting lines can't work. These two diffs are both `+1 -1`:

```diff
- if retries < max {          - func parseNumstat(raw string) {
+ if retries <= max {         + func parseNumStat(raw string) {
```

The first is a bug fix. The second is a rename. Every line-counting tool calls them the same thing.

kommitted pairs each removed line with the line that replaced it, breaks both into tokens, and looks at **which kind of token changed**. An operator moved? That's a fix. Only a name moved? That's a refactor.

And when it isn't sure, it says so instead of inventing a confident answer.

---

## Install

```bash
git clone https://github.com/katayunak/kommitted.git
cd kommitted
pip install -e .
```

`-e` installs in editable mode: your edits take effect immediately, no reinstall. Requires Python 3.10+.

Check it worked:

```bash
kommitted --help
```

---

## Usage

Stage your changes first — kommitted only reads the staging area, never your working tree.

```bash
git add .
kommitted
```

### Options

| Flag | Short | What it does |
|---|---|---|
| `--why` | `-y` | Print the reasoning to stderr |
| `--commit` | `-c` | Actually create the commit |
| `--brain NAME` | `-b` | Which strategy decides the type: `rules`, `llm`, `auto` |
| `--save` | | Remember `--brain` for this repo |
| `--global` | | With `--save`, remember it everywhere |

### Common workflows

**Look before you leap** — print the message, decide for yourself:

```bash
kommitted
```

**Understand the decision** — reasoning goes to stderr, so it never pollutes a pipe:

```bash
kommitted --why
kommitted --why | git commit -F -    # you still see the reasoning
```

**Commit directly:**

```bash
kommitted --commit
```

**Pick a brain and remember it:**

```bash
kommitted -b llm --save            # this repo only
kommitted -b llm --save --global   # every repo
```

Settings live in git's own config, so there's no extra file to manage:

```bash
git config --get kommitted.brain
git config --unset kommitted.brain
```

---

## Brains

A *brain* is a strategy for deciding the commit type. Pick with `-b`.

### `rules` (default)

Free, offline, instant, and fully explainable. Every answer carries the rules that produced it.

It reads seven kinds of evidence and each one **votes**:

| Evidence | Example | Strength |
|---|---|---|
| File paths | everything is under `tests/` | strong |
| Branch name | `fix/login-crash` | medium |
| New definitions | a new `func` appeared | strong |
| Edit kinds | an operator changed | strong |
| Behaviour counts | did a conditional appear? | weak |
| Comments | only prose changed | medium |
| Line counts | `+40 -2` | weak |

Nothing returns early. A commit with three weak hints for `fix` and one medium hint for `refactor` comes out `fix` — and the confidence shows how close it was.

### `llm`

Sends a truncated diff to Google Gemini. Needs an API key:

```bash
export GEMINI_API_KEY=your-key-here
kommitted -b llm
```

Get a key at [aistudio.google.com](https://aistudio.google.com/apikey).

**`-b llm` is strict.** If the key is missing or the model is unreachable, kommitted prints the reason and exits nonzero. It does not quietly answer with the rule brain, because that would print something that looks fine and isn't what you asked for — and a script piping into `git commit` would never notice.

### `auto`

The same model, but it degrades instead of failing:

```bash
kommitted -b auto
```

Tries Gemini, uses `rules` when it can't, and says so in the first reason. **Fallback is a property of `auto`, never of failure.** Once any mode is allowed to degrade quietly, the flags stop meaning anything.

---

## Understanding confidence

Confidence is **not** "how likely this is correct." It's *how good the evidence was*, and it's built from two parts:

```
agreement = winner's points / all points awarded
strength  = min(1.0, winner's points / 30)
confidence = agreement × strength
```

**Agreement** asks whether anything disagreed. **Strength** asks whether there was much evidence at all — without it, a single weak hint with nothing to contradict it would score 100%.

| Situation | Confidence |
|---|---|
| Several rules agree | 0.8 – 1.0 |
| One solid rule, nothing against it | 0.4 – 0.6 |
| One weak guess | 0.1 – 0.3 |
| Rules split evenly | below 0.4 |
| Nothing matched | 0.0 |

**Low confidence is information, not failure.** Use `--why` and write it yourself.

---

## Supported languages

| Language | Extensions |
|---|---|
| Go | `.go` |
| Python | `.py` `.pyi` |
| JavaScript / TypeScript | `.js` `.jsx` `.ts` `.tsx` `.mjs` |

Files in other languages still count toward paths and line totals — kommitted just won't read inside them. It stays quiet rather than guessing with the wrong language's rules.

### Adding a language

One file in `src/kommitted/languages/`, one entry in `LANGUAGES`. Nothing else changes.

```python
# src/kommitted/languages/rust.py
import re
from .base import Comment, Language

RUST = Language(
    name="rust",
    extensions=(".rs",),
    functions=(("func", re.compile(r"^\s*(?:pub\s+)?fn\s+(\w+)")),),
    types=(("type", re.compile(r"^\s*(?:pub\s+)?(?:struct|enum|trait)\s+(\w+)")),),
    declarations=(("let", re.compile(r"^\s*let\s+(?:mut\s+)?(\w+)")),),
    conditionals=re.compile(r"^\s*if\b|^\s*\}?\s*else\b"),
    loops=re.compile(r"^\s*for\b|^\s*while\b|^\s*loop\b"),
    panics=re.compile(r"\bpanic!\(|\bunwrap\(\)|\bexpect\("),
    comments=Comment(line=("//",), block=(("/*", "*/"),)),
    manifests=("Cargo.toml", "Cargo.lock"),
)
```

Any field you leave out simply never matches. `None` means "this language has no such thing" — Go has no `while`, Python has no pointers — which is more honest than inventing a pattern that can never fire.

---

## How it works

```
git ──▶ gitrunner ──▶ diffparser ──▶ diffcontent ──▶ Context ──▶ scorers ──▶ builder
        raw text      file stats     paired lines    evidence    votes       message
```

Each stage knows nothing about the stages after it. That's why swapping `rules` for `llm` changes one line.

The interesting stage is `diffcontent`. A unified diff prints all the removed lines, then all the added ones. kommitted pairs them up — the first `-` line with the first `+` line — so a modified line becomes one `Change` with a `before` and an `after`. Then it tokenizes both sides and compares.

```python
classify_edit("if retries < max {", "if retries <= max {")
# {EditType.OPERATOR}          -> fix

classify_edit("func parseNumstat(", "func parseNumStat(")
# {EditType.RENAMED}           -> refactor

classify_edit("if a < maxTries {", "if b <= maxTries {")
# {RENAMED, OPERATOR}          -> both are true, both get counted
```

Whitespace is dropped before comparing, so `gofmt` churn reads as *unchanged* and can't fake an edit.

---

## Known limits

Honest list, not a roadmap:

- **Cross-file moves read as delete + add.** A function moved from `a.go` to `b.go` is the commonest refactor there is, and pairing is per-file.
- **Block comments spanning lines aren't tracked.** `is_comment` judges one line at a time, so the middle of a `/* ... */` block reads as code.
- **Grouped Go declarations are skipped.** Names inside `var (...)` blocks sit on unkeyworded lines; matching them would swallow every struct literal in the file.
- **File status is unused.** `--numstat` can't tell a new file from an appended one — both print `40 0 file`.
- **Every score is an unvalidated guess.** The numbers in `constants.py` were chosen by feel and have never been fitted against real commits.

---

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

Tests are organised by what they protect:

| File | Covers |
|---|---|
| `test_tokens.py` | Reading one changed line |
| `test_change.py` | Pairing, and fix vs refactor |
| `test_diffcontent.py` | Per-language pattern matching |
| `test_rules.py` | Scoring and confidence |
| `test_builder.py` | Message formatting |
| `test_cli.py` | End to end, against real repos |

---

## License

MIT — see [LICENSE](LICENSE).
