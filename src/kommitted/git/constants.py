"""Constants for reading git and for writing the message."""

# --- Message shape ---------------------------------------------------------

# Git convention: subject lines fit in 50 chars so `git log --oneline` and
# GitHub don't truncate them. This one is NOT a guess.
MAX_SUBJECT_LEN = 50

# How much of a change must live under one directory before we name it as
# the scope. UNVALIDATED GUESS - needs an eval over real repos.
SCOPE_DOMINANCE = 0.7

# The verb that opens the subject line, per commit type. Keys are the
# CommitType values, and CommitType is a str Enum, so a plain string looks
# them up too.
VERBS = {
    "feat": "add",
    "fix": "fix",
    "docs": "update",
    "test": "add tests for",
    "chore": "update",
    "refactor": "refactor",
}
DEFAULT_VERB = "update"

# Comment churn is worth a body line whether or not code changed with it: a
# reader skimming `git log` wants to know the prose moved. The numbers are
# how many comment LINES appeared and disappeared.
BODY_COMMENTS = "- comments (+{added} -{removed})"

# A body listing 48 files is not a summary, it is the output of `git
# diff --stat` with extra steps. Nobody reads past the first screen.
MAX_BODY_FILES = 10
BODY_MORE_FILES = "- ...and {count} more file(s)"

# --- Settings, stored in git's own config ----------------------------------
# `git config kommitted.brain llm` instead of a config file we have to find,
# parse and version. Git already solved per-repo vs global.

SETTING_PREFIX = "kommitted"
SETTING_BRAIN = f"{SETTING_PREFIX}.brain"
SETTING_LANGUAGE = f"{SETTING_PREFIX}.language"

# --- Messages --------------------------------------------------------------

MSG_NOTHING_STAGED = "no staged changes - run `git add` first"
MSG_COMMITTED = "committed : "
MSG_SETTING_SAVED = "saved {key} = {value}"
