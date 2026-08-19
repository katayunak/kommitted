"""Everything that talks to git, or that reads what git prints."""

from . import constants
from .builder import build
from .diffcontent import Change, DiffContent, Line, Symbol, parse_diff
from .diffparser import parse_numstat
from .gitrunner import (
    GitError,
    commit,
    current_branch,
    read_setting,
    staged_diff,
    staged_numstat,
    write_setting,
)
from .models import Classification, NumStat

__all__ = [
    "Change",
    "Classification",
    "DiffContent",
    "GitError",
    "Line",
    "NumStat",
    "Symbol",
    "build",
    "commit",
    "constants",
    "current_branch",
    "parse_diff",
    "parse_numstat",
    "read_setting",
    "staged_diff",
    "staged_numstat",
    "write_setting",
]
