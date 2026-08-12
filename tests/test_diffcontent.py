"""Tests for reading meaning out of the diff body, per language."""

import pytest

from kommitted import languages
from kommitted.diffcontent import parse_diff

PY_NEW_FUNC = """\
diff --git a/model/parser.py b/model/parser.py
--- a/model/parser.py
+++ b/model/parser.py
@@ -1,2 +1,6 @@
 import json
+
+def parse_numstat(raw):
+    return raw.split()
"""

GO_NEW_FUNC = """\
diff --git a/git.go b/git.go
+++ b/git.go
@@ -1 +1,4 @@
+func StagedDiff() (string, error) {
+	return run("diff")
+}
"""

GO_METHOD = """\
+++ b/git.go
+func (r *Runner) Commit(msg string) error {
"""

MOVED_FUNC = """\
--- a/model/old.py
+++ b/model/old.py
-def helper(x):
-    return x
+def helper(x):
+    return x + 1
"""

PY_ERROR_HANDLING = """\
+++ b/a.py
@@ -1,3 +1,6 @@
 value = load()
+if value is None:
+    raise ValueError("missing")
"""

GO_ERROR_HANDLING = """\
+++ b/a.go
+	if err != nil {
+		return nil, err
+	}
"""


def names(symbols):
    """Compare on (kind, name); the language tag is asserted separately."""
    return [(s.kind, s.name) for s in symbols]


# ---------------------------------------------------------------------------
# Symbol detection, per language
# ---------------------------------------------------------------------------


def test_finds_new_python_function():
    assert ("func", "parse_numstat") in names(parse_diff(PY_NEW_FUNC).added)


def test_finds_new_go_function():
    assert ("func", "StagedDiff") in names(parse_diff(GO_NEW_FUNC).added)


def test_finds_go_method_with_receiver():
    # `func (r *Runner) Commit(...)` - the receiver must not be captured.
    assert ("func", "Commit") in names(parse_diff(GO_METHOD).added)


def test_symbols_are_tagged_with_their_language():
    assert parse_diff(PY_NEW_FUNC).added[0].language == "python"
    assert parse_diff(GO_NEW_FUNC).added[0].language == "go"


def test_language_is_tracked_from_the_file_header():
    assert parse_diff(PY_NEW_FUNC).languages_seen == {"python"}
    assert parse_diff(GO_NEW_FUNC).languages_seen == {"go"}


# ---------------------------------------------------------------------------
# The point of per-language rules: no cross-language false positives
# ---------------------------------------------------------------------------


def test_go_syntax_inside_a_python_file_is_ignored():
    # A .py file containing the literal text `type Config struct` is a string
    # or a comment, not a Go type. Language-agnostic patterns would have
    # matched it.
    diff = "+++ b/a.py\n+type Config struct {\n"
    assert names(parse_diff(diff).added) == []


def test_python_def_inside_a_go_file_is_ignored():
    diff = "+++ b/a.go\n+def not_python_here(x):\n"
    assert names(parse_diff(diff).added) == []


def test_unknown_extension_finds_nothing():
    # Silence beats guessing wrong on a language we have no rules for.
    diff = "+++ b/a.rb\n+def ruby_method\n"
    assert parse_diff(diff).added == []


def test_go_error_pattern_does_not_fire_on_python():
    diff = "+++ b/a.py\n+comment = 'if err != nil'\n"
    assert parse_diff(diff).error_handling_added == 0


# ---------------------------------------------------------------------------
# new vs moved
# ---------------------------------------------------------------------------


def test_new_symbols_excludes_moved_ones():
    content = parse_diff(MOVED_FUNC)
    # 'helper' appears on both sides -> edited, not created.
    assert content.new_symbols == []
    assert ("func", "helper") in names(content.moved_symbols)


def test_new_symbol_is_new_when_absent_from_removed_side():
    assert [s.name for s in parse_diff(PY_NEW_FUNC).new_symbols] == ["parse_numstat"]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("diff", [PY_ERROR_HANDLING, GO_ERROR_HANDLING])
def test_detects_added_error_handling(diff):
    assert parse_diff(diff).error_handling_added >= 1


# ---------------------------------------------------------------------------
# Headers and edge cases
# ---------------------------------------------------------------------------


def test_file_headers_are_not_treated_as_content():
    # '+++ b/model/parser.py' starts with '+' but is a header. If it leaked
    # through, every filename would look like a changed line.
    assert all("parser" not in s.name for s in parse_diff(PY_NEW_FUNC).added)


def test_empty_diff_is_safe():
    content = parse_diff("")
    assert content.added == []
    assert content.removed == []
    assert content.new_symbols == []
    assert content.languages_seen == set()


def test_diff_with_no_definitions():
    assert parse_diff("+++ b/a.py\n+x = compute()\n+y = x + 1\n").added == []


def test_multiple_files_switch_language_mid_diff():
    diff = PY_NEW_FUNC + GO_NEW_FUNC
    content = parse_diff(diff)
    assert content.languages_seen == {"python", "go"}
    assert ("func", "parse_numstat") in names(content.added)
    assert ("func", "StagedDiff") in names(content.added)


def test_python_class_detected():
    assert ("class", "Parser") in names(parse_diff("+++ b/a.py\n+class Parser:\n").added)


def test_go_type_detected():
    diff = "+++ b/a.go\n+type Config struct {\n"
    assert ("type", "Config") in names(parse_diff(diff).added)


def test_uppercase_constants_detected():
    diff = "+++ b/c.py\n+MAX_RETRIES = 3\n+local_thing = 4\n"
    found = [n for _, n in names(parse_diff(diff).added)]
    assert "MAX_RETRIES" in found
    assert "local_thing" not in found  # lowercase locals are noise


# ---------------------------------------------------------------------------
# languages.py itself
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path, expected",
    [
        ("a.py", "python"),
        ("src/b.go", "go"),
        ("web/c.tsx", "javascript"),
        ("d.rb", "unknown"),
        ("Makefile", "unknown"),  # no extension at all
    ],
)
def test_language_lookup_by_extension(path, expected):
    assert languages.for_path(path).name == expected


@pytest.mark.parametrize("path", ["go.mod", "requirements.txt", "web/package.json"])
def test_manifest_detection(path):
    assert languages.is_manifest(path)


def test_non_manifest():
    assert not languages.is_manifest("src/main.py")


def test_manifest_change_is_recorded():
    assert parse_diff("+++ b/go.mod\n+require x v1.0\n").manifest_changed
