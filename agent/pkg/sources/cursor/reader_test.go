package cursor

import (
	"database/sql"
	"encoding/json"
	"path/filepath"
	"testing"
	"time"

	_ "modernc.org/sqlite"
)

// buildFixtureDB writes a state.vscdb-shaped SQLite file with the given
// composers + bubbles JSON-encoded. Used by every test that needs a
// real Cursor DB to read from.
func buildFixtureDB(t *testing.T, entries map[string]any) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "state.vscdb")
	db, err := sql.Open("sqlite", "file:"+path+"?mode=rwc")
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	defer db.Close()

	if _, err := db.Exec(
		`CREATE TABLE cursorDiskKV (key TEXT PRIMARY KEY, value BLOB)`,
	); err != nil {
		t.Fatalf("create cursorDiskKV: %v", err)
	}

	for k, v := range entries {
		raw, err := json.Marshal(v)
		if err != nil {
			t.Fatalf("marshal %s: %v", k, err)
		}
		if _, err := db.Exec(
			`INSERT INTO cursorDiskKV (key, value) VALUES (?, ?)`,
			k, raw,
		); err != nil {
			t.Fatalf("insert %s: %v", k, err)
		}
	}
	return path
}

// May 28 2026 — used as fixture timestamps in milliseconds.
var (
	t0 = time.Date(2026, 5, 28, 10, 0, 0, 0, time.UTC).UnixMilli()
	t1 = time.Date(2026, 5, 28, 10, 0, 30, 0, time.UTC).UnixMilli()
	t2 = time.Date(2026, 5, 28, 10, 1, 15, 0, time.UTC).UnixMilli()
)

func TestReadAllSessions_HappyPath(t *testing.T) {
	composerID := "comp-1"
	dbPath := buildFixtureDB(t, map[string]any{
		// One composer.
		"composerData:" + composerID: map[string]any{
			"composerId":  composerID,
			"createdAt":   t0,
			"unifiedMode": "agent",
			"isAgentic":   true,
			"model":       "claude-3.7-sonnet",
		},
		// Three bubbles. Bubble 1 = user (no tokens). Bubble 2 + 3 = assistant.
		"bubbleId:" + composerID + ":b1": map[string]any{
			"bubbleId":   "b1",
			"composerId": composerID,
			"createdAt":  t0,
		},
		"bubbleId:" + composerID + ":b2": map[string]any{
			"bubbleId":   "b2",
			"composerId": composerID,
			"createdAt":  t1,
			"tokenCount": map[string]int{"inputTokens": 1200, "outputTokens": 400},
			"toolFormerData": map[string]any{
				"name": "edit_file",
				"args": map[string]string{"file_path": "/repo/a.ts"},
			},
		},
		"bubbleId:" + composerID + ":b3": map[string]any{
			"bubbleId":   "b3",
			"composerId": composerID,
			"createdAt":  t2,
			"tokenCount": map[string]int{"inputTokens": 2000, "outputTokens": 700},
			"tools": []map[string]any{
				{"name": "read_file", "args": map[string]string{"path": "/repo/b.ts"}},
				{"name": "edit_file", "args": map[string]string{"file_path": "/repo/a.ts"}},
			},
		},
	})

	sessions, err := ReadAllSessions(dbPath)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if len(sessions) != 1 {
		t.Fatalf("expected 1 session, got %d", len(sessions))
	}
	s := sessions[0]
	if s.ComposerID != composerID {
		t.Errorf("composer_id: %q", s.ComposerID)
	}
	if s.Mode != "agent" {
		t.Errorf("mode: %q", s.Mode)
	}
	if !s.IsAgentic {
		t.Errorf("isAgentic should be true")
	}
	if s.Model != "claude-3.7-sonnet" {
		t.Errorf("model: %q", s.Model)
	}
	if s.Tokens.Input != 3200 || s.Tokens.Output != 1100 {
		t.Errorf("tokens: %+v", s.Tokens)
	}
	// 2 token-bearing bubbles → turn count 2.
	if s.TurnCount != 2 {
		t.Errorf("turn count: %d", s.TurnCount)
	}
	if s.BubbleCount != 3 {
		t.Errorf("bubble count: %d", s.BubbleCount)
	}
	// Tool calls across both shapes — files dedup'd + sorted.
	want := []string{"/repo/a.ts", "/repo/b.ts"}
	if len(s.FilesTouched) != 2 || s.FilesTouched[0] != want[0] || s.FilesTouched[1] != want[1] {
		t.Errorf("files: %v", s.FilesTouched)
	}
	// EndedAt extended past composer.createdAt by the bubble timestamps.
	if !s.EndedAt.Equal(time.UnixMilli(t2).UTC()) {
		t.Errorf("ended_at: %v", s.EndedAt)
	}
	if s.IsRefunded {
		t.Errorf("no bubble was refunded")
	}
}

