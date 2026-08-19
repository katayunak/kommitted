"""Every brain must honour the same signature.

`Brain` is a typing.Protocol, and Protocols are checked by type checkers -
never at runtime. Python happily let `RuleBrain.classify` grow a `branch`
parameter while `LLMBrain.classify` kept two, and nothing failed until a
real user ran `kommitted -b llm`:

    TypeError: LLMBrain.classify() takes from 2 to 3 positional arguments
    but 4 were given

Every test called one brain directly with the arguments that brain happened
to accept, so the drift was invisible. These tests walk the registry
instead, so adding a brain or changing the signature breaks here first.
"""

import inspect

import pytest

from kommitted.brains import BRAINS, LLMError, get_brain
from kommitted.brains.base import Brain
from kommitted.git.models import Classification

from .conftest import stat

DIFF = "+++ b/a.py\n+x = 1\n"


@pytest.fixture(params=sorted(BRAINS))
def brain(request, monkeypatch):
    """Every registered brain, offline.

    Clearing the API key forces the LLM brain down its fallback path, so
    these run without a network or a key.
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return get_brain(request.param)


def called_ok(brain, *args, **kwargs) -> bool:
    """True if the call went through, whatever it decided afterwards.

    A strict brain raises LLMError when the model is unreachable, which is
    correct behaviour and still proves the signature accepted the call.
    These tests are about the interface, not the verdict.
    """
    try:
        return isinstance(brain.classify(*args, **kwargs), Classification)
    except LLMError:
        return True


def test_every_brain_accepts_the_full_signature(brain):
    assert called_ok(brain, [stat("a.py")], DIFF, "fix/thing")


def test_every_brain_accepts_keyword_arguments(brain):
    # Positional calls hide a renamed parameter. Keywords do not.
    assert called_ok(brain, [stat("a.py")], diff=DIFF, branch="fix/thing")


def test_every_brain_works_with_stats_alone(brain):
    assert called_ok(brain, [stat("a.py")])


def test_every_brain_handles_nothing_staged(brain):
    result = brain.classify([], "", "")
    assert isinstance(result, Classification)
    assert result.confidence == 0.0


def test_every_brain_has_a_name_matching_its_registry_key():
    for key in BRAINS:
        assert get_brain(key).name == key


def test_every_brain_signature_matches_the_protocol():
    """Compare parameter names and order against the Protocol itself.

    Catches a rename (`branch` -> `branch_name`) that positional calls would
    sail straight past.
    """
    expected = list(inspect.signature(Brain.classify).parameters)

    for key in BRAINS:
        actual = list(inspect.signature(get_brain(key).classify).parameters)
        # Bound methods drop `self`; the Protocol's unbound one keeps it.
        assert ["self", *actual] == expected, f"{key} drifted from Brain"


def test_an_unknown_brain_names_the_valid_options():
    with pytest.raises(KeyError) as caught:
        get_brain("nonsense")

    for key in BRAINS:
        assert key in str(caught.value)
