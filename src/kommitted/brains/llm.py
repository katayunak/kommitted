"""LLM brain - asks a model to read the diff and judge the commit.

Uses Google's Gemini free tier
"""

import json
import os
import urllib.error
import urllib.request

from ..git import constants as gc
from ..git.models import Classification, NumStat
from . import constants as c
from .rules.commit_type import CommitType
from .rules.rules import RuleBrain

SYSTEM_PROMPT = """\
You are a senior engineer writing a git commit message.

Read the diff and decide which Conventional Commits type it is:
- feat: new user-facing capability
- fix: corrects broken behaviour
- refactor: restructures code without changing behaviour
- docs: documentation only
- test: tests only
- chore: build, config, dependencies, tooling

Then write a subject: imperative mood, lowercase, no trailing period, under
40 characters. Describe WHAT CHANGED AND WHY, not which files moved.

Good:  "handle binary files in numstat"
Bad:   "update diffparser.py"

Set confidence honestly. If the diff is ambiguous, say so with a low number
rather than guessing high.\
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": [
                *(t.value for t in CommitType),
            ],
        },
        "subject": {"type": "string"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["type", "subject", "confidence", "reason"],
}


class LLMError(Exception):
    pass


def build_prompt(stats: list[NumStat], diff: str, branch: str = "") -> str:
    files = "\n".join(
        f"  {st.path} (+{st.added_lines} -{st.deleted_lines})" for st in stats
    )

    truncated = diff[: c.MAX_DIFF_CHARS]
    note = "\n\n[diff truncated]" if len(diff) > c.MAX_DIFF_CHARS else ""

    # The branch name is what the author said they were doing. Cheap
    # context for the model, and it costs a handful of tokens.
    header = f"Branch: {branch}\n\n" if branch else ""

    return f"{header}Files changed:\n{files}\n\nDiff:\n{truncated}{note}"


def call_gemini(prompt: str, api_key: str) -> dict:
    url = c.GEMINI_API_URL.format(model=c.GEMINI_MODEL)
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
        },
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=c.LLM_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise LLMError(f"HTTP {exc.code}: {exc.read()[:200].decode(errors='replace')}")
    except urllib.error.URLError as exc:
        raise LLMError(f"network error: {exc.reason}")
    except TimeoutError:
        raise LLMError(f"timed out after {c.LLM_TIMEOUT_SECONDS}s")
    except json.JSONDecodeError as exc:
        raise LLMError(f"API returned non-JSON: {exc}")

    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"unexpected response shape: {exc}")

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"model returned malformed JSON: {exc}")


class LLMBrain:
    """Ask Gemini. Whether a failure is fatal depends on what was asked for.

    `-b llm` is an instruction, not a preference. If the user names the
    model and the model cannot be reached, silently answering with the rule
    brain produces a message that LOOKS fine and is not what they asked for -
    and without `--why` there is nothing on screen to say so.

    So: `llm` is strict and raises. `auto` is the mode that degrades, and it
    says why in the first reason.

    Fallback belongs to `auto`, not to failure. Once any mode is allowed to
    degrade quietly, the flags stop meaning anything.
    """

    def __init__(self, api_key: str | None = None, *, strict: bool = True):
        # Read the env var lazily so importing this module never fails and
        # tests can inject a key without touching the environment.
        self.api_key = api_key or os.environ.get(c.GEMINI_API_KEY_ENV, "")
        self.fallback = RuleBrain()
        self.strict = strict
        self.name = "llm" if strict else "auto"

    def classify(
        self, stats: list[NumStat], diff: str = "", branch: str = ""
    ) -> Classification:
        if not stats:
            return self.fallback.classify(stats, diff, branch)

        try:
            if not self.api_key:
                raise LLMError(f"{c.GEMINI_API_KEY_ENV} is not set")
            result = call_gemini(build_prompt(stats, diff, branch), self.api_key)
            return self._to_classification(result)
        except LLMError as exc:
            if self.strict:
                # The CLI turns this into a message on stderr and a nonzero
                # exit, so a script that pipes into `git commit` stops
                # instead of committing something the user did not ask for.
                raise

            # with_reason returns a NEW Classification rather than mutating -
            # the dataclass is frozen, so the fallback path can't accidentally
            # corrupt a verdict another caller is holding.
            return self.fallback.classify(stats, diff, branch).with_reason(
                c.REASON_LLM_FALLBACK.format(error=exc)
            )

    def _to_classification(self, result: dict) -> Classification:
        """Validate the model's answer before trusting it."""
        commit_type = result.get("type", "")
        if commit_type not in gc.VERBS:
            raise LLMError(f"model returned unknown type {commit_type!r}")

        # A model can return confidence as a string, or out of range.
        try:
            confidence = float(result.get("confidence", 0))
        except (TypeError, ValueError):
            raise LLMError("model returned non-numeric confidence")
        confidence = max(0.0, min(1.0, confidence))

        subject = str(result.get("subject", "")).strip()
        if not subject:
            raise LLMError("model returned an empty subject")

        if confidence < c.LLM_MIN_CONFIDENCE:
            # The model told us it was guessing. Believe it.
            raise LLMError(f"confidence {confidence:.2f} below threshold")

        return Classification(
            type=commit_type,
            confidence=confidence,
            reasons=(c.REASON_LLM_PREFIX + str(result.get("reason", "")).strip(),),
            subject=subject,
        )
