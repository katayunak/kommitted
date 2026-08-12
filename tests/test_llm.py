"""Tests for the LLM brain.

None of these hit the network. The point of a fallback path is that it works
when the network doesn't - so the tests replace `call_gemini` with fakes and
check every failure mode reaches the right place.
"""

import pytest

from kommitted import constants as c
from kommitted.brains import llm as llm_module
from kommitted.brains.llm import LLMBrain, LLMError, build_prompt

from .conftest import stat

GOOD_RESPONSE = {
    "type": "fix",
    "subject": "handle binary files in numstat",
    "confidence": 0.85,
    "reason": "adds a None branch for git's '-' marker",
}


@pytest.fixture
def brain():
    return LLMBrain(api_key="fake-key-for-tests")


def fake_gemini(response):
    """Build a stand-in for call_gemini that returns a fixed payload."""

    def _call(prompt, api_key):
        return response

    return _call


def failing_gemini(exc):
    def _call(prompt, api_key):
        raise exc

    return _call


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_uses_the_model_answer(brain, monkeypatch):
    monkeypatch.setattr(llm_module, "call_gemini", fake_gemini(GOOD_RESPONSE))

    result = brain.classify([stat("model/diffparser.py", 8, 2)], diff="+ x")

    assert result.type == "fix"
    assert result.confidence == 0.85
    assert result.subject == "handle binary files in numstat"


def test_reason_is_labelled_as_coming_from_the_model(brain, monkeypatch):
    monkeypatch.setattr(llm_module, "call_gemini", fake_gemini(GOOD_RESPONSE))
    result = brain.classify([stat("a.py")], diff="+ x")
    assert result.reasons[0].startswith(c.REASON_LLM_PREFIX)


# ---------------------------------------------------------------------------
# Fallback - the property that makes this shippable
# ---------------------------------------------------------------------------


def test_missing_api_key_falls_back_to_rules():
    brain = LLMBrain(api_key="")
    result = brain.classify([stat("model/a.py", 100, 0)], diff="+ x")

    assert result.type  # still got an answer
    assert c.GEMINI_API_KEY_ENV in result.reasons[0]


def test_network_failure_falls_back(brain, monkeypatch):
    monkeypatch.setattr(
        llm_module, "call_gemini", failing_gemini(LLMError("network error: unreachable"))
    )
    result = brain.classify([stat("model/a.py", 100, 0)], diff="+ x")

    assert result.type
    assert "network error" in result.reasons[0]


def test_unknown_commit_type_falls_back(brain, monkeypatch):
    bad = {**GOOD_RESPONSE, "type": "banana"}
    monkeypatch.setattr(llm_module, "call_gemini", fake_gemini(bad))

    result = brain.classify([stat("model/a.py", 100, 0)], diff="+ x")
    assert result.type in c.VERBS  # never leaks an invalid type downstream


def test_empty_subject_falls_back(brain, monkeypatch):
    bad = {**GOOD_RESPONSE, "subject": "   "}
    monkeypatch.setattr(llm_module, "call_gemini", fake_gemini(bad))

    result = brain.classify([stat("model/a.py", 100, 0)], diff="+ x")
    assert "empty subject" in result.reasons[0]


def test_low_confidence_falls_back_to_rules(brain, monkeypatch):
    unsure = {**GOOD_RESPONSE, "confidence": 0.1}
    monkeypatch.setattr(llm_module, "call_gemini", fake_gemini(unsure))

    result = brain.classify([stat("model/a.py", 100, 0)], diff="+ x")
    # A model that says it's guessing should not outrank an honest heuristic.
    assert "below threshold" in result.reasons[0]


def test_non_numeric_confidence_falls_back(brain, monkeypatch):
    bad = {**GOOD_RESPONSE, "confidence": "very sure"}
    monkeypatch.setattr(llm_module, "call_gemini", fake_gemini(bad))

    result = brain.classify([stat("model/a.py", 100, 0)], diff="+ x")
    assert "non-numeric" in result.reasons[0]


def test_confidence_above_one_is_clamped(brain, monkeypatch):
    overconfident = {**GOOD_RESPONSE, "confidence": 4.2}
    monkeypatch.setattr(llm_module, "call_gemini", fake_gemini(overconfident))

    result = brain.classify([stat("a.py")], diff="+ x")
    assert result.confidence == 1.0


def test_nothing_staged_never_calls_the_model(brain, monkeypatch):
    def explode(prompt, api_key):
        raise AssertionError("should not call the API with nothing staged")

    monkeypatch.setattr(llm_module, "call_gemini", explode)
    assert brain.classify([]).type == c.TYPE_CHORE


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def test_prompt_includes_files_and_diff():
    prompt = build_prompt([stat("model/a.py", 3, 1)], "+added line")
    assert "model/a.py (+3 -1)" in prompt
    assert "+added line" in prompt


def test_long_diff_is_truncated():
    huge = "+x\n" * 100_000
    prompt = build_prompt([stat("a.py")], huge)
    assert len(prompt) < c.MAX_DIFF_CHARS + 2000
    assert "[diff truncated]" in prompt


def test_file_list_survives_truncation():
    # The summary must outlive the cut - otherwise a huge diff leaves the
    # model with no idea which files changed.
    huge = "+x\n" * 100_000
    prompt = build_prompt([stat("model/important.py", 1, 1)], huge)
    assert "model/important.py" in prompt
