import argparse
import sys

from . import constants as c
from . import gitrunner
from .brains import BRAINS, BRAINS_NEEDING_DIFF, DEFAULT_BRAIN, get_brain
from .builder import build
from .diffparser import parse_numstat


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="kommitted",
        description="Write a Conventional Commits message from staged changes.",
    )
    parser.add_argument(
        "-y",
        "--why",
        action="store_true",
        help="show why this commit type was chosen",
    )
    parser.add_argument(
        "-c",
        "--commit",
        action="store_true",
        help="create the commit, not just print the message",
    )
    parser.add_argument(
        "-b",
        "--brain",
        default=DEFAULT_BRAIN,
        choices=sorted(BRAINS),
        help="which strategy decides the commit type (default: %(default)s)",
    )
    # argv=None makes argparse read sys.argv. Passing it explicitly is what
    # lets tests call parse_args(["--why"]) without touching global state.
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    # always start simple
    stats = parse_numstat(gitrunner.staged_numstat())

    if not stats:
        # nothing staged yet
        print(c.MSG_NOTHING_STAGED)
        return c.EXIT_OK

    brain = get_brain(args.brain)

    diff = ""
    if brain.name in BRAINS_NEEDING_DIFF:
        diff = gitrunner.staged_diff()

    classification = brain.classify(stats, diff)
    message = build(classification, stats)

    if args.why:
        # committed --why | git commit -F -
        # the terminal still displays stderr, so the user sees the explanation, but it doesn't enter the pipe
        # stdout will
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
        print(c.MSG_COMMITTED)

    print(message)
    return c.EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except gitrunner.GitError as exc:
        # The only expected failure. Anything else is a bug and should keep
        # its traceback rather than be swallowed here.
        print(f"error: {exc}", file=sys.stderr)
        return c.EXIT_ERROR