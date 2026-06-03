package state

import (
	"path/filepath"
	"testing"
)

func TestEmptyStateOnMissingFile(t *testing.T) {
	s, err := Open(filepath.Join(t.TempDir(), "missing.json"))
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	if s.Has("claude-code", "sess-1") {
		t.Error("expected false on fresh state")
	}
}

func TestMarkAndCheck(t *testing.T) {
	path := filepath.Join(t.TempDir(), "state.json")
	s, _ := Open(path)
	if err := s.Mark("claude-code", "sess-1"); err != nil {
		t.Fatalf("mark: %v", err)
	}
	if !s.Has("claude-code", "sess-1") {
		t.Error("expected Has=true after Mark")
	}
	if s.Has("claude-code", "other") {
		t.Error("expected Has=false for un-marked id")
	}
}

func TestPersistsAcrossReopens(t *testing.T) {
	path := filepath.Join(t.TempDir(), "state.json")
	s1, _ := Open(path)
	_ = s1.Mark("claude-code", "sess-1")
	s2, _ := Open(path)
	if !s2.Has("claude-code", "sess-1") {
		t.Error("state did not persist across reopens")
	}
}

func TestKeyedByToolAndSession(t *testing.T) {
	path := filepath.Join(t.TempDir(), "state.json")
	s, _ := Open(path)
	_ = s.Mark("claude-code", "id-x")
	if s.Has("cursor", "id-x") {
		t.Error("state should be scoped per (tool, id)")
	}
}
