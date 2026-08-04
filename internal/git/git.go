// Package git is the only place in this project that talks to git.
// Keeping it isolated means the rest of the code never cares *how* we get
// a diff - it just asks for one.
package git

import (
	"fmt"
	"os/exec"
)

// StagedDiff returns the output of `git diff --staged`.
//
// Note what this does NOT do: it doesn't decide whether an empty diff is a
// problem. Returning "" with a nil error is a perfectly valid result - it
// means git ran fine and there was simply nothing staged. Deciding what to
// do about that is the caller's job, not ours.
func StagedDiff() (string, error) {
	cmd := exec.Command("git", "diff", "--staged")

	out, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("running git diff --staged: %w", err)
	}

	return string(out), nil
}

func StagedDiffNumStat() (string, error) {
	cmd := exec.Command("git", "diff", "--staged", "--numstat")

	out, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("running git diff --staged: %w", err)
	}

	return string(out), nil
}
