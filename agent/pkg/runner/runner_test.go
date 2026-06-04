package runner

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/viberoi/viberoi/agent/pkg/config"
	"github.com/viberoi/viberoi/agent/pkg/state"
)

// fixturePath copies the canonical claudecode fixture into a per-test
// `<tmp>/<account>/<group>/<id>/session.jsonl` layout — close to the
// real Claude Code on-disk tree.
func fixturePath(t *testing.T) string {
	t.Helper()
	src := filepath.Join("..", "..", "testdata", "claudecode", "session.jsonl")
	data, err := os.ReadFile(src)
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}
	root := t.TempDir()
	dst := filepath.Join(root, "acct", "grp", "id-1", "session.jsonl")
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := os.WriteFile(dst, data, 0o644); err != nil {
		t.Fatalf("write: %v", err)
	}
	return root
}

func newRunner(t *testing.T, statePath, claudePath, ingestURL string) *Runner {
	t.Helper()
	cfg := &config.Config{
		OrgID:          "00000000-0000-0000-0000-000000000001",
		DeveloperID:    "00000000-0000-0000-0000-000000000101",
		Token:          "tok-test",
		IngestURL:      ingestURL,
		PollIntervalS:  60,
		ClaudeCodePath: claudePath,
	}
	if err := cfg.Validate(); err != nil {
		t.Fatalf("validate: %v", err)
	}
	st, err := state.Open(statePath)
	if err != nil {
		t.Fatalf("state: %v", err)
	}
	r := New(cfg, st)
	r.Logger = func(string, ...any) {} // silence in tests
	return r
}

func TestRun_PushesUnseenSessions(t *testing.T) {
	root := fixturePath(t)
	statePath := filepath.Join(t.TempDir(), "state.json")

	var seen atomic.Int32
	var seenBody []byte
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen.Add(1)
		seenBody, _ = io.ReadAll(r.Body)
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()

	r := newRunner(t, statePath, root, srv.URL)
	r.Client.HTTP = srv.Client()

	res, err := r.Run(context.Background())
	if err != nil {
		t.Fatalf("run: %v", err)
	}
	if res.Pushed != 1 || res.Skipped != 0 || res.Failed != 0 || res.Discovered != 1 {
		t.Errorf("result: %+v", res)
	}
	if seen.Load() != 1 {
		t.Errorf("expected 1 HTTP hit, got %d", seen.Load())
	}
	// Spot-check the wire envelope.
	if !strings.Contains(string(seenBody), `"session_id":"sess-fixture-1"`) {
		t.Errorf("body missing session_id: %s", seenBody)
	}
}

func TestRun_SkipsAlreadyUploaded(t *testing.T) {
	root := fixturePath(t)
	statePath := filepath.Join(t.TempDir(), "state.json")
	var seen atomic.Int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen.Add(1)
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()

	r := newRunner(t, statePath, root, srv.URL)
	r.Client.HTTP = srv.Client()

	if _, err := r.Run(context.Background()); err != nil {
		t.Fatalf("first run: %v", err)
	}
	// Re-run should skip the same session.
	res, err := r.Run(context.Background())
	if err != nil {
		t.Fatalf("second run: %v", err)
	}
	if res.Skipped != 1 || res.Pushed != 0 {
		t.Errorf("expected skipped=1 pushed=0, got %+v", res)
	}
	if seen.Load() != 1 {
		t.Errorf("expected only 1 HTTP hit across two runs, got %d", seen.Load())
	}
}

func TestRun_ReturnsErrAuthOn401(t *testing.T) {
	root := fixturePath(t)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
	}))
	defer srv.Close()
	r := newRunner(t, filepath.Join(t.TempDir(), "s.json"), root, srv.URL)
	r.Client.HTTP = srv.Client()
	if _, err := r.Run(context.Background()); err == nil {
		t.Error("expected auth error")
	}
}

func TestRun_HandlesMissingClaudePath(t *testing.T) {
	statePath := filepath.Join(t.TempDir(), "s.json")
	r := newRunner(t, statePath, filepath.Join(t.TempDir(), "does-not-exist"), "http://x")
	res, err := r.Run(context.Background())
	if err != nil {
		t.Fatalf("missing dir should not error: %v", err)
	}
	if res.Discovered != 0 {
		t.Errorf("expected 0 discoveries, got %+v", res)
	}
}

// ── AGENT MODE + landmine ────────────────────────────────────────────────

func agentModeFixture(t *testing.T) string {
	t.Helper()
	src := filepath.Join("..", "..", "testdata", "claudecode_agentmode", "audit.jsonl")
	data, err := os.ReadFile(src)
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}
	root := t.TempDir()
	dst := filepath.Join(root, "acct", "grp", "local_id-1", "audit.jsonl")
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := os.WriteFile(dst, data, 0o644); err != nil {
		t.Fatalf("write: %v", err)
	}
	return root
}