func TestReadAllSessions_RefundedBubblesExcludedFromTokens(t *testing.T) {
	dbPath := buildFixtureDB(t, map[string]any{
		"composerData:comp-2": map[string]any{
			"composerId":  "comp-2",
			"createdAt":   t0,
			"unifiedMode": "chat",
		},
		"bubbleId:comp-2:b1": map[string]any{
			"bubbleId":   "b1",
			"tokenCount": map[string]int{"inputTokens": 5000, "outputTokens": 200},
		},
		"bubbleId:comp-2:b2": map[string]any{
			"bubbleId":   "b2",
			"isRefunded": true,
			"tokenCount": map[string]int{"inputTokens": 9999, "outputTokens": 9999},
		},
	})
	sessions, err := ReadAllSessions(dbPath)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if len(sessions) != 1 {
		t.Fatalf("expected 1 session, got %d", len(sessions))
	}
	s := sessions[0]
	if s.Tokens.Input != 5000 || s.Tokens.Output != 200 {
		t.Errorf("refunded tokens leaked into total: %+v", s.Tokens)
	}
	if !s.IsRefunded {
		t.Errorf("session should be flagged as having a refund")
	}
}

func TestReadAllSessions_SkipsEmptyComposers(t *testing.T) {
	dbPath := buildFixtureDB(t, map[string]any{
		// Two composers, only one has activity.
		"composerData:comp-empty": map[string]any{
			"composerId":  "comp-empty",
			"createdAt":   t0,
			"unifiedMode": "chat",
		},
		"composerData:comp-real": map[string]any{
			"composerId":  "comp-real",
			"createdAt":   t0,
			"unifiedMode": "chat",
		},
		"bubbleId:comp-real:b1": map[string]any{
			"bubbleId":   "b1",
			"tokenCount": map[string]int{"inputTokens": 100, "outputTokens": 50},
		},
	})
	sessions, err := ReadAllSessions(dbPath)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if len(sessions) != 1 {
		t.Fatalf("empty composer should be skipped — got %d sessions", len(sessions))
	}
	if sessions[0].ComposerID != "comp-real" {
		t.Errorf("wrong composer surfaced: %s", sessions[0].ComposerID)
	}
}

func TestReadAllSessions_MissingDB(t *testing.T) {
	_, err := ReadAllSessions(filepath.Join(t.TempDir(), "missing.vscdb"))
	if err == nil {
		t.Error("expected error on missing db")
	}
}

func TestReadAllSessions_MultipleComposers(t *testing.T) {
	dbPath := buildFixtureDB(t, map[string]any{
		"composerData:comp-1": map[string]any{
			"composerId": "comp-1", "createdAt": t0, "unifiedMode": "chat",
		},
		"bubbleId:comp-1:b1": map[string]any{
			"tokenCount": map[string]int{"inputTokens": 100, "outputTokens": 50},
		},
		"composerData:comp-2": map[string]any{
			"composerId": "comp-2", "createdAt": t1, "unifiedMode": "agent", "isAgentic": true,
		},
		"bubbleId:comp-2:b1": map[string]any{
			"tokenCount": map[string]int{"inputTokens": 200, "outputTokens": 80},
		},
	})
	sessions, err := ReadAllSessions(dbPath)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if len(sessions) != 2 {
		t.Fatalf("expected 2 sessions, got %d", len(sessions))
	}
	// Per-composer routing — assert each got its own bubble counted.
	byID := map[string]CursorSession{}
	for _, s := range sessions {
		byID[s.ComposerID] = s
	}
	if byID["comp-1"].Tokens.Input != 100 {
		t.Errorf("comp-1 tokens leaked from another composer: %+v", byID["comp-1"].Tokens)
	}
	if byID["comp-2"].Tokens.Input != 200 {
		t.Errorf("comp-2 tokens leaked from another composer: %+v", byID["comp-2"].Tokens)
	}
}

func TestResolveMode(t *testing.T) {
	if got := resolveMode(rawComposer{UnifiedMode: "agent"}); got != "agent" {
		t.Errorf("unifiedMode lost: %s", got)
	}
	if got := resolveMode(rawComposer{ForceMode: "edit"}); got != "edit" {
		t.Errorf("forceMode fallback lost: %s", got)
	}
	if got := resolveMode(rawComposer{}); got != "chat" {
		t.Errorf("default should be chat, got %s", got)
	}
}
