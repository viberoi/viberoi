// Package git wraps the local `git` CLI to extract branch + commit
// hashes + LOC numbers for a session window. Numbers only, never diff
// content — that's a privacy hard line.
//
// We shell out instead of pulling go-git because the dependency is
// large and the calls we need are trivial. The only flags passed to git
// are constants — no user input is interpolated into argv.
package git

import (
	"context"
	"errors"
	"fmt"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

// Errors callers can match on.
var (
	ErrNotARepo = errors.New("git: cwd is not a git repository")
)

// Repo summarises the working tree for a session.
type Repo struct {
	OriginCWD  string // git toplevel
	Branch     string // resolved real branch (not worktree)
	RawBranch  string // branch as `git rev-parse --abbrev-ref` returned
	IsWorktree bool
}

// LOCDiff is the line-count delta over a time range, derived from
// `git diff --shortstat --since=<t>`. Adds/deletes only; no file paths,
// no patch hunks.
type LOCDiff struct {
	LinesAdded   int
	LinesDeleted int
}

// Inspect returns the Repo for a directory. Returns ErrNotARepo when
// `dir` isn't inside a git working tree.
func Inspect(ctx context.Context, dir string) (*Repo, error) {
	top, err := runGit(ctx, dir, "rev-parse", "--show-toplevel")
	if err != nil {
		return nil, ErrNotARepo
	}
	branch, err := runGit(ctx, dir, "rev-parse", "--abbrev-ref", "HEAD")
	if err != nil {
		return nil, err
	}
	commonDir, _ := runGit(ctx, dir, "rev-parse", "--git-common-dir")
	gitDir, _ := runGit(ctx, dir, "rev-parse", "--git-dir")
	isWorktree := commonDir != "" && commonDir != gitDir

	resolved := branch
	if isWorktree {
		// Resolve symbolic ref via the common dir so we land on the real
		// branch the worktree tracks, not the worktree's own ref.
		if real, err := runGit(ctx, dir, "symbolic-ref", "--short", "HEAD"); err == nil {
			resolved = real
		}
	}

	return &Repo{
		OriginCWD:  top,
		Branch:     resolved,
		RawBranch:  branch,
		IsWorktree: isWorktree,
	}, nil
}

// CommitsSince returns commit hashes (full sha) authored after `since`.
// Bounded at `limit` to prevent runaway scans on long sessions.
func CommitsSince(ctx context.Context, dir string, since time.Time, limit int) ([]string, error) {
	out, err := runGit(ctx, dir,
		"log",
		"--pretty=format:%H",
		"--since="+since.UTC().Format(time.RFC3339),
		"--max-count="+strconv.Itoa(limit),
	)
	if err != nil {
		return nil, err
	}
	if out == "" {
		return []string{}, nil
	}
	return strings.Split(out, "\n"), nil
}

// LOCSince returns line-add/line-delete counts for commits since `since`.
func LOCSince(ctx context.Context, dir string, since time.Time) (LOCDiff, error) {
	out, err := runGit(ctx, dir,
		"log",
		"--shortstat",
		"--no-merges",
		"--pretty=tformat:",
		"--since="+since.UTC().Format(time.RFC3339),
	)
	if err != nil {
		return LOCDiff{}, err
	}
	return parseShortstat(out), nil
}

// parseShortstat reads lines like
//   ` 2 files changed, 14 insertions(+), 3 deletions(-)`
// and sums all `insertions(+)` / `deletions(-)` across them.
func parseShortstat(s string) LOCDiff {
	var d LOCDiff
	for _, line := range strings.Split(s, "\n") {
		for _, chunk := range strings.Split(line, ",") {
			chunk = strings.TrimSpace(chunk)
			if strings.HasSuffix(chunk, "insertions(+)") || strings.HasSuffix(chunk, "insertion(+)") {
				d.LinesAdded += firstIntOf(chunk)
			}
			if strings.HasSuffix(chunk, "deletions(-)") || strings.HasSuffix(chunk, "deletion(-)") {
				d.LinesDeleted += firstIntOf(chunk)
			}
		}
	}
	return d
}

func firstIntOf(s string) int {
	parts := strings.Fields(s)
	if len(parts) == 0 {
		return 0
	}
	n, err := strconv.Atoi(parts[0])
	if err != nil {
		return 0
	}
	return n
}

// FirstCommitTimeSince returns the timestamp of the EARLIEST commit
// authored after `since`. Zero time + nil if there are no commits.
// Used to compute Timing.time_to_first_commit_min for a session.
func FirstCommitTimeSince(ctx context.Context, dir string, since time.Time) (time.Time, error) {
	// --reverse + --max-count=1 gives the oldest commit in the window.
	out, err := runGit(ctx, dir,
		"log",
		"--reverse",
		"--pretty=format:%aI",
		"--since="+since.UTC().Format(time.RFC3339),
		"--max-count=1",
	)
	if err != nil {
		return time.Time{}, err
	}
	if out == "" {
		return time.Time{}, nil
	}
	t, parseErr := time.Parse(time.RFC3339, out)
	if parseErr != nil {
		return time.Time{}, fmt.Errorf("git: cannot parse commit time %q: %w", out, parseErr)
	}
	return t, nil
}

// IsDirty returns true when the working tree has uncommitted changes
// (staged, unstaged, or untracked). Used to populate
// CodeOutput.uncommitted_at_end when a session window closes.
//
// `git status --porcelain` exits 0 either way; non-empty output means
// dirty. Returns (false, err) on git invocation failure.
func IsDirty(ctx context.Context, dir string) (bool, error) {
	out, err := runGit(ctx, dir, "status", "--porcelain")
	if err != nil {
		return false, err
	}
	return out != "", nil
}

func runGit(ctx context.Context, dir string, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, "git", args...)
	cmd.Dir = dir
	out, err := cmd.Output()
	if err != nil {
		var ee *exec.ExitError
		if errors.As(err, &ee) {
			return "", fmt.Errorf("git %s exited %d", args[0], ee.ExitCode())
		}
		return "", fmt.Errorf("git %s: %w", args[0], err)
	}
	return strings.TrimSpace(string(out)), nil
}
