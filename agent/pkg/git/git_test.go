package git

import (
	"context"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// runShell is a tiny helper to set up a real git repo in a tempdir for
// these tests. We rely on the system `git` binary being on PATH — same
// dependency the real agent has.
func runShell(t *testing.T, dir string, args ...string) {
	t.Helper()
	cmd := exec.Command(args[0], args[1:]...)
	cmd.Dir = dir
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("%v failed: %v\n%s", args, err, out)
	}
}

func setupRepo(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	runShell(t, dir, "git", "init", "-q", "-b", "main")
	runShell(t, dir, "git", "config", "user.email", "test@example.com")
	runShell(t, dir, "git", "config", "user.name", "test")
	runShell(t, dir, "git", "config", "commit.gpgsign", "false")
	return dir
}

func TestInspectReturnsBranchAndTopLevel(t *testing.T) {
	dir := setupRepo(t)
	// Create one commit so HEAD resolves.
	runShell(t, dir, "git", "commit", "-q", "--allow-empty", "-m", "init")
	repo, err := Inspect(context.Background(), dir)
	if err != nil {
		t.Fatalf("inspect: %v", err)
	}
	if repo.Branch != "main" {
		t.Errorf("branch: %q", repo.Branch)
	}
	if filepath.Base(repo.OriginCWD) != filepath.Base(dir) {
		t.Errorf("top-level mismatch: %q vs %q", repo.OriginCWD, dir)
	}
	if repo.IsWorktree {
		t.Error("not a worktree, IsWorktree should be false")
	}
}

func TestInspectErrorsOnNonRepo(t *testing.T) {
	dir := t.TempDir()
	_, err := Inspect(context.Background(), dir)
	if err != ErrNotARepo {
		t.Errorf("expected ErrNotARepo, got %v", err)
	}
}

func TestCommitsSinceReturnsHashes(t *testing.T) {
	dir := setupRepo(t)
	// Past, then a fresh commit.
	past := time.Now().Add(-time.Hour)
	runShell(t, dir, "git", "commit", "-q", "--allow-empty", "-m", "one")
	runShell(t, dir, "git", "commit", "-q", "--allow-empty", "-m", "two")
	hashes, err := CommitsSince(context.Background(), dir, past, 10)
	if err != nil {
		t.Fatalf("commits: %v", err)
	}
	if len(hashes) != 2 {
		t.Errorf("expected 2 hashes, got %d (%v)", len(hashes), hashes)
	}
	for _, h := range hashes {
		if len(h) != 40 {
			t.Errorf("hash %q not a full sha", h)
		}
	}
}

func TestLOCSinceCountsAddsAndDeletes(t *testing.T) {
	dir := setupRepo(t)
	past := time.Now().Add(-time.Hour)
	// One file, three lines added.
	runShell(t, dir, "git", "init", "-q") // idempotent
	writeAndCommit(t, dir, "a.txt", "1\n2\n3\n", "add a")
	// Delete one of them.
	writeAndCommit(t, dir, "a.txt", "1\n3\n", "remove line 2")
	loc, err := LOCSince(context.Background(), dir, past)
	if err != nil {
		t.Fatalf("loc: %v", err)
	}
	if loc.LinesAdded != 3 {
		t.Errorf("adds: %d", loc.LinesAdded)
	}
	if loc.LinesDeleted != 1 {
		t.Errorf("deletes: %d", loc.LinesDeleted)
	}
}

func writeAndCommit(t *testing.T, dir, name, content, msg string) {
	t.Helper()
	path := filepath.Join(dir, name)
	if err := writeFile(path, content); err != nil {
		t.Fatalf("write: %v", err)
	}
	runShell(t, dir, "git", "add", name)
	runShell(t, dir, "git", "commit", "-q", "-m", msg)
}

func writeFile(path, content string) error {
	cmd := exec.Command("sh", "-c", "cat > "+escapeSh(path))
	cmd.Stdin = strings.NewReader(content)
	return cmd.Run()
}

func escapeSh(s string) string {
	return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
}

func TestParseShortstat(t *testing.T) {
	tests := []struct {
		in   string
		want LOCDiff
	}{
		{" 1 file changed, 3 insertions(+)", LOCDiff{LinesAdded: 3}},
		{" 1 file changed, 1 insertion(+), 1 deletion(-)", LOCDiff{LinesAdded: 1, LinesDeleted: 1}},
		{
			" 2 files changed, 14 insertions(+), 3 deletions(-)\n 1 file changed, 5 insertions(+)",
			LOCDiff{LinesAdded: 19, LinesDeleted: 3},
		},
		{"", LOCDiff{}},
	}
	for _, tc := range tests {
		got := parseShortstat(tc.in)
		if got != tc.want {
			t.Errorf("parseShortstat(%q) = %+v, want %+v", tc.in, got, tc.want)
		}
	}
}
