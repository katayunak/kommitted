from dataclasses import dataclass, field

from diffparser import NumStat

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


@dataclass
class Classification:
    type: str
    confidence: float  # 0.0 - 1.0: how much to trust this answer
    reasons: list[str] = field(default_factory=list)  # Reasons: make([]string, 0)


def is_test(path: str) -> bool:
    p = path.lower()
    return any(marker in p for marker in TEST_MARKERS)


def is_doc(path: str) -> bool:
    p = path.lower()
    return p.endswith(DOC_EXTENSIONS) or any(d in p for d in DOC_DIRS)


def is_config(path: str) -> bool:
    p = path.lower()
    name = p.rsplit("/", 1)[-1]
    return name in CONFIG_NAMES or any(d in p for d in CONFIG_DIRS)


def classify(stats: list[NumStat]) -> Classification:
    if not stats:
        return Classification("chore", 0.0, ["nothing staged"])

    paths = [st.path for st in stats]

    # Binary files report None. Treating unknown as 0 keeps the arithmetic
    # simple, but note that we silently lose information here.
    added = sum(st.added_lines or 0 for st in stats)
    deleted = sum(st.deleted_lines or 0 for st in stats)

    # --- Rules by path: the reliable ones ---------------------------------
    # Order matters. A change touching only tests is a test commit even if it
    # adds 200 lines.

    if all(is_test(p) for p in paths):
        return Classification(
            "test", 0.9, [f"all {len(paths)} file(s) look like tests"]
        )

    if all(is_doc(p) for p in paths):
        return Classification("docs", 0.9, ["only documentation files changed"])

    if all(is_config(p) for p in paths):
        return Classification("chore", 0.85, ["only config/build files changed"])

    # --- Rules by shape: these are guesses --------------------------------
    # Nothing below can actually separate a feature from a bug fix, because
    # line counts carry no meaning. The low confidence values say so.

    if deleted == 0 and added > 0:
        return Classification(
            "feat",
            0.6,
            [f"purely additive (+{added} -0)", "new code usually means a feature"],
        )

    if added == 0 and deleted > 0:
        return Classification(
            "chore",
            0.5,
            [f"purely deletions (-{deleted})", "could be cleanup or a revert"],
        )

    total = added + deleted
    if abs(added - deleted) / total < 0.25:
        return Classification(
            "refactor",
            0.45,
            [f"balanced edit (+{added} -{deleted})", "similar amounts in and out"],
        )

    if added > deleted:
        return Classification("feat", 0.4, [f"mostly additions (+{added} -{deleted})"])

    return Classification(
        "fix",
        0.3,
        [
            f"mostly deletions (+{added} -{deleted})",
            "cannot tell fix from refactor without reading the diff",
        ],
    )
