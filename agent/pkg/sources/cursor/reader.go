// Package cursor reads Cursor IDE local state.
//
// Cursor stores everything in one SQLite file at
//   %APPDATA%\Cursor\User\globalStorage\state.vscdb
//
// Two tables matter for us:
//
//   cursorDiskKV  — composers (conversation headers) + per-message bubbles
//                  key = composerData:<composerId>     → JSON header
//                  key = bubbleId:<composerId>:<bubbleId> → JSON message
//
//   ItemTable      — aiCodeTrackingLines (AI-code→commit map; deferred to
//                  V3 — currently the runner uses git diff for LOC).
//
// One Cursor SQLite file produces N sessions — one per composer. The
// reader returns them all and the runner enumerates each.
//
// V1 scope notes (deferred to V2):
//   * Reconcile against Cursor's usage/billing API via usageUuid.
//   * aiCodeTrackingLines for AI-code→commit attribution.
//   * Cline (saoudrizwan.claude-dev) overlap dedup.
package cursor

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"sort"
	"strings"
	"time"

	_ "modernc.org/sqlite" // pure-Go driver — no CGO
)

// CursorSession is one conversation (composer) with its messages folded in.
type CursorSession struct {
	ComposerID    string
	Mode          string // "agent" | "chat" | "edit" — composer's unifiedMode/forceMode
	IsAgentic     bool
	Model         string
	StartedAt     time.Time
	EndedAt       time.Time
	Tokens        Tokens
	TurnCount     int    // count of bubbles with > 0 tokens (assistant generations)
	FilesTouched  []string
	IsRefunded    bool   // any bubble in the conversation was refunded
	BubbleCount   int    // total bubbles, including tool-only (0-token) ones
}

// Tokens — same shape as the Claude Code reader's, for envelope parity.
type Tokens struct {
	Input      int
	Output     int
	CacheRead  int // Cursor doesn't expose cache_read / cache_write; left at 0
	CacheWrite int
}

// ── On-wire shapes ──────────────────────────────────────────────────────────
// Permissive: anything we don't depend on is ignored. Cursor adds fields
// freely between releases.

type rawComposer struct {
	ComposerID  string `json:"composerId"`
	CreatedAt   int64  `json:"createdAt"` // milliseconds since epoch
	UnifiedMode string `json:"unifiedMode,omitempty"`
	ForceMode   string `json:"forceMode,omitempty"`
	IsAgentic   *bool  `json:"isAgentic,omitempty"`

	// model is occasionally on the composer; if not, we fall back to the
	// first non-empty model we see on a bubble.
	Model string `json:"model,omitempty"`
}

type rawBubble struct {
	BubbleID   string `json:"bubbleId,omitempty"`
	ComposerID string `json:"composerId,omitempty"`

	// Bubble timing — `createdAt` ms since epoch when present.
	CreatedAt int64 `json:"createdAt,omitempty"`

	TokenCount *struct {
		InputTokens  int `json:"inputTokens"`
		OutputTokens int `json:"outputTokens"`
	} `json:"tokenCount,omitempty"`

	Model      string `json:"model,omitempty"`
	IsRefunded bool   `json:"isRefunded,omitempty"`
	IsAgentic  bool   `json:"isAgentic,omitempty"`

	// Tool calls — each one may carry a file_path or path argument.
	// `toolFormerData` is the documented field name; older releases use
	// `tools` array. We read both, tolerantly.
	ToolFormerData *toolCall   `json:"toolFormerData,omitempty"`
	Tools          []toolCall  `json:"tools,omitempty"`
}

type toolCall struct {
	Name string `json:"name,omitempty"`
	Args *struct {
		// Cursor variants — accept any of these as the path arg.
		FilePath string `json:"file_path,omitempty"`
		Path     string `json:"path,omitempty"`
		Target   string `json:"target,omitempty"`
	} `json:"args,omitempty"`
}

func (tc *toolCall) path() string {
	if tc == nil || tc.Args == nil {
		return ""
	}
	if tc.Args.FilePath != "" {
		return tc.Args.FilePath
	}
	if tc.Args.Path != "" {
		return tc.Args.Path
	}
	return tc.Args.Target
}

