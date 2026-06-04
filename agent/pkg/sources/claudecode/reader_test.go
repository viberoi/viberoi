package claudecode

import (
	"path/filepath"
	"testing"
	"time"
)

func TestReadFile_Fixture(t *testing.T) {
	path := filepath.Join("..", "..", "..", "testdata", "claudecode", "session.jsonl")
	got, err := ReadFile(path)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if got.SessionID != "sess-fixture-1" {
		t.Errorf("session id: %q", got.SessionID)
	}
	if got.Model != "claude-opus-4-7" {
		t.Errorf("model: %q", got.Model)
	}
	// 3 assistant turns → sum tokens across all of them.
	if got.TurnCount != 3 {
		t.Errorf("turn count: %d", got.TurnCount)
	}
	wantTokens := Tokens{
		Input:      1200 + 2400 + 3000,
		Output:     300 + 500 + 700,
		CacheRead:  800 + 1500 + 2000,
		CacheWrite: 50,
	}
	if got.Tokens != wantTokens {
		t.Errorf("tokens: got %+v want %+v", got.Tokens, wantTokens)
	}
	wantFiles := []string{"/repo/a.go", "/repo/b.go"}
	if len(got.FilesTouched) != len(wantFiles) {
		t.Errorf("files_touched: %v", got.FilesTouched)
	} else {
		for i, f := range wantFiles {
			if got.FilesTouched[i] != f {
				t.Errorf("files_touched[%d]: %q vs %q", i, got.FilesTouched[i], f)
			}
		}
	}
	if !got.IsAgentic {
		t.Error("expected IsAgentic=true (saw tool_use entries)")
	}
	wantStart := time.Date(2026, 6, 3, 12, 0, 0, 0, time.UTC)
	wantEnd := time.Date(2026, 6, 3, 12, 2, 0, 0, time.UTC)
	if !got.StartedAt.Equal(wantStart) {
		t.Errorf("started_at: %v", got.StartedAt)
	}
	if !got.EndedAt.Equal(wantEnd) {
		t.Errorf("ended_at: %v", got.EndedAt)
	}
}

func TestReadFile_MissingFile(t *testing.T) {
	_, err := ReadFile(filepath.Join(t.TempDir(), "nope.jsonl"))
	if err == nil {
		t.Error("expected error on missing file")
	}
}

// ── Subagent aggregation ────────────────────────────────────────────────

func TestReadFile_AggregatesSubagents(t *testing.T) {
	path := filepath.Join(
		"..", "..", "..", "testdata", "claudecode", "with-subagents", "session.jsonl",
	)
	got, err := ReadFile(path)
	if err != nil {
		t.Fatalf("read: %v", err)
	}

	// Main = 1 assistant turn. Subagent aaa = 2 turns. Subagent bbb = 1.
	if got.TurnCount != 4 {
		t.Errorf("turn count: got %d want 4", got.TurnCount)
	}
	if got.SubagentCount != 2 {
		t.Errorf("subagent count: got %d want 2", got.SubagentCount)
	}

	want := Tokens{
		Input:      1000 + 500 + 300 + 700,
		Output:     200 + 100 + 50 + 150,
		CacheRead:  500 + 200 + 150 + 300,
		CacheWrite: 50,
	}
	if got.Tokens != want {
		t.Errorf("tokens: got %+v want %+v", got.Tokens, want)
	}

	wantFiles := []string{"/repo/parent.go", "/repo/sub_a.go", "/repo/sub_b.go"}
	if len(got.FilesTouched) != len(wantFiles) {
		t.Errorf("files_touched: got %v want %v", got.FilesTouched, wantFiles)
	} else {
		for i, f := range wantFiles {
			if got.FilesTouched[i] != f {
				t.Errorf("files_touched[%d]: %q vs %q", i, got.FilesTouched[i], f)
			}
		}
	}

	// Subagent bbb runs until 10:01:00 — that should extend the parent
	// session's EndedAt past its 10:00:10 last turn.
	wantEnd := time.Date(2026, 6, 4, 10, 1, 0, 0, time.UTC)
	if !got.EndedAt.Equal(wantEnd) {
		t.Errorf("ended_at extension: got %v want %v", got.EndedAt, wantEnd)
	}

	// session_id stays the parent's — subagent ids are NOT promoted.
	if got.SessionID != "sess-parent-1" {
		t.Errorf("session id should stay parent's: %q", got.SessionID)
	}
}

func TestReadFile_SkipsNonAgentSubagentFiles(t *testing.T) {
	// The fixture has agent-aaa.meta.json — must NOT be parsed as a
	// subagent. If it were, SubagentCount would be 3 not 2.
	path := filepath.Join(
		"..", "..", "..", "testdata", "claudecode", "with-subagents", "session.jsonl",
	)
	got, err := ReadFile(path)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if got.SubagentCount != 2 {
		t.Errorf("subagent count should be 2 (sidecar .meta.json ignored): got %d", got.SubagentCount)
	}
}

func TestReadFile_NoSubagentDirIsFine(t *testing.T) {
	// Original fixture has no subagents/ dir — should not error.
	path := filepath.Join("..", "..", "..", "testdata", "claudecode", "session.jsonl")
	got, err := ReadFile(path)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if got.SubagentCount != 0 {
		t.Errorf("expected subagent count 0, got %d", got.SubagentCount)
	}
}
