import subprocess


class GitError(Exception):
    pass


def _run_git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
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
