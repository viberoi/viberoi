package ingest

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/viberoi/viberoi/agent/pkg/schema"
)

func sampleSession() schema.Session {
	now := time.Now().UTC()
	return schema.Session{
		SessionID: "sess-1", DeveloperID: "dev", OrgID: "org",
		Tool: schema.ToolInfo{Name: schema.ToolClaudeCode, Surface: schema.SurfaceCLI,
			Version: "0", Model: "claude-opus-4-7", CaptureMode: schema.CaptureLocalExact,
			PricingModel: schema.Pricing{Type: schema.PricingSubscription, Unit: schema.PricingUnitTokens}},
		Timing:   schema.Timing{StartedAt: now, EndedAt: now.Add(time.Minute), ActiveDurationMin: 1},
		Activity: schema.Activity{Mode: schema.ModeAgent},
		Quality:  schema.Quality{HallucinationRisk: schema.HallucinationNone},
		Attribution: schema.Attribution{Method: schema.AttrBranchParse,
			Signals: []string{schema.SourceLocalJSONL}},
		Meta: schema.Meta{CapturedAt: now, AgentVersion: "test",
			DataSources: []string{schema.SourceLocalJSONL}, SchemaVersion: schema.SchemaVersion},
	}
}

func TestPushOneSendsExpectedHeadersAndBody(t *testing.T) {
	var seenHeader http.Header
	var seenBody []byte
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seenHeader = r.Header.Clone()
		seenBody, _ = io.ReadAll(r.Body)
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()

	c := &Client{
		BaseURL: srv.URL, Token: "tok", OrgID: "o", DeveloperID: "d",
		HTTP: srv.Client(),
	}
	if err := c.PushOne(context.Background(), sampleSession()); err != nil {
		t.Fatalf("push: %v", err)
	}
	if got := seenHeader.Get("Authorization"); got != "Bearer tok" {
		t.Errorf("auth header: %q", got)
	}
	if got := seenHeader.Get("X-VibeROI-Org-Id"); got != "o" {
		t.Errorf("org header: %q", got)
	}
	if got := seenHeader.Get("X-VibeROI-Developer-Id"); got != "d" {
		t.Errorf("dev header: %q", got)
	}
	if !strings.Contains(string(seenBody), `"session_id":"sess-1"`) {
		t.Errorf("body missing session_id: %s", seenBody)
	}
}

func TestRetriesOn5xx(t *testing.T) {
	var hits atomic.Int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		n := hits.Add(1)
		if n < 3 {
			w.WriteHeader(http.StatusBadGateway)
			return
		}
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()
	c := &Client{BaseURL: srv.URL, Token: "t", OrgID: "o", DeveloperID: "d", HTTP: srv.Client()}
	if err := c.PushOne(context.Background(), sampleSession()); err != nil {
		t.Fatalf("expected success after retries, got %v", err)
	}
	if hits.Load() != 3 {
		t.Errorf("expected 3 hits, got %d", hits.Load())
	}
}

func TestNoRetryOn401(t *testing.T) {
	var hits atomic.Int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		hits.Add(1)
		w.WriteHeader(http.StatusUnauthorized)
	}))
	defer srv.Close()
	c := &Client{BaseURL: srv.URL, Token: "t", OrgID: "o", DeveloperID: "d", HTTP: srv.Client()}
	err := c.PushOne(context.Background(), sampleSession())
	if !errors.Is(err, ErrAuth) {
		t.Fatalf("expected ErrAuth, got %v", err)
	}
	if hits.Load() != 1 {
		t.Errorf("auth failures must not retry, got %d hits", hits.Load())
	}
}

func TestPushBatchEmptyIsNoOp(t *testing.T) {
	c := &Client{BaseURL: "http://x", Token: "t", OrgID: "o", DeveloperID: "d"}
	if err := c.PushBatch(context.Background(), nil); err != nil {
		t.Errorf("empty batch should be noop, got %v", err)
	}
}

func TestPushBatchPostsToBatchEndpoint(t *testing.T) {
	var seenPath string
	var seenBody []byte
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seenPath = r.URL.Path
		seenBody, _ = io.ReadAll(r.Body)
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()
	c := &Client{BaseURL: srv.URL, Token: "t", OrgID: "o", DeveloperID: "d", HTTP: srv.Client()}
	s := sampleSession()
	if err := c.PushBatch(context.Background(), []schema.Session{s, s}); err != nil {
		t.Fatalf("batch: %v", err)
	}
	if seenPath != "/ingest/sessions" {
		t.Errorf("expected batch path, got %s", seenPath)
	}
	var decoded []schema.Session
	if err := json.Unmarshal(seenBody, &decoded); err != nil || len(decoded) != 2 {
		t.Errorf("body should be a 2-element array: %s", seenBody)
	}
}
