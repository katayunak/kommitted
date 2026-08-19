"""Shared fixtures and helpers.

pytest auto-discovers this file - no import needed in the test modules.
Anything defined here is available to every test in this directory.
"""

import subprocess

import pytest

from kommitted.git.models import NumStat


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """An empty git repo that is already the current working directory.

    tmp_path and monkeypatch both undo themselves after each test, so no test
    can leak state into another or touch your real repo.
    """
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], check=True)
    # Identity must be set or `git commit` refuses to run on a clean machine.
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "config", "user.name", "test"], check=True)
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path, monkeypatch):
    """A directory that is NOT a git repo."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def stat(path, added=1, deleted=0):
    """Shorthand so tests read as data, not constructor noise."""
    return NumStat(added_lines=added, deleted_lines=deleted, path=path)


def stage(root, name, content):
    """Write a file (creating parent dirs) and stage it."""
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    subprocess.run(["git", "add", name], check=True)
