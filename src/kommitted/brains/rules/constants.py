"""Constants for the rule brain: what counts as evidence, and for how much."""

# --- Path detection --------------------------------------------------------

TEST_MARKERS = ("test_", "_test.", "/tests/", "/test/", ".spec.", ".test.")
DOC_EXTENSIONS = (".md", ".rst", ".txt", ".adoc")
DOC_DIRS = ("/docs/", "docs/")
CONFIG_NAMES = (
    ".gitignore",
    ".dockerignore",
    "dockerfile",
    "makefile",
    "go.mod",
    "go.sum",
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
)
CONFIG_DIRS = (".github/", ".vscode/", ".idea/")

# --- Branch names ----------------------------------------------------------
# `fix/login-crash` says what the author thought they were doing. Cheap and
# usually honest, but people forget to branch, so it is evidence not proof.

BRANCH_PREFIXES = {
    "feat": "feat",
    "feature": "feat",
    "fix": "fix",
    "hotfix": "fix",
    "bug": "fix",
    "bugfix": "fix",
    "refactor": "refactor",
    "cleanup": "refactor",
    "docs": "docs",
    "doc": "docs",
    "test": "test",
    "tests": "test",
    "chore": "chore",
    "ci": "chore",
    "build": "chore",
}

# --- Thresholds ------------------------------------------------------------

# An edit is "balanced" (lines in ~ lines out) below this ratio, which
# suggests code moved rather than grew. UNVALIDATED GUESS.
BALANCED_EDIT_RATIO = 0.25

# A change small enough that an added guard is the story, not a side
# effect of writing new code. UNVALIDATED GUESS.
SMALL_CHANGE_LINES = 50

# Above this many changed lines a commit is "large", which makes a pure
# rename much less likely to be the whole story. UNVALIDATED GUESS.
LARGE_CHANGE_LINES = 200

# --- Reasons ---------------------------------------------------------------
# Templates use .format().

REASON_NOTHING_STAGED = "nothing staged"
REASON_ALL_TESTS = "all {count} file(s) look like tests"
REASON_ONLY_DOCS = "only documentation files changed"
REASON_ONLY_CONFIG = "only config/build files changed"
REASON_BRANCH = "branch {branch!r} starts with {prefix!r}"
REASON_PURELY_ADDITIVE = "purely additive (+{added} -0)"
REASON_PURELY_DELETIONS = "purely deletions (-{deleted})"
REASON_BALANCED_EDIT = "balanced edit (+{added} -{deleted})"
REASON_MOSTLY_ADDITIONS = "mostly additions (+{added} -{deleted})"
REASON_MOSTLY_DELETIONS = "mostly deletions (+{added} -{deleted})"
REASON_NEW_DEFINITIONS = "new {kind}(s) defined: {names}"
REASON_MOVED_DEFINITIONS = "same name(s) removed and re-added: {names}"
REASON_FILES_MOVED = "{count} file(s) moved between directories: {examples}"
REASON_FILES_RENAMED = "{count} file(s) renamed in place"
REASON_OPERATOR_EDIT = "{count} line(s) changed an operator"
REASON_LITERAL_EDIT = "{count} line(s) changed a literal value"
REASON_RENAME_EDIT = "{count} line(s) changed only a name"
REASON_BEHAVIOR_ADDED = "control flow appeared: {kinds}"
REASON_BEHAVIOR_PRESERVED = "no behaviour construct changed count"
REASON_COMMENTS_ONLY = "only comment lines changed"
