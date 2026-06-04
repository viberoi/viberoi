// Package claudecode reads Claude Code CLI session JSONL files.
//
// Reads two artifacts from one CLI session directory:
//   1. session.jsonl — the main conversation (per-turn tokens, tool_use).
//   2. subagents/agent-*.jsonl — per-subagent token series. Summed into
//      the parent session so cost reflects total work, not just the
//      orchestrator's portion.
//
// File layout (verified by reading real session files; see
// `frontend/_design/VibeROI-DataSource-Master-final.md` TOOL #1):
//
//   %APPDATA%\Claude\local-cli-sessions\<account>\<group>\<cliSessionId>\
//     session.jsonl
//     subagents\
//       agent-<id>.jsonl
//       agent-<id>.meta.json   (skipped — non-JSONL sidecar)
//
// Each .jsonl line is a JSON object. We only depend on a few fields and
// ignore everything else — Claude Code adds fields between releases,
// and a strict parser would break on every minor update.
//
// AGENT MODE (Cowork / agentic) sessions live elsewhere
// (local-agent-mode-sessions/) and are handled by the sibling
// `claudecode_agentmode` package.
package claudecode

import (
	"bufio"
	"encoding/json"
	"errors"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// FileSession is the parsed result of one CLI session — main file
// plus all its subagent files folded in.
type FileSession struct {
	SessionID     string
	Model         string
	StartedAt     time.Time
	EndedAt       time.Time
	Tokens        Tokens
	TurnCount     int
	SubagentCount int
	FilesTouched  []string // unique, sorted, real paths only
	IsAgentic     bool
}

// Tokens holds the four token series Claude Code records per turn.
// We sum across every assistant turn — main session + every subagent.
type Tokens struct {
	Input      int
	Output     int
	CacheRead  int
	CacheWrite int
}

// rawTurn is the minimal subset of the on-wire shape we depend on.
// Both session.jsonl and agent-*.jsonl use this shape.
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

// ReadFile parses a session.jsonl file at `path` AND every sibling
// `subagents/agent-*.jsonl`. Subagent tokens + files_touched are
// summed into the returned FileSession.
//
// Returns an error if the main file is missing or unreadable.
// Subagent files that fail to parse are logged-and-skipped (caller
// won't see them, but main session won't fail).
func ReadFile(path string) (*FileSession, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	out, err := readMain(f)
	_ = f.Close()
	if err != nil {
		return nil, err
	}

	// Fold in subagents from a sibling subagents/ directory.
	subagentDir := filepath.Join(filepath.Dir(path), "subagents")
	if entries, err := os.ReadDir(subagentDir); err == nil {
		for _, e := range entries {
			if e.IsDir() {
				continue
			}
			name := e.Name()
			if !strings.HasPrefix(name, "agent-") || !strings.HasSuffix(name, ".jsonl") {
				continue
			}
			subPath := filepath.Join(subagentDir, name)
			subFile, err := os.Open(subPath)
			if err != nil {
				continue // unreadable subagent shouldn't kill the main session
			}
			sub, err := readMain(subFile)
			_ = subFile.Close()
			if err != nil {
				continue
			}
			mergeSubagent(out, sub)
		}
	} else if !errors.Is(err, fs.ErrNotExist) {
		// Real failure reading the subagents/ dir other than not-found.
		// Keep the main session result; surface as a no-op (subagents
		// just won't be aggregated this run).
	}
	return out, nil
}

// readMain parses one JSONL stream. Used for both session.jsonl and
// every subagents/agent-*.jsonl — the format is identical.
func readMain(r io.Reader) (*FileSession, error) {
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

// mergeSubagent folds a subagent's totals into the parent session.
// Tokens + files_touched aggregate; turn count adds the subagent's
// assistant turns; the time window extends if the subagent's range
// reaches beyond the main session's.
func mergeSubagent(main, sub *FileSession) {
	main.SubagentCount++
	main.Tokens.Input += sub.Tokens.Input
	main.Tokens.Output += sub.Tokens.Output
	main.Tokens.CacheRead += sub.Tokens.CacheRead
	main.Tokens.CacheWrite += sub.Tokens.CacheWrite
	main.TurnCount += sub.TurnCount
	if sub.IsAgentic {
		main.IsAgentic = true
	}
	// Extend time window if the subagent ran beyond the main session.
	if !sub.StartedAt.IsZero() && (main.StartedAt.IsZero() || sub.StartedAt.Before(main.StartedAt)) {
		main.StartedAt = sub.StartedAt
	}
	if sub.EndedAt.After(main.EndedAt) {
		main.EndedAt = sub.EndedAt
	}
	// Merge files_touched — preserve sort order.
	existing := map[string]struct{}{}
	for _, f := range main.FilesTouched {
		existing[f] = struct{}{}
	}
	for _, f := range sub.FilesTouched {
		existing[f] = struct{}{}
	}
	main.FilesTouched = sortedKeys(existing)
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
