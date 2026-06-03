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
