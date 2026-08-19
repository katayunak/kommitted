"""Rule-based brain: explicit rules, no model, no network, no API key.

Fast, free, offline, and completely explainable - every answer carries the
rules that produced it.

Evidence we read today:
    file paths          tests / docs / config          (reliable)
    branch name         `fix/...` says what was meant  (usually honest)
    new definitions     new functions and types        (good)
    edit kinds          operator vs literal vs rename  (the fix/refactor key)
    behaviour counts    did control flow move          (necessary, not enough)
    comments            prose-only changes             (reliable)
    line counts         shape                          (nearly meaningless)

Evidence we still do not read:

  1. FILE STATUS (A/M/D/R). `git diff --staged --name-status` gives it.
     Numstat cannot tell a brand-new file from an appended one - both print
     "40  0  file". Status would separate "add" from "update", make all-D
     commits `chore`, and catch renames outright.

  2. CROSS-FILE MOVES. A function deleted from a.go and added in b.go is
     the commonest refactor there is. Pairing is per-file, so today it reads
     as a delete plus an add.

  3. COMMIT HISTORY. `git log` shows how THIS team writes messages. Learning
     their conventions beats imposing ours.
"""

from ...git.models import Classification, NumStat
from . import constants as c
from .commit_type import CommitType
from .context import Context
from .scorers import score_all


class RuleBrain:
    name = "rules"

    def classify(
        self, stats: list[NumStat], diff: str = "", branch: str = ""
    ) -> Classification:
        if not stats:
            return Classification(
                type=CommitType.CHORE.value,
                confidence=0.0,
                reasons=(c.REASON_NOTHING_STAGED,),
            )

        context = Context.collect(files=stats, diff_text=diff, branch=branch)
        return score_all(context).classify()
