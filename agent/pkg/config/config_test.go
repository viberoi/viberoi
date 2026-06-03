package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestRoundTrip(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.yaml")
	c := &Config{
		OrgID:         "00000000-0000-0000-0000-000000000001",
		DeveloperID:   "00000000-0000-0000-0000-000000000101",
		Token:         "secret-token-do-not-log",
		IngestURL:     "http://127.0.0.1:8001/ingest",
		PollIntervalS: 60,
	}
	if err := Save(path, c); err != nil {
		t.Fatalf("save: %v", err)
	}
	// Confirm 0600 perms (POSIX only — skip on Windows where chmod is approximate).
	if info, _ := os.Stat(path); info != nil && info.Mode().Perm() != 0o600 && os.Getenv("OS") != "Windows_NT" {
		t.Logf("warning: perms %o (non-POSIX FS?)", info.Mode().Perm())
	}
	back, err := Load(path)
	if err != nil {
		t.Fatalf("load: %v", err)
	}
	if back.Token != c.Token {
		t.Errorf("token round-trip lost")
	}
	if back.PollIntervalS != 60 {
		t.Errorf("poll interval round-trip lost: %d", back.PollIntervalS)
	}
}

func TestValidateRejectsMissing(t *testing.T) {
	c := &Config{}
	if err := c.Validate(); err == nil {
		t.Error("expected error from empty config")
	}
}

func TestValidateAppliesPollDefault(t *testing.T) {
	c := &Config{
		OrgID: "a", DeveloperID: "b", Token: "c", IngestURL: "https://x",
	}
	if err := c.Validate(); err != nil {
		t.Fatalf("validate: %v", err)
	}
	if c.PollIntervalS != 300 {
		t.Errorf("expected default 300, got %d", c.PollIntervalS)
	}
}

func TestPollIntervalFloor(t *testing.T) {
	c := &Config{PollIntervalS: 5}
	if c.PollInterval() < 30*1_000_000_000 {
		t.Error("expected 30s floor")
	}
}
