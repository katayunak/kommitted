"""End-to-end tests for the CLI.

These run the real entry point as a subprocess inside real throwaway repos -
the same way a user runs it. Slower than the unit tests, but the only ones
that prove the whole pipeline is wired together.
"""

import subprocess
import sys

from .conftest import stage


def run_cli(*flags: str) -> subprocess.CompletedProcess:
    """Run the tool the way a user would, via `python -m committed`."""
    return subprocess.run(
        [sys.executable, "-m", "committed", *flags],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_prints_a_message(repo):
    stage(repo, "model/classifier.py", "x = 1\n")
    proc = run_cli()

    assert proc.returncode == 0
    assert proc.stdout.startswith("feat(model): add classifier")


def test_message_has_the_git_required_blank_line(repo):
    stage(repo, "model/a.py", "one\ntwo\n")
    assert run_cli().stdout.split("\n")[1] == ""


def test_body_lists_each_file(repo):
    stage(repo, "model/a.py", "a\n")
    stage(repo, "model/b.py", "b\n")
    out = run_cli().stdout
    assert "- model/a.py (+1 -0)" in out
    assert "- model/b.py (+1 -0)" in out


def test_docs_only_change_is_classified_as_docs(repo):
    stage(repo, "README.md", "# hello\n")
    assert run_cli().stdout.startswith("docs: ")


def test_tests_only_change_is_classified_as_test(repo):
    stage(repo, "model/test_thing.py", "def test_x(): pass\n")
    assert run_cli().stdout.startswith("test(model): ")


# ---------------------------------------------------------------------------
# Nothing staged - a normal state, not a failure
# ---------------------------------------------------------------------------


def test_nothing_staged_exits_zero(repo):
    proc = run_cli()
    assert proc.returncode == 0
    assert "no staged changes" in proc.stdout


# ---------------------------------------------------------------------------
# Failure
# ---------------------------------------------------------------------------


def test_outside_a_repo_exits_one(empty_dir):
    proc = run_cli()
    assert proc.returncode == 1
    assert proc.stdout == ""  # nothing on the data channel
    assert "error:" in proc.stderr


# ---------------------------------------------------------------------------
# --why
# ---------------------------------------------------------------------------


def test_why_writes_reasoning_to_stderr_only(repo):
    stage(repo, "model/a.py", "x\n")
    proc = run_cli("--why")

    assert "confidence" in proc.stderr
    assert "confidence" not in proc.stdout  # stdout stays pipeable


def test_why_names_the_brain(repo):
    stage(repo, "model/a.py", "x\n")
    assert "rules" in run_cli("--why").stderr


def test_without_why_stderr_is_clean(repo):
    stage(repo, "model/a.py", "x\n")
    assert run_cli().stderr == ""


# ---------------------------------------------------------------------------
# --brain
# ---------------------------------------------------------------------------


def test_brain_flag_accepts_rules(repo):
    stage(repo, "model/a.py", "x\n")
    assert run_cli("--brain", "rules").returncode == 0


def test_unknown_brain_is_rejected_by_argparse(repo):
    proc = run_cli("--brain", "nonsense")
    assert proc.returncode == 2  # argparse usage error


# ---------------------------------------------------------------------------
# --commit
# ---------------------------------------------------------------------------


def test_commit_creates_a_real_commit(repo):
    stage(repo, "model/a.py", "x\n")
    assert run_cli("--commit").returncode == 0

    log = subprocess.run(
        ["git", "log", "--pretty=%s"], capture_output=True, text=True, check=True
    )
    assert log.stdout.strip() == "feat(model): add a"


def test_commit_writes_the_body_too(repo):
    stage(repo, "model/a.py", "x\n")
    run_cli("--commit")

    log = subprocess.run(
        ["git", "log", "-1", "--pretty=%b"], capture_output=True, text=True, check=True
    )
    assert "- model/a.py (+1 -0)" in log.stdout


def test_commit_clears_the_staging_area(repo):
    stage(repo, "model/a.py", "x\n")
    run_cli("--commit")

    staged = subprocess.run(
        ["git", "diff", "--staged", "--numstat"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert staged.stdout == ""


def test_without_commit_flag_nothing_is_committed(repo):
    stage(repo, "model/a.py", "x\n")
    run_cli()

    log = subprocess.run(["git", "log", "--oneline"], capture_output=True, text=True)
    assert log.returncode != 0  # no commits exist yet


# ---------------------------------------------------------------------------
# argparse plumbing
# ---------------------------------------------------------------------------


def test_help_exits_zero():
    proc = run_cli("--help")
    assert proc.returncode == 0
    assert "Conventional Commits" in proc.stdout


def test_unknown_flag_exits_two():
    assert run_cli("--nonsense").returncode == 2
