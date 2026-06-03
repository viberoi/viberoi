// Package state tracks which sessions we've already uploaded.
//
// One file per agent install: `state.json` in the config dir. Per
// (tool, session_id) we record `uploaded_at`. The runner consults
// this before POSTing; if a session_id is present, it's skipped.
//
// The file is rewritten atomically (write to .tmp + rename) so a
// crash mid-write can't leave it corrupted.
package state

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// State is the on-disk shape.
type State struct {
	Uploaded map[string]Entry `json:"uploaded"` // key = tool + ":" + session_id
}

type Entry struct {
	Tool       string    `json:"tool"`
	SessionID  string    `json:"session_id"`
	UploadedAt time.Time `json:"uploaded_at"`
}

// Store is a goroutine-safe handle around the state file.
type Store struct {
	path string
	mu   sync.Mutex
	data *State
}

// Open loads state from `path`. Missing file → empty state (not an error).
func Open(path string) (*Store, error) {
	s := &Store{path: path, data: &State{Uploaded: map[string]Entry{}}}
	raw, err := os.ReadFile(path)
	if errors.Is(err, fs.ErrNotExist) {
		return s, nil
	}
	if err != nil {
		return nil, err
	}
	var parsed State
	if err := json.Unmarshal(raw, &parsed); err != nil {
		return nil, fmt.Errorf("state file invalid: %w", err)
	}
	if parsed.Uploaded == nil {
		parsed.Uploaded = map[string]Entry{}
	}
	s.data = &parsed
	return s, nil
}

// Has returns true if (tool, sessionID) was already uploaded.
func (s *Store) Has(tool, sessionID string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	_, ok := s.data.Uploaded[key(tool, sessionID)]
	return ok
}

// Mark records (tool, sessionID) as uploaded now, then flushes to disk.
func (s *Store) Mark(tool, sessionID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.data.Uploaded[key(tool, sessionID)] = Entry{
		Tool:       tool,
		SessionID:  sessionID,
		UploadedAt: time.Now().UTC(),
	}
	return s.flushLocked()
}

func (s *Store) flushLocked() error {
	if err := os.MkdirAll(filepath.Dir(s.path), 0o700); err != nil {
		return err
	}
	raw, err := json.MarshalIndent(s.data, "", "  ")
	if err != nil {
		return err
	}
	tmp := s.path + ".tmp"
	if err := os.WriteFile(tmp, raw, 0o600); err != nil {
		return err
	}
	return os.Rename(tmp, s.path)
}

func key(tool, sessionID string) string {
	return tool + ":" + sessionID
}
