package main

import (
	"fmt"
	"os"
	"strings"

	"committed/internal/git"
)

func main() {
	diff, err := git.StagedDiff()
	if err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}

	diffNumSat, err := git.StagedDiffNumStat()
	if err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}

	// git exits 0 with empty output when nothing is staged. That's not an
	// error - it's a normal situation that deserves a useful message.
	if strings.TrimSpace(diff) == "" {
		fmt.Println("no staged changes - run `git add` first")
		return
	}

	fmt.Print(diff)
	fmt.Print(diffNumSat)
}
