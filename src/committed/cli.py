import argparse
import sys

from . import constants as c
from . import gitrunner
from .brains import BRAINS, DEFAULT_BRAIN, get_brain
from .builder import build
from .diffparser import parse_numstat


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
    parser.add_argument(
        "--brain",
        default=DEFAULT_BRAIN,
        choices=sorted(BRAINS),
        help="which strategy decides the commit type (default: %(default)s)",
    )
    # argv=None makes argparse read sys.argv. Passing it explicitly is what
    # lets tests call parse_args(["--why"]) without touching global state.
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    """The whole pipeline. Returns the process exit code.

    Returning a code instead of calling sys.exit keeps this testable - a test
    can assert on the return value rather than catching SystemExit.
    """
    stats = parse_numstat(gitrunner.staged_numstat())

    if not stats:
        # Not an error: git worked fine and there is simply nothing staged.
        print(c.MSG_NOTHING_STAGED)
        return c.EXIT_OK

    brain = get_brain(args.brain)
    # Only fetch the full diff if the brain will actually use it. The rule
    # brain ignores it, and on a big changeset this is a lot of text.
    diff = "" if brain.name == "rules" else gitrunner.staged_diff()

    classification = brain.classify(stats, diff)
    message = build(classification, stats)

    if args.why:
        # Reasoning goes to stderr so `committed | git commit -F -` still
        # pipes a clean message. Same stdout-is-the-data-channel discipline
        # as the parser.
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


if __name__ == "__main__":
    sys.exit(main())
