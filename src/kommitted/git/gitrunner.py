import subprocess


class GitError(Exception):
    pass


# Git escapes non-ASCII bytes in paths by default, so `café.go` arrives as
# `"caf\303\251.go"` - quoted, and no longer a path anything can open. Off
# is what every modern terminal wants.
_GIT = ("git", "-c", "core.quotePath=false")


def _run_git(*args: str) -> str:
    try:
        result = subprocess.run(
            [*_GIT, *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        # git isn't installed or isn't on PATH.
        raise GitError("git executable not found on PATH") from exc

    if result.returncode != 0:
        # Any nonzero exit is a real failure.
        raise GitError(
            f"git {' '.join(args)} failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )

    return result.stdout


def staged_diff() -> str:
    return _run_git("diff", "--staged")


def staged_numstat() -> str:
    return _run_git("diff", "--staged", "--numstat")


def current_branch() -> str:
    return _run_git("branch", "--show-current").strip()


def commit(message: str) -> None:
    _run_git("commit", "-m", message)


def read_setting(key: str) -> str | None:
    try:
        value = _run_git("config", "--get", key).strip()
    except GitError:
        return None
    return value or None


def write_setting(key: str, value: str, *, everywhere: bool = False) -> None:
    scope = "--global" if everywhere else "--local"
    _run_git("config", scope, key, value)


def current_branch_or_empty() -> str:
    try:
        return current_branch()
    except GitError:
        return ""
