"""Tests for the rule-based brain."""

import pytest

from kommitted import constants as c
from kommitted.brains import BRAINS, DEFAULT_BRAIN, get_brain
from kommitted.brains.rules import RuleBrain, is_config, is_doc, is_test
from kommitted.diffparser import parse_numstat

from .conftest import stat


@pytest.fixture
def brain():
    return RuleBrain()


# ---------------------------------------------------------------------------
# Path predicates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["tests/test_a.py", "model/test_thing.py", "internal/git/git_test.go", "a.spec.ts"],
)
def test_is_test_matches(path):
    assert is_test(path)


@pytest.mark.parametrize("path", ["model/builder.py", "README.md", "latest.py"])
def test_is_test_rejects(path):
    assert not is_test(path)


@pytest.mark.parametrize("path", ["README.md", "docs/guide.rst", "notes.txt"])
def test_is_doc_matches(path):
    assert is_doc(path)


@pytest.mark.parametrize("path", [".gitignore", "go.mod", ".github/ci.yml"])
def test_is_config_matches(path):
    assert is_config(path)


# ---------------------------------------------------------------------------
# classify - path rules (the reliable ones)
# ---------------------------------------------------------------------------


def test_nothing_staged(brain):
    result = brain.classify([])
    assert result.type == c.TYPE_CHORE
    assert result.confidence == c.CONFIDENCE_NONE
    assert result.reasons == (c.REASON_NOTHING_STAGED,)


def test_only_tests(brain):
    result = brain.classify([stat("tests/test_a.py", 40, 0)])
    assert result.type == c.TYPE_TEST
    assert result.confidence == c.CONFIDENCE_PATH_STRONG


def test_only_docs(brain):
    result = brain.classify([stat("README.md", 12, 3)])
    assert result.type == c.TYPE_DOCS
    assert result.reasons == (c.REASON_ONLY_DOCS,)


def test_only_config(brain):
    result = brain.classify([stat(".gitignore", 5, 0), stat("go.mod", 2, 0)])
    assert result.type == c.TYPE_CHORE


def test_path_rules_beat_shape_rules(brain):
    # 200 purely-additive lines would otherwise say "feat". Tests win.
    result = brain.classify([stat("tests/test_a.py", 200, 0)])
    assert result.type == c.TYPE_TEST


def test_mixed_paths_fall_through_to_shape_rules(brain):
    # Not ALL tests, so the path rule must not fire.
    result = brain.classify([stat("tests/test_a.py", 10, 0), stat("src/a.py", 10, 0)])
    assert result.type != c.TYPE_TEST


# ---------------------------------------------------------------------------
# classify - shape rules (the guesses)
# ---------------------------------------------------------------------------


def test_purely_additive_is_feat(brain):
    result = brain.classify([stat("src/a.py", 120, 0)])
    assert result.type == c.TYPE_FEAT
    assert result.confidence == c.CONFIDENCE_SHAPE_ADDITIVE


def test_purely_deletions_is_chore(brain):
    result = brain.classify([stat("src/a.py", 0, 40)])
    assert result.type == c.TYPE_CHORE


def test_balanced_edit_is_refactor(brain):
    result = brain.classify([stat("src/a.py", 30, 28)])
    assert result.type == c.TYPE_REFACTOR


def test_mostly_additions_is_feat(brain):
    result = brain.classify([stat("src/a.py", 100, 10)])
    assert result.type == c.TYPE_FEAT


def test_mostly_deletions_is_fix(brain):
    result = brain.classify([stat("src/a.py", 5, 40)])
    assert result.type == c.TYPE_FIX


def test_shape_rules_are_less_confident_than_path_rules(brain):
    shape = brain.classify([stat("src/a.py", 100, 10)])
    path = brain.classify([stat("README.md", 100, 10)])
    # The tool should be honest about which answers it trusts.
    assert shape.confidence < path.confidence


def test_binary_only_change_does_not_crash(brain):
    from kommitted.models import NumStat

    result = brain.classify([NumStat(None, None, "logo.png")])
    assert result.type  # any answer is fine; not crashing is the point


def test_every_answer_carries_a_reason(brain):
    cases = ["10\t0\ta.py\n", "0\t10\ta.py\n", "30\t28\ta.py\n", "5\t40\ta.py\n"]
    for raw in cases:
        result = brain.classify(parse_numstat(raw))
        assert result.reasons, f"no reason given for {raw!r}"


def test_diff_argument_is_accepted_and_ignored(brain):
    # The Brain protocol passes a diff; rules don't use it but must accept it.
    a = brain.classify([stat("src/a.py", 10, 0)])
    b = brain.classify([stat("src/a.py", 10, 0)], diff="some diff text")
    assert a == b


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------


def test_default_brain_is_registered():
    assert DEFAULT_BRAIN in BRAINS


def test_get_brain_returns_an_instance():
    assert isinstance(get_brain("rules"), RuleBrain)


def test_get_brain_rejects_unknown_names():
    with pytest.raises(KeyError) as excinfo:
        get_brain("nonsense")
    # The error should tell the user what IS available.
    assert "rules" in str(excinfo.value)


def test_rule_brain_satisfies_the_protocol():
    # Structural typing: no inheritance, just the right method and attribute.
    brain = get_brain("rules")
    assert hasattr(brain, "name")
    assert callable(brain.classify)
