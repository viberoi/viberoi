// Package claudecode reads Claude Code CLI session JSONL files.
//
// V1 scope — reads the main session.jsonl only:
//   * Sums input/output/cache token counts across every assistant turn.
//   * Counts turn boundaries.
//   * Extracts file paths from tool_use entries (file_path arg) into
//     `files_touched` — paths only, never file contents.
//   * Picks earliest/latest timestamp for the session window.
//
// Deferred to V2 (per design doc):
//   * Subagent aggregation (subagents/agent-*.jsonl)
//   * AGENT MODE audit log
//   * ANTHROPIC_API_KEY landmine detection
//
// File layout (verified by reading real session files; see
// `frontend/_design/VibeROI-DataSource-Master-final.md` TOOL #1):
//   %APPDATA%\Claude\local-cli-sessions\<account>\<group>\<cliSessionId>\session.jsonl
//
// Each line is a JSON object. We only care about a few fields and
// ignore everything else — Claude Code adds fields between releases,
// and a strict parser would break on every minor update.
package claudecode

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

// FileSession is the parsed result of one session.jsonl file.
type FileSession struct {
	SessionID    string
	Model        string
	StartedAt    time.Time
	EndedAt      time.Time
	Tokens       Tokens
	TurnCount    int
	FilesTouched []string // unique, sorted, real paths only
	IsAgentic    bool
}

// Tokens holds the four token series Claude Code records per turn.
// We sum across all assistant turns in the file.
type Tokens struct {
	Input      int
	Output     int
	CacheRead  int
	CacheWrite int
}

// rawTurn is the minimal subset of the on-wire shape we depend on.
// Everything else is ignored — Claude Code adds fields freely between
// versions and a strict decoder would break on every update.
type rawTurn struct {
	Type      string    `json:"type"`
	SessionID string    `json:"session_id"`
	Timestamp time.Time `json:"timestamp"`
	Message   *struct {
		Role  string `json:"role"`
		Model string `json:"model"`
		Usage *struct {
			InputTokens         int `json:"input_tokens"`
			OutputTokens        int `json:"output_tokens"`
			CacheReadTokens     int `json:"cache_read_input_tokens"`
			CacheCreationTokens int `json:"cache_creation_input_tokens"`
		} `json:"usage"`
		Content []struct {
			Type  string `json:"type"`
			Name  string `json:"name,omitempty"`
			Input *struct {
				FilePath string `json:"file_path,omitempty"`
			} `json:"input,omitempty"`
		} `json:"content,omitempty"`
	} `json:"message,omitempty"`
}

// ReadFile parses a session.jsonl file at `path`.
//
// Returns an empty FileSession (with no error) if the file exists but
// contains no parseable turns — that happens when the file is one byte
// long (Claude Code creates the file empty on session start). Caller
// can decide to skip.
//
// Returns an error if the file is missing or unreadable.
func ReadFile(path string) (*FileSession, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return readFromReader(f)
}

func readFromReader(r io.Reader) (*FileSession, error) {
	files := map[string]struct{}{}
	out := &FileSession{}
	scanner := bufio.NewScanner(r)
	// Claude Code JSON lines can be large (long tool outputs we ignore,
	// but they still ride the line). Pre-allocate a generous buffer.
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)
	var turnCount int

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var t rawTurn
		if err := json.Unmarshal(line, &t); err != nil {
			// One malformed line shouldn't kill the whole session.
			continue
		}
		if out.SessionID == "" && t.SessionID != "" {
			out.SessionID = t.SessionID
		}
		if !t.Timestamp.IsZero() {
			if out.StartedAt.IsZero() || t.Timestamp.Before(out.StartedAt) {
				out.StartedAt = t.Timestamp
			}
			if t.Timestamp.After(out.EndedAt) {
				out.EndedAt = t.Timestamp
			}
		}
		if t.Message == nil {
			continue
		}
		if t.Message.Role == "assistant" {
			turnCount++
			if u := t.Message.Usage; u != nil {
				out.Tokens.Input += u.InputTokens
				out.Tokens.Output += u.OutputTokens
				out.Tokens.CacheRead += u.CacheReadTokens
				out.Tokens.CacheWrite += u.CacheCreationTokens
			}
			if out.Model == "" && t.Message.Model != "" {
				out.Model = t.Message.Model
			}
		}
		for _, c := range t.Message.Content {
			if c.Type == "tool_use" {
				// Any tool use marks the session as agentic (running code,
				// reading files, etc. — not pure chat).
				out.IsAgentic = true
				if c.Input != nil && c.Input.FilePath != "" {
					files[c.Input.FilePath] = struct{}{}
				}
			}
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	if out.SessionID == "" {
		return nil, errors.New("claudecode: no session_id found in file")
	}
	out.TurnCount = turnCount
	out.FilesTouched = sortedKeys(files)
	return out, nil
}

func sortedKeys(m map[string]struct{}) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		// Defensive: an unusually shaped tool input could put non-paths in
		// here. Skip empty / whitespace-only entries.
		if strings.TrimSpace(k) == "" {
			continue
		}
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}
