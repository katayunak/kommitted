import argparse
import sys

from . import constants as c
from .brains import (
    BRAINS,
    BRAINS_NEEDING_DIFF,
    DEFAULT_BRAIN,
    LLMError,
    get_brain,
)
from .git import constants as gc
from .git import gitrunner
from .git.builder import build
from .git.diffcontent import parse_diff
from .git.diffparser import parse_numstat


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="kommitted",
        description="Write a Conventional Commits message from your staged changes.",
    )

    parser.add_argument(
        "-y",
        "--why",
        action="store_true",
        help="show why this commit?",
    )

    parser.add_argument(
        "-c",
        "--commit",
        action="store_true",
        help="commit the message",
    )

    parser.add_argument(
        "-b",
        "--brain",
        default=None,
        choices=sorted(BRAINS),
        help="which strategy decides the commit type (default: saved, else rules)",
    )

    # No short forms on purpose. Short flags are a small, shared namespace,
    # so they are worth spending only on things you type every day - and you
    # save a setting once, then never again. `--global` also reaches outside
    # this repo, so making it long is a deliberate speed bump. Git makes the
    # same call: `git config --global` has no short form either.
    parser.add_argument(
        "--save",
        action="store_true",
        help="remember --brain for this repository",
    )

    parser.add_argument(
        "--global",
        dest="everywhere",
        action="store_true",
        help="with --save, remember it for every repository",
    )

    # argv=None makes argparse read sys.argv. Passing it explicitly is what
    # lets tests call parse_args(["--why"]) without touching global state.
    return parser.parse_args(argv)


def choose_brain(asked_for: str | None) -> str:
    if asked_for:
        return asked_for

    saved = gitrunner.read_setting(gc.SETTING_BRAIN)
    if saved in BRAINS:
        return saved
    return DEFAULT_BRAIN


def save_settings(args: argparse.Namespace) -> int:
    if not args.brain:
        print("--save needs --brain, e.g. `kommitted -b rules --save`", file=sys.stderr)
        return c.EXIT_ERROR

    gitrunner.write_setting(gc.SETTING_BRAIN, args.brain, everywhere=args.everywhere)
    print(gc.MSG_SETTING_SAVED.format(key=gc.SETTING_BRAIN, value=args.brain))
    return c.EXIT_OK


def run(args: argparse.Namespace) -> int:
    if args.save:
        return save_settings(args)

    stats = parse_numstat(gitrunner.staged_numstat())
    if not stats:
        print(gc.MSG_NOTHING_STAGED)
        return c.EXIT_OK

    brain = get_brain(choose_brain(args.brain))

    diff = ""
    if brain.name in BRAINS_NEEDING_DIFF:
        diff = gitrunner.staged_diff()

    branch = gitrunner.current_branch_or_empty()

    # TODO(double-parse): the rules brain parses this diff again internally.
    content = parse_diff(diff) if diff else None

    classification = brain.classify(stats, diff, branch)
    message = build(classification, stats, content)

    if args.why:
        print(
            f"brain: {brain.name}  type: {classification.type} "
            f"(confidence {classification.confidence:.2f})",
            file=sys.stderr,
        )
        for reason in classification.reasons:
            print(f"  - {reason}", file=sys.stderr)
        print(file=sys.stderr)

    if args.commit:
        gitrunner.commit(message)
        print(gc.MSG_COMMITTED)

    print(message)
    return c.EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except gitrunner.GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return c.EXIT_ERROR
    except LLMError as exc:
        # `-b llm` asked for the model specifically. Quietly answering with
        # the rule brain would print something that looks fine and is not
        # what was requested, and a script piping into `git commit` would
        # never notice. Say so, and exit nonzero so the pipe stops.
        print(f"error: {exc}", file=sys.stderr)
        print("use `-b auto` to fall back to rules instead", file=sys.stderr)
        return c.EXIT_ERROR