"""Integration tests for gitrunner - they create real throwaway repos."""

import subprocess

import pytest

from kommitted.gitrunner import (
    GitError,
    commit,
    current_branch,
    staged_diff,
    staged_numstat,
)

from .conftest import stage

# ---------------------------------------------------------------------------
# The distinction that matters: failure vs. empty
# ---------------------------------------------------------------------------


def test_not_a_repo_raises(empty_dir):
    # The whole point of GitError: this must NOT quietly return "".
    with pytest.raises(GitError):
        staged_numstat()


def test_not_a_repo_error_mentions_the_command(empty_dir):
    with pytest.raises(GitError) as excinfo:
        staged_numstat()
    assert "diff --staged --numstat" in str(excinfo.value)


def test_nothing_staged_returns_empty_string(repo):
    # Not an error - git succeeded and correctly reported nothing.
    assert staged_numstat() == ""
    assert staged_diff() == ""


# ---------------------------------------------------------------------------
# staged_numstat
# ---------------------------------------------------------------------------


def test_numstat_format(repo):
    stage(repo, "a.txt", "one\ntwo\n")
    assert staged_numstat() == "2\t0\ta.txt\n"


def test_numstat_multiple_files(repo):
    stage(repo, "a.txt", "aaa\n")
    stage(repo, "b.txt", "bbb\n")
    lines = staged_numstat().strip().split("\n")
    assert {ln.split("\t")[2] for ln in lines} == {"a.txt", "b.txt"}


def test_numstat_ignores_unstaged_work(repo):
    (repo / "untracked.txt").write_text("not staged\n")
    assert staged_numstat() == ""


def test_numstat_reports_staged_version_not_working_copy(repo):
    # Stage one version, then edit again. --staged must report the snapshot
    # in the index, not what's on disk now.
    stage(repo, "a.txt", "staged\n")
    (repo / "a.txt").write_text("edited after staging\n")
    assert staged_numstat() == "1\t0\ta.txt\n"


# ---------------------------------------------------------------------------
# staged_diff
# ---------------------------------------------------------------------------


def test_diff_contains_content(repo):
    stage(repo, "a.txt", "hello\n")
    diff = staged_diff()
    # Assert on stable parts. Blob hashes change every run, so comparing the
    # whole diff would fail for no reason.
    assert "a.txt" in diff
    assert "new file" in diff
    assert "+hello" in diff


def test_diff_and_numstat_agree_on_file_count(repo):
    stage(repo, "a.txt", "aaa\n")
    stage(repo, "b.txt", "bbb\n")
    assert staged_diff().count("diff --git") == 2
    assert len(staged_numstat().strip().split("\n")) == 2


# ---------------------------------------------------------------------------
# current_branch
# ---------------------------------------------------------------------------


def test_current_branch_works_before_any_commit(repo):
    # Regression test: `rev-parse --abbrev-ref HEAD` raises here because HEAD
    # points at a branch with no commits yet.
    branch = current_branch()
    assert branch in {"main", "master"}  # depends on init.defaultBranch
    assert "\n" not in branch


def test_current_branch_after_a_commit(repo):
    stage(repo, "a.txt", "hello\n")
    commit("init")
    assert current_branch() in {"main", "master"}


def test_current_branch_is_empty_when_detached(repo):
    stage(repo, "a.txt", "hello\n")
    commit("init")
    subprocess.run(["git", "checkout", "-q", "--detach", "HEAD"], check=True)
    # Detached HEAD is a real state, not a failure.
    assert current_branch() == ""


def test_current_branch_outside_repo_raises(empty_dir):
    with pytest.raises(GitError):
        current_branch()


# ---------------------------------------------------------------------------
# commit
# ---------------------------------------------------------------------------


def test_commit_creates_a_commit(repo):
    stage(repo, "a.txt", "hello\n")
    commit("feat: add a.txt")

    log = subprocess.run(
        ["git", "log", "--oneline"], capture_output=True, text=True, check=True
    )
    assert "feat: add a.txt" in log.stdout


def test_commit_clears_the_staging_area(repo):
    stage(repo, "a.txt", "hello\n")
    commit("feat: add a.txt")
    assert staged_numstat() == ""


def test_commit_with_nothing_staged_raises(repo):
    with pytest.raises(GitError):
        commit("nothing to see")


def test_commit_message_with_spaces_and_quotes_survives(repo):
    # Passing a token list (never shell=True) means no shell re-parses this.
    stage(repo, "a.txt", "hello\n")
    tricky = 'fix(git): handle "weird" paths; rm -rf /'
    commit(tricky)

    log = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"], capture_output=True, text=True, check=True
    )
    assert log.stdout.strip() == tricky