func TestRun_PushesAgentModeSessions(t *testing.T) {
	cliRoot := fixturePath(t)
	agentModeRoot := agentModeFixture(t)
	statePath := filepath.Join(t.TempDir(), "state.json")

	var seen atomic.Int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen.Add(1)
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()

	r := newRunner(t, statePath, cliRoot, srv.URL)
	r.Cfg.ClaudeCodeAgentModePath = agentModeRoot
	r.Client.HTTP = srv.Client()

	res, err := r.Run(context.Background())
	if err != nil {
		t.Fatalf("run: %v", err)
	}
	// 1 CLI + 1 agent-mode = 2 sessions pushed.
	if res.Pushed != 2 || res.Discovered != 2 {
		t.Errorf("result: %+v", res)
	}
	if seen.Load() != 2 {
		t.Errorf("expected 2 HTTP hits, got %d", seen.Load())
	}
}

func TestBuildAgentModeSession_AgenticAndModelPropagated(t *testing.T) {
	root := agentModeFixture(t)
	r := newRunner(t, filepath.Join(t.TempDir(), "s.json"), root, "http://x")
	files, err := discoverAgentModeAuditFiles(root)
	if err != nil || len(files) != 1 {
		t.Fatalf("discover: %v %v", files, err)
	}
	r.Now = func() time.Time { return time.Date(2026, 6, 4, 11, 2, 0, 0, time.UTC) }
	s, err := r.buildAgentModeSession(context.Background(), files[0])
	if err != nil {
		t.Fatalf("build: %v", err)
	}
	if !s.Activity.IsAgentic || s.Activity.Mode != "agent" {
		t.Errorf("AGENT MODE must always be agentic+agent: %+v", s.Activity)
	}
	if s.Tool.Model != "claude-opus-4-7" {
		t.Errorf("model not propagated: %s", s.Tool.Model)
	}
	if s.Tool.PricingModel.Type != "subscription" {
		t.Errorf("apiKeySource=none should map to subscription: %s", s.Tool.PricingModel.Type)
	}
}

func TestBuildAgentModeSession_APIKeyFlipsPricing(t *testing.T) {
	src := filepath.Join("..", "..", "testdata", "claudecode_agentmode", "audit-api-key.jsonl")
	data, err := os.ReadFile(src)
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}
	root := t.TempDir()
	dst := filepath.Join(root, "acct", "grp", "local_id-1", "audit.jsonl")
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := os.WriteFile(dst, data, 0o644); err != nil {
		t.Fatalf("write: %v", err)
	}

	r := newRunner(t, filepath.Join(t.TempDir(), "s.json"), root, "http://x")
	files, _ := discoverAgentModeAuditFiles(root)
	s, err := r.buildAgentModeSession(context.Background(), files[0])
	if err != nil {
		t.Fatalf("build: %v", err)
	}
	if s.Tool.PricingModel.Type != "api_key" {
		t.Errorf(
			"apiKeySource=environment should flip pricing to api_key, got %s",
			s.Tool.PricingModel.Type,
		)
	}
}

func TestBuildCLISession_EnvVarLandminFlipsPricing(t *testing.T) {
	root := fixturePath(t)
	r := newRunner(t, filepath.Join(t.TempDir(), "s.json"), root, "http://x")
	files, _ := discoverCLISessionFiles(root)

	t.Setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
	s, err := r.buildCLISession(context.Background(), files[0])
	if err != nil {
		t.Fatalf("build: %v", err)
	}
	if s.Tool.PricingModel.Type != "api_key" {
		t.Errorf("env-var ANTHROPIC_API_KEY should flip pricing to api_key, got %s", s.Tool.PricingModel.Type)
	}
}

func TestBuildSession_Envelope(t *testing.T) {
	root := fixturePath(t)
	statePath := filepath.Join(t.TempDir(), "s.json")
	r := newRunner(t, statePath, root, "http://x")
	files, err := discoverCLISessionFiles(root)
	if err != nil || len(files) != 1 {
		t.Fatalf("discover: %v %v", files, err)
	}
	r.Now = func() time.Time { return time.Date(2026, 6, 3, 13, 0, 0, 0, time.UTC) }
	s, err := r.buildCLISession(context.Background(), files[0])
	if err != nil {
		t.Fatalf("build: %v", err)
	}
	if s.Meta.SchemaVersion != "1.0" {
		t.Errorf("schema_version: %s", s.Meta.SchemaVersion)
	}
	if !s.Activity.IsAgentic || s.Activity.Mode != "agent" {
		t.Errorf("agentic flag/mode: %+v", s.Activity)
	}
	if s.Tokens.Input != 6600 {
		t.Errorf("token sum: %d", s.Tokens.Input)
	}
	raw, _ := json.Marshal(s)
	for _, want := range []string{`"session_id":"sess-fixture-1"`, `"schema_version":"1.0"`, `"files_touched_count":2`} {
		if !strings.Contains(string(raw), want) {
			t.Errorf("envelope missing %s", want)
		}
	}
}
