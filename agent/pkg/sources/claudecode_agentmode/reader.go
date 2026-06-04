// Package claudecode_agentmode reads Claude Code AGENT MODE
// (Cowork / agentic) session audit logs.
//
// File layout (verified by reading real session files; see
// `frontend/_design/VibeROI-DataSource-Master-final.md` TOOL #1):
//
//   %APPDATA%\Claude\local-agent-mode-sessions\<account>\<group>\local_<id>\
//     audit.jsonl
//
// Audit lines are HMAC-signed event records — we don't verify the
// signature (that's Anthropic's internal integrity check, not ours).
// We just read the events we care about:
//
//   - `init` event — carries `apiKeySource` (subscription vs API key),
//     model, tool list, account info.
//   - `turn.complete` event — carries per-turn token usage and
//     `completedTurns`.
//   - `tool.use` event — carries file paths touched.
//
// AGENT MODE sessions are always `is_agentic = true` and capture mode
// `local_exact`.

package claudecode_agentmode

import (
	"bufio"
	"encoding/json"
	"errors"
	"io"
	"os"
	"sort"
	"strings"
	"time"
)

// AuditSession is the parsed result of one audit.jsonl file.
type AuditSession struct {
	SessionID     string
	Model         string
	StartedAt     time.Time
	EndedAt       time.Time
	Tokens        Tokens
	TurnCount     int
	FilesTouched  []string
	IsAgentic     bool   // always true for AGENT MODE
	APIKeySource  string // "none" = subscription; anything else = API key
}

// Tokens — same shape as the CLI reader.
type Tokens struct {
	Input      int
	Output     int
	CacheRead  int
	CacheWrite int
}

// rawEvent — minimal shape we care about. Audit lines carry an HMAC
// signature we ignore; the event payload is what matters.
type rawEvent struct {
	Type      string    `json:"type"`
	Timestamp time.Time `json:"timestamp"`

	// init event
	Init *struct {
		SessionID    string   `json:"session_id"`
		APIKeySource string   `json:"apiKeySource"`
		Model        string   `json:"model"`
		Tools        []string `json:"tools"`
		Account      string   `json:"account"`
	} `json:"init,omitempty"`

	// turn.complete event
	Turn *struct {
		CompletedTurns int `json:"completedTurns"`
		Usage          *struct {
			InputTokens         int `json:"input_tokens"`
			OutputTokens        int `json:"output_tokens"`
			CacheReadTokens     int `json:"cache_read_input_tokens"`
			CacheCreationTokens int `json:"cache_creation_input_tokens"`
		} `json:"usage,omitempty"`
	} `json:"turn,omitempty"`

	// tool.use event
	ToolUse *struct {
		Name  string `json:"name"`
		Input *struct {
			FilePath string `json:"file_path,omitempty"`
		} `json:"input,omitempty"`
	} `json:"tool_use,omitempty"`
}

// ReadFile parses one audit.jsonl.
func ReadFile(path string) (*AuditSession, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return readFromReader(f)
}

func readFromReader(r io.Reader) (*AuditSession, error) {
	files := map[string]struct{}{}
	out := &AuditSession{IsAgentic: true}
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var ev rawEvent
		if err := json.Unmarshal(line, &ev); err != nil {
			// Malformed line — skip; don't kill the parse.
			continue
		}
		if !ev.Timestamp.IsZero() {
			if out.StartedAt.IsZero() || ev.Timestamp.Before(out.StartedAt) {
				out.StartedAt = ev.Timestamp
			}
			if ev.Timestamp.After(out.EndedAt) {
				out.EndedAt = ev.Timestamp
			}
		}
		switch ev.Type {
		case "init":
			if ev.Init != nil {
				if out.SessionID == "" {
					out.SessionID = ev.Init.SessionID
				}
				if out.Model == "" {
					out.Model = ev.Init.Model
				}
				if out.APIKeySource == "" {
					out.APIKeySource = ev.Init.APIKeySource
				}
			}
		case "turn.complete":
			if ev.Turn != nil {
				if ev.Turn.CompletedTurns > out.TurnCount {
					out.TurnCount = ev.Turn.CompletedTurns
				}
				if u := ev.Turn.Usage; u != nil {
					out.Tokens.Input += u.InputTokens
					out.Tokens.Output += u.OutputTokens
					out.Tokens.CacheRead += u.CacheReadTokens
					out.Tokens.CacheWrite += u.CacheCreationTokens
				}
			}
		case "tool.use":
			if ev.ToolUse != nil && ev.ToolUse.Input != nil && ev.ToolUse.Input.FilePath != "" {
				files[ev.ToolUse.Input.FilePath] = struct{}{}
			}
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	if out.SessionID == "" {
		return nil, errors.New("claudecode_agentmode: no init event found")
	}
	out.FilesTouched = sortedKeys(files)
	return out, nil
}

// UsingAPIKey reports whether this session was billed via API key
// (rather than the Pro/Team subscription). True when `apiKeySource`
// is anything other than the literal string "none".
func (a *AuditSession) UsingAPIKey() bool {
	return a.APIKeySource != "" && a.APIKeySource != "none"
}

func sortedKeys(m map[string]struct{}) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		if strings.TrimSpace(k) == "" {
			continue
		}
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}
