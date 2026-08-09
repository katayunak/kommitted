#!/usr/bin/env python3
"""committed - write a Conventional Commits message from your staged changes.

Usage:
    committed              show the suggested message
    committed --why        also show how the type was decided
    committed --commit     create the commit with that message
"""

import argparse
import os
import sys

# The tool runs from inside *other* repos, so the current directory is never
# our project. Anchor the import path to this file's location instead.
#
# A packaged install (pyproject + `pip install -e .`) would make this
# unnecessary, but that's a distribution concern, not a code one - and this
# keeps the tool runnable straight from a clone.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "model"))

import gitrunner  # noqa: E402
from builder import build  # noqa: E402
from classifier import classify  # noqa: E402
from diffparser import num_stat_parser  # noqa: E402

# Exit codes. 0 = success, 1 = we failed, 2 = argparse's own usage error.
EXIT_OK = 0
EXIT_ERROR = 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="committed",
        description="Write a Conventional Commits message from staged changes.",
    )
    parser.add_argument(
        "--why",
        action="store_true",
        help="show why this commit type was chosen",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="create the commit, not just print the message",
    )
    # argv=None makes argparse read sys.argv. Passing it explicitly is what
    # lets tests call parse_args(["--why"]) without touching global state.
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    """The whole pipeline. Returns the process exit code.

    Returning a code instead of calling sys.exit keeps this testable - a test
    can assert on the return value rather than catching SystemExit.
    """
    numstat = gitrunner.staged_numstat()
    stats = num_stat_parser(numstat)

    if not stats:
        # Not an error: git worked fine and there is simply nothing staged.
        print("no staged changes - run `git add` first")
        return EXIT_OK

    classification = classify(stats)
    message = build(classification, stats)

    if args.why:
        # Reasoning goes to stderr so `committed --why | git commit -F -`
        # still pipes a clean message. Same stdout-is-data discipline as
        # the parser.
        print(f"type: {classification.type} "
              f"(confidence {classification.confidence:.2f})", file=sys.stderr)
        for reason in classification.reasons:
            print(f"  - {reason}", file=sys.stderr)
        print(file=sys.stderr)

    if args.commit:
        gitrunner.commit(message)
        print("committed:")
        print(message)
        return EXIT_OK

    print(message)
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except gitrunner.GitError as exc:
        # The only expected failure. Anything else is a bug and should keep
        # its traceback rather than be swallowed here.
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
