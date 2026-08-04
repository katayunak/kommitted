package git

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// newTestRepo creates a throwaway git repo in a temp directory and makes it
// the working directory for the duration of the test.
//
// t.TempDir() and t.Chdir() both clean up automatically when the test ends,
// so no test can leak state into another one - or into your real repo.
func newTestRepo(t *testing.T) string {
	t.Helper()

	dir := t.TempDir()
	t.Chdir(dir)

	run := func(args ...string) {
		t.Helper()
		cmd := exec.Command("git", args...)
		if out, err := cmd.CombinedOutput(); err != nil {
			t.Fatalf("git %s failed: %v\n%s", strings.Join(args, " "), err, out)
		}
	}

	run("init")
	// Identity must be set or `git commit` refuses to run on a clean machine.
	run("config", "user.email", "test@example.com")
	run("config", "user.name", "test")

	return dir
}

func writeFile(t *testing.T, dir, name, content string) {
	t.Helper()
	path := filepath.Join(dir, name)
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("writing %s: %v", name, err)
	}
}

func gitAdd(t *testing.T, args ...string) {
	t.Helper()
	cmd := exec.Command("git", append([]string{"add"}, args...)...)
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("git add failed: %v\n%s", err, out)
	}
}

func TestStagedDiff_NothingStaged(t *testing.T) {
	newTestRepo(t)

	diff, err := StagedDiff()
	if err != nil {
		t.Fatalf("expected no error on an empty repo, got: %v", err)
	}
	if diff != "" {
		t.Errorf("expected empty diff, got %q", diff)
	}
}

func TestStagedDiff_NewFileStaged(t *testing.T) {
	dir := newTestRepo(t)
	writeFile(t, dir, "hello.txt", "line one\n")
	gitAdd(t, "hello.txt")

	diff, err := StagedDiff()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Check the pieces that matter, not the exact bytes - blob hashes in the
	// `index abc..def` line change every run, so asserting on the whole diff
	// would give you a test that fails for no reason.
	for _, want := range []string{"hello.txt", "new file", "+line one"} {
		if !strings.Contains(diff, want) {
			t.Errorf("diff missing %q\ngot:\n%s", want, diff)
		}
	}
}

func TestStagedDiff_UnstagedChangesAreIgnored(t *testing.T) {
	dir := newTestRepo(t)
	writeFile(t, dir, "hello.txt", "line one\n")
	// Deliberately NOT staged.

	diff, err := StagedDiff()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if diff != "" {
		t.Errorf("--staged must ignore unstaged work, got %q", diff)
	}
}

func TestStagedDiff_OnlyStagedVersionIsReported(t *testing.T) {
	dir := newTestRepo(t)

	writeFile(t, dir, "hello.txt", "staged version\n")
	gitAdd(t, "hello.txt")
	// Modify the file again AFTER staging. The staging area still holds the
	// old content - this is the whole point of the index.
	writeFile(t, dir, "hello.txt", "working dir version\n")

	diff, err := StagedDiff()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(diff, "staged version") {
		t.Errorf("expected the staged content in the diff, got:\n%s", diff)
	}
	if strings.Contains(diff, "working dir version") {
		t.Errorf("unstaged edit leaked into --staged output:\n%s", diff)
	}
}

func TestStagedDiff_NotAGitRepo(t *testing.T) {
	// A temp dir with no `git init` - git should fail and we should surface it.
	t.Chdir(t.TempDir())

	_, err := StagedDiff()
	if err == nil {
		t.Fatal("expected an error outside a git repo, got nil")
	}
	if !strings.Contains(err.Error(), "running git diff --staged") {
		t.Errorf("error should be wrapped with our context, got: %v", err)
	}
}

func TestStagedDiff_MultipleFiles(t *testing.T) {
	dir := newTestRepo(t)
	writeFile(t, dir, "a.txt", "aaa\n")
	writeFile(t, dir, "b.txt", "bbb\n")
	gitAdd(t, ".")

	diff, err := StagedDiff()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(diff, "a.txt") || !strings.Contains(diff, "b.txt") {
		t.Errorf("expected both files in the diff, got:\n%s", diff)
	}
}
