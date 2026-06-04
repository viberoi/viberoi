package claudecode_agentmode

import (
	"path/filepath"
	"testing"
	"time"
)

func TestReadFile_Fixture(t *testing.T) {
	path := filepath.Join(
		"..", "..", "..", "testdata", "claudecode_agentmode", "audit.jsonl",
	)
	got, err := ReadFile(path)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if got.SessionID != "agentmode-fixture-1" {
		t.Errorf("session id: %q", got.SessionID)
	}
	if got.Model != "claude-opus-4-7" {
		t.Errorf("model: %q", got.Model)
	}
	if got.APIKeySource != "none" {
		t.Errorf("api key source: %q", got.APIKeySource)
	}
	if got.UsingAPIKey() {
		t.Error("apiKeySource='none' must NOT be flagged as API key")
	}
	if !got.IsAgentic {
		t.Error("AGENT MODE sessions are always agentic")
	}
	// completedTurns is monotonic; we take the max (3).
	if got.TurnCount != 3 {
		t.Errorf("turn count: %d", got.TurnCount)
	}
	want := Tokens{
		Input:      2000 + 2500 + 3000,
		Output:     400 + 500 + 600,
		CacheRead:  1000 + 1500 + 2000,
		CacheWrite: 100,
	}
	if got.Tokens != want {
		t.Errorf("tokens: got %+v want %+v", got.Tokens, want)
	}
	wantFiles := []string{"/repo/x.go", "/repo/y.go"}
	if len(got.FilesTouched) != 2 || got.FilesTouched[0] != wantFiles[0] || got.FilesTouched[1] != wantFiles[1] {
		t.Errorf("files_touched: %v", got.FilesTouched)
	}
	// Time window — earliest init, latest turn.
	wantStart := time.Date(2026, 6, 4, 11, 0, 0, 0, time.UTC)
	wantEnd := time.Date(2026, 6, 4, 11, 1, 0, 0, time.UTC)
	if !got.StartedAt.Equal(wantStart) {
		t.Errorf("started_at: %v", got.StartedAt)
	}
	if !got.EndedAt.Equal(wantEnd) {
		t.Errorf("ended_at: %v", got.EndedAt)
	}
}

func TestUsingAPIKey_TrueWhenSourceIsNotNone(t *testing.T) {
	path := filepath.Join(
		"..", "..", "..", "testdata", "claudecode_agentmode", "audit-api-key.jsonl",
	)
	got, err := ReadFile(path)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if !got.UsingAPIKey() {
		t.Errorf("apiKeySource=%q should flag as API key", got.APIKeySource)
	}
}

func TestReadFile_MissingFile(t *testing.T) {
	_, err := ReadFile(filepath.Join(t.TempDir(), "nope.jsonl"))
	if err == nil {
		t.Error("expected error on missing file")
	}
}
