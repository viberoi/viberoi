// Package copilot reads GitHub Copilot chat sessions from VS Code's
// workspaceStorage directory.
//
// Layout (Windows):
//
//	%APPDATA%\Code\User\workspaceStorage\<hash>\chatSessions\<sessionId>.json
//
// One JSON file per chat session. The file contains:
//   - sessionId (UUID), requesterUsername, responderUsername
//   - creationDate, lastMessageDate (epoch ms)
//   - requests[]: per-turn objects with timestamp, modelId
//     (e.g. "github.copilot-chat/gpt-4.1"), agent.id, response[]
//
// Per Master spec § 364-471: token counts are NOT exposed in the
// local file — Copilot keeps them server-side. We emit sessions with
// tokens=0 and let the backend reconciler call the GitHub copilot
// metrics API. The session is flagged is_estimated=true on the
// agent's `tokens` payload until reconciliation runs.
//
// Empty sessions (zero requests) are skipped — they're typically the
// "I have to sign in" stubs VS Code creates on first open.
package copilot

import (
	"encoding/json"
	"errors"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// Session is the parsed result of one Copilot chat session file.
type Session struct {
	SessionID  string
	Username   string
	Model      string // last modelId seen ("gpt-4.1", "claude-sonnet-4-5", etc.)
	CreatedAt  time.Time
	UpdatedAt  time.Time
	TurnCount  int
	AgentID    string   // copilot agent id (e.g. github.copilot.editsAgent)
	IsExternal bool     // when the chat is owned by a non-copilot agent
	FilePaths  []string // attachments referenced in requests (paths only)
}

// rawFile mirrors only the fields we depend on. Unknown fields are
// ignored — Copilot adds + removes shape across VS Code releases and
// we don't want one schema bump to break the reader.
type rawFile struct {
	SessionID         string     `json:"sessionId"`
	RequesterUsername string     `json:"requesterUsername"`
	CreationDate      int64      `json:"creationDate"`     // epoch ms
	LastMessageDate   int64      `json:"lastMessageDate"`  // epoch ms
	Requests          []rawTurn  `json:"requests"`
}

type rawTurn struct {
	Timestamp int64  `json:"timestamp"` // epoch ms
	ModelID   string `json:"modelId"`   // e.g. "github.copilot-chat/gpt-4.1"
	Agent     *struct {
		ID         string `json:"id"`         // e.g. "github.copilot.editsAgent"
		IsExternal bool   `json:"isExternal"` // present on non-copilot agents
		ExtID      *struct {
			Value string `json:"value"`
		} `json:"extensionId,omitempty"`
	} `json:"agent,omitempty"`
	VariableData *struct {
		Variables []rawVar `json:"variables"`
	} `json:"variableData,omitempty"`
}

type rawVar struct {
	// We only pull `name` (file path) when the variable kind is a file
	// reference. Most other fields carry user content we deliberately
	// ignore (privacy: paths OK, content not).
	Name *struct {
		// Sometimes a string, sometimes an object — try both via raw.
	} `json:"-"`
	NameRaw   json.RawMessage `json:"name,omitempty"`
	Kind      string          `json:"kind,omitempty"`
	ModelText string          `json:"modelDescription,omitempty"`
}

// Discover walks `root` (the workspaceStorage dir) and returns every
// chatSession JSON path. Missing root returns (nil, nil) so callers
// can pass an empty CopilotPath as "skip".
func Discover(root string) ([]string, error) {
	if root == "" {
		return nil, nil
	}
	if _, err := os.Stat(root); errors.Is(err, fs.ErrNotExist) {
		return nil, nil
	}
	var out []string
	err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if d.IsDir() {
			return nil
		}
		if filepath.Ext(path) != ".json" {
			return nil
		}
		// VS Code path shape: workspaceStorage/<hash>/chatSessions/<id>.json
		parent := filepath.Base(filepath.Dir(path))
		if parent != "chatSessions" {
			return nil
		}
		out = append(out, path)
		return nil
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// ReadFile parses one chat session JSON file. Empty sessions return
// nil + nil — caller should skip them. Genuine I/O / parse errors
// surface as non-nil err.
func ReadFile(path string) (*Session, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var raw rawFile
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, err
	}
	if len(raw.Requests) == 0 {
		return nil, nil // empty — Copilot stub, skip
	}

	s := &Session{
		SessionID: raw.SessionID,
		Username:  raw.RequesterUsername,
		CreatedAt: msToTime(raw.CreationDate),
		UpdatedAt: msToTime(raw.LastMessageDate),
		TurnCount: len(raw.Requests),
	}

	// Take the last modelId seen — Copilot sometimes switches mid-session;
	// the most recent one is the most representative.
	files := map[string]struct{}{}
	for _, t := range raw.Requests {
		if t.ModelID != "" {
			s.Model = simplifyModelID(t.ModelID)
		}
		if t.Agent != nil {
			s.AgentID = t.Agent.ID
			if t.Agent.IsExternal {
				s.IsExternal = true
			}
		}
		if t.VariableData != nil {
			for _, v := range t.VariableData.Variables {
				if path := variablePath(v); path != "" {
					files[path] = struct{}{}
				}
			}
		}
	}
	for p := range files {
		s.FilePaths = append(s.FilePaths, p)
	}
	return s, nil
}

// IsClaudeProxy returns true for chat sessions whose router prefixes
// the session id with "claude-code:/" — those are Claude Code chats
// surfaced inside VS Code via Copilot's UI shell, not Copilot work.
// Master spec § 460 calls for deduping them to avoid double-counting
// against the Claude Code source.
func (s *Session) IsClaudeProxy() bool {
	return strings.HasPrefix(s.SessionID, "claude-code:/")
}

// simplifyModelID drops Copilot's "github.copilot-chat/" prefix when
// present. Leaves OpenAI/Anthropic identifiers (gpt-4.1, claude-sonnet-...)
// intact so they match the backend's rate-table lookup.
func simplifyModelID(id string) string {
	const prefix = "github.copilot-chat/"
	if strings.HasPrefix(id, prefix) {
		return id[len(prefix):]
	}
	return id
}

func msToTime(ms int64) time.Time {
	if ms <= 0 {
		return time.Time{}
	}
	return time.UnixMilli(ms).UTC()
}

// variablePath extracts a file path from a Copilot variable when the
// variable is a file-attachment reference. We accept the raw `name`
// when it's a plain string (the simplest shape). Object shapes are
// ignored — they're typically code snippets which we don't want.
func variablePath(v rawVar) string {
	if len(v.NameRaw) == 0 {
		return ""
	}
	var s string
	if err := json.Unmarshal(v.NameRaw, &s); err != nil {
		return ""
	}
	// Heuristic: only treat as a file path if it looks like one
	// (has a slash or a dot+ext). Avoids inadvertently picking up
	// free-text variable names.
	if strings.ContainsAny(s, "/\\") || strings.Contains(s, ".") {
		return s
	}
	return ""
}
