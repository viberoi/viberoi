package copilot

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDiscoverEmptyRoot(t *testing.T) {
	files, err := Discover("")
	if err != nil {
		t.Fatalf("Discover empty: %v", err)
	}
	if files != nil {
		t.Fatalf("Discover empty: expected nil, got %v", files)
	}
}

func TestDiscoverNonExistentRoot(t *testing.T) {
	files, err := Discover(filepath.Join(os.TempDir(), "does-not-exist-xyz"))
	if err != nil {
		t.Fatalf("Discover missing: %v", err)
	}
	if files != nil {
		t.Fatalf("Discover missing: expected nil, got %v", files)
	}
}

func TestDiscoverWalksOnlyChatSessions(t *testing.T) {
	root := t.TempDir()
	// Workspace 1 has a chatSessions/session.json — should be picked up.
	ws1 := filepath.Join(root, "ws1", "chatSessions")
	if err := os.MkdirAll(ws1, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(ws1, "s.json"), []byte("{}"), 0o644); err != nil {
		t.Fatal(err)
	}
	// Workspace 2 has an unrelated dir + json — should be ignored.
	ws2 := filepath.Join(root, "ws2", "stateBag")
	if err := os.MkdirAll(ws2, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(ws2, "noise.json"), []byte("{}"), 0o644); err != nil {
		t.Fatal(err)
	}
	files, err := Discover(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(files) != 1 {
		t.Fatalf("expected 1 file, got %d: %v", len(files), files)
	}
}

func TestReadFileSkipsEmptyRequests(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "empty.json")
	body := `{
        "sessionId": "abc",
        "requesterUsername": "alice",
        "creationDate": 1700000000000,
        "lastMessageDate": 1700000000000,
        "requests": []
    }`
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	s, err := ReadFile(path)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if s != nil {
		t.Fatalf("expected nil for empty requests, got %#v", s)
	}
}

func TestReadFileParsesShape(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "real.json")
	body := `{
        "sessionId": "session-42",
        "requesterUsername": "alice",
        "creationDate": 1700000000000,
        "lastMessageDate": 1700000005000,
        "requests": [
            {
                "timestamp": 1700000000000,
                "modelId": "github.copilot-chat/gpt-4.1",
                "agent": { "id": "github.copilot.editsAgent" },
                "variableData": {
                    "variables": [{"name": "src/auth.py", "kind": "file"}]
                }
            },
            {
                "timestamp": 1700000003000,
                "modelId": "github.copilot-chat/claude-sonnet-4-5"
            }
        ]
    }`
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	s, err := ReadFile(path)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if s == nil {
		t.Fatal("expected non-nil session")
	}
	if s.SessionID != "session-42" {
		t.Errorf("sessionID: %q", s.SessionID)
	}
	if s.Username != "alice" {
		t.Errorf("username: %q", s.Username)
	}
	if s.TurnCount != 2 {
		t.Errorf("turn count: %d", s.TurnCount)
	}
	// Last modelId wins.
	if s.Model != "claude-sonnet-4-5" {
		t.Errorf("model: %q", s.Model)
	}
	if s.AgentID != "github.copilot.editsAgent" {
		t.Errorf("agentID: %q", s.AgentID)
	}
	if len(s.FilePaths) != 1 || s.FilePaths[0] != "src/auth.py" {
		t.Errorf("files: %v", s.FilePaths)
	}
}

func TestIsClaudeProxyDedupe(t *testing.T) {
	s := &Session{SessionID: "claude-code:/conversations/abc"}
	if !s.IsClaudeProxy() {
		t.Error("expected claude-code:/ prefix to dedupe")
	}
	s = &Session{SessionID: "regular-uuid"}
	if s.IsClaudeProxy() {
		t.Error("expected regular session not to dedupe")
	}
}
