# --- Commit types ----------------------------------------------------------

TYPE_FEAT = "feat"
TYPE_FIX = "fix"
TYPE_DOCS = "docs"
TYPE_TEST = "test"
TYPE_CHORE = "chore"
TYPE_REFACTOR = "refactor"

VERBS = {
    TYPE_FEAT: "add",
    TYPE_FIX: "fix",
    TYPE_DOCS: "update",
    TYPE_TEST: "add tests for",
    TYPE_CHORE: "update",
    TYPE_REFACTOR: "refactor",
}
DEFAULT_VERB = "update"

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

# --- Thresholds (all guesses - see module docstring) -----------------------

# Git convention: subject lines fit in 50 chars so `git log --oneline` and
# GitHub don't truncate them. This one is NOT a guess.
MAX_SUBJECT_LEN = 50

# How much of a change must live under one directory before we name it as
# the scope. UNVALIDATED GUESS - needs an eval over real repos.
SCOPE_DOMINANCE = 0.7

# An edit is "balanced" (lines in ≈ lines out) below this ratio, which
# suggests code moved rather than grew. UNVALIDATED GUESS.
BALANCED_EDIT_RATIO = 0.25

# --- Confidence levels -----------------------------------------------------
# Path-based rules are reliable. Shape-based rules are guesses, and these
# numbers say so out loud.

CONFIDENCE_PATH_STRONG = 0.9
CONFIDENCE_PATH_WEAK = 0.85
CONFIDENCE_SHAPE_ADDITIVE = 0.6
CONFIDENCE_SHAPE_DELETIONS = 0.5
CONFIDENCE_SHAPE_BALANCED = 0.45
CONFIDENCE_SHAPE_MOSTLY_ADD = 0.4
CONFIDENCE_SHAPE_FALLBACK = 0.3
CONFIDENCE_NONE = 0.0

# --- Reasons ---------------------------------------------------------------
# Templates use .format().

REASON_NOTHING_STAGED = "nothing staged"
REASON_ALL_TESTS = "all {count} file(s) look like tests"
REASON_ONLY_DOCS = "only documentation files changed"
REASON_ONLY_CONFIG = "only config/build files changed"
REASON_PURELY_ADDITIVE = "purely additive (+{added} -0)"
REASON_NEW_CODE_IS_FEATURE = "new code usually means a feature"
REASON_PURELY_DELETIONS = "purely deletions (-{deleted})"
REASON_COULD_BE_CLEANUP = "could be cleanup or a revert"
REASON_BALANCED_EDIT = "balanced edit (+{added} -{deleted})"
REASON_SIMILAR_IN_OUT = "similar amounts in and out"
REASON_MOSTLY_ADDITIONS = "mostly additions (+{added} -{deleted})"
REASON_MOSTLY_DELETIONS = "mostly deletions (+{added} -{deleted})"
REASON_NEEDS_DIFF_CONTENT = "cannot tell fix from refactor without reading the diff"

# --- Messages --------------------------------------------------------------

MSG_NOTHING_STAGED = "no staged changes - run `git add` first"
MSG_COMMITTED = "committed:"

# --- Exit codes ------------------------------------------------------------
# 2 is reserved: argparse uses it for usage errors.

EXIT_OK = 0
EXIT_ERROR = 1