// ReadAllSessions opens the Cursor SQLite at `path`, enumerates every
// composer, folds in its bubbles, returns one CursorSession per composer.
//
// Composers with zero token activity AND zero file touches are skipped
// — Cursor creates empty composers on UI tab-open that have no work to
// report and would spam the Ingest pipeline.
func ReadAllSessions(path string) ([]CursorSession, error) {
	if _, err := os.Stat(path); err != nil {
		return nil, fmt.Errorf("cursor: stat db: %w", err)
	}

	// Open read-only (?mode=ro) so we never write to the user's live IDE state.
	db, err := sql.Open("sqlite", "file:"+path+"?mode=ro&immutable=1")
	if err != nil {
		return nil, fmt.Errorf("cursor: open db: %w", err)
	}
	defer db.Close()

	composers, err := readComposers(db)
	if err != nil {
		return nil, err
	}

	out := make([]CursorSession, 0, len(composers))
	for _, comp := range composers {
		session, err := buildSession(db, comp)
		if err != nil {
			// One bad composer shouldn't kill the whole read.
			continue
		}
		if session.Tokens.Input == 0 && session.Tokens.Output == 0 &&
			len(session.FilesTouched) == 0 {
			continue
		}
		out = append(out, *session)
	}
	return out, nil
}

func readComposers(db *sql.DB) ([]rawComposer, error) {
	rows, err := db.Query(
		`SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%'`,
	)
	if err != nil {
		return nil, fmt.Errorf("cursor: query composers: %w", err)
	}
	defer rows.Close()

	var out []rawComposer
	for rows.Next() {
		var key string
		var value []byte
		if err := rows.Scan(&key, &value); err != nil {
			continue
		}
		var c rawComposer
		if err := json.Unmarshal(value, &c); err != nil {
			continue // skip malformed entries
		}
		if c.ComposerID == "" {
			c.ComposerID = strings.TrimPrefix(key, "composerData:")
		}
		if c.ComposerID == "" {
			continue
		}
		out = append(out, c)
	}
	return out, rows.Err()
}

func buildSession(db *sql.DB, comp rawComposer) (*CursorSession, error) {
	prefix := "bubbleId:" + comp.ComposerID + ":"
	rows, err := db.Query(
		`SELECT value FROM cursorDiskKV WHERE key LIKE ?`,
		prefix+"%",
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	files := map[string]struct{}{}
	session := &CursorSession{
		ComposerID: comp.ComposerID,
		Mode:       resolveMode(comp),
		Model:      comp.Model,
		StartedAt:  msToTime(comp.CreatedAt),
		EndedAt:    msToTime(comp.CreatedAt),
	}
	if comp.IsAgentic != nil {
		session.IsAgentic = *comp.IsAgentic
	}

	for rows.Next() {
		var value []byte
		if err := rows.Scan(&value); err != nil {
			continue
		}
		var b rawBubble
		if err := json.Unmarshal(value, &b); err != nil {
			continue
		}
		session.BubbleCount++
		if b.IsRefunded {
			session.IsRefunded = true
			// Don't count refunded bubble's tokens toward the cost figure.
			continue
		}
		if b.IsAgentic {
			session.IsAgentic = true
		}
		if session.Model == "" && b.Model != "" {
			session.Model = b.Model
		}
		if t := b.TokenCount; t != nil {
			if t.InputTokens > 0 || t.OutputTokens > 0 {
				session.TurnCount++
			}
			session.Tokens.Input += t.InputTokens
			session.Tokens.Output += t.OutputTokens
		}
		// Tool calls — read both shapes.
		if p := b.ToolFormerData.path(); p != "" {
			files[p] = struct{}{}
			session.IsAgentic = true
		}
		for i := range b.Tools {
			if p := b.Tools[i].path(); p != "" {
				files[p] = struct{}{}
				session.IsAgentic = true
			}
		}
		// Time window — Cursor's per-bubble timestamps extend the
		// session's range past the composer's createdAt.
		if b.CreatedAt > 0 {
			ts := msToTime(b.CreatedAt)
			if session.StartedAt.IsZero() || ts.Before(session.StartedAt) {
				session.StartedAt = ts
			}
			if ts.After(session.EndedAt) {
				session.EndedAt = ts
			}
		}
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	session.FilesTouched = sortedKeys(files)
	return session, nil
}

// resolveMode picks the most specific mode signal Cursor exposes:
// unifiedMode (newer releases) → forceMode (older).
func resolveMode(c rawComposer) string {
	if c.UnifiedMode != "" {
		return c.UnifiedMode
	}
	if c.ForceMode != "" {
		return c.ForceMode
	}
	return "chat" // safe default
}

func msToTime(ms int64) time.Time {
	if ms <= 0 {
		return time.Time{}
	}
	return time.UnixMilli(ms).UTC()
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

// ErrNoDB is returned by callers that want to surface a missing DB
// distinctly from other errors. Currently ReadAllSessions returns a
// wrapped fs error; clients can use errors.Is(err, ErrNoDB) by
// checking os.IsNotExist on the wrapped error.
var ErrNoDB = errors.New("cursor: state.vscdb not found")
