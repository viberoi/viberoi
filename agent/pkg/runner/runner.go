// Package runner orchestrates the pipeline:
//   discover Claude Code session files → parse → enrich with git → POST
//
// One Run() call walks the configured Claude Code sessions root, parses
// every session.jsonl, builds a Session struct, and posts what hasn't
// been posted before (per the state store). Daemon mode is just Run()
// in a loop with sleep on the configured interval.
package runner

import (
	"context"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"time"

	"github.com/viberoi/viberoi/agent/pkg/config"
	"github.com/viberoi/viberoi/agent/pkg/git"
	"github.com/viberoi/viberoi/agent/pkg/ingest"
	"github.com/viberoi/viberoi/agent/pkg/schema"
	"github.com/viberoi/viberoi/agent/pkg/sources/claudecode"
	"github.com/viberoi/viberoi/agent/pkg/state"
)

const (
	AgentVersion = "0.1.0"
)

// Result summarises one Run().
type Result struct {
	Discovered int
	Skipped    int // already in state
	Pushed     int
	Failed     int
}

// Runner is the top-level orchestrator. Constructed by the CLI from
// loaded config + opened state.
type Runner struct {
	Cfg    *config.Config
	State  *state.Store
	Client *ingest.Client
	Now    func() time.Time // injectable for tests
	Logger func(string, ...any)
}

// New builds a Runner with sensible defaults.
func New(cfg *config.Config, st *state.Store) *Runner {
	return &Runner{
		Cfg:   cfg,
		State: st,
		Client: &ingest.Client{
			BaseURL:     cfg.IngestURL,
			Token:       cfg.Token,
			OrgID:       cfg.OrgID,
			DeveloperID: cfg.DeveloperID,
			UserAgent:   "viberoi-agent/" + AgentVersion,
		},
		Now:    time.Now,
		Logger: func(msg string, kv ...any) { fmt.Println(append([]any{msg}, kv...)...) },
	}
}

// Run executes one full pass: discover + parse + push.
func (r *Runner) Run(ctx context.Context) (Result, error) {
	var res Result
	if r.Cfg.ClaudeCodePath == "" {
		return res, errors.New("runner: ClaudeCodePath not configured")
	}
	files, err := discoverSessionFiles(r.Cfg.ClaudeCodePath)
	if err != nil {
		return res, fmt.Errorf("discover: %w", err)
	}
	res.Discovered = len(files)
	for _, path := range files {
		if ctx.Err() != nil {
			return res, ctx.Err()
		}
		session, err := r.buildSession(ctx, path)
		if err != nil {
			r.Logger("session_build_failed", "path", path, "error_type", typeName(err))
			res.Failed++
			continue
		}
		if r.State.Has(schema.ToolClaudeCode, session.SessionID) {
			res.Skipped++
			continue
		}
		if err := r.Client.PushOne(ctx, *session); err != nil {
			if errors.Is(err, ingest.ErrAuth) {
				return res, err // surface auth failure to caller
			}
			r.Logger(
				"session_push_failed",
				"session_id", session.SessionID,
				"error_type", typeName(err),
			)
			res.Failed++
			continue
		}
		if err := r.State.Mark(schema.ToolClaudeCode, session.SessionID); err != nil {
			r.Logger("state_mark_failed", "session_id", session.SessionID)
		}
		res.Pushed++
	}
	return res, nil
}

// RunForever loops Run() with the configured poll interval. Returns
// only when ctx is cancelled.
func (r *Runner) RunForever(ctx context.Context) error {
	for {
		if _, err := r.Run(ctx); err != nil {
			r.Logger("run_iteration_failed", "error_type", typeName(err))
			if errors.Is(err, ingest.ErrAuth) {
				return err
			}
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(r.Cfg.PollInterval()):
		}
	}
}

// buildSession parses a Claude Code session.jsonl and folds in git data
// for the session window.
func (r *Runner) buildSession(ctx context.Context, jsonlPath string) (*schema.Session, error) {
	fs, err := claudecode.ReadFile(jsonlPath)
	if err != nil {
		return nil, err
	}

	cwd, _ := os.Getwd()
	repo, _ := git.Inspect(ctx, cwd) // best-effort; not in a repo → blank
	var commits []string
	loc := git.LOCDiff{}
	if repo != nil && !fs.StartedAt.IsZero() {
		commits, _ = git.CommitsSince(ctx, repo.OriginCWD, fs.StartedAt, 50)
		loc, _ = git.LOCSince(ctx, repo.OriginCWD, fs.StartedAt)
	}

	started := fs.StartedAt
	ended := fs.EndedAt
	durMin := int(ended.Sub(started).Minutes())
	if durMin < 0 {
		durMin = 0
	}

	mode := schema.ModeAgent
	if !fs.IsAgentic {
		mode = schema.ModeChat
	}

	s := &schema.Session{
		SessionID:   fs.SessionID,
		DeveloperID: r.Cfg.DeveloperID,
		OrgID:       r.Cfg.OrgID,
		Tool: schema.ToolInfo{
			Name:        schema.ToolClaudeCode,
			Surface:     schema.SurfaceCLI,
			Version:     "unknown",
			Model:       safeOr(fs.Model, "unknown"),
			CaptureMode: schema.CaptureLocalExact,
			PricingModel: schema.Pricing{
				Type:    schema.PricingSubscription,
				Unit:    schema.PricingUnitTokens,
				RateUSD: 0,
			},
		},
		Timing: schema.Timing{
			StartedAt:         started,
			EndedAt:           ended,
			ActiveDurationMin: durMin,
		},
		Tokens: schema.Tokens{
			Input:        fs.Tokens.Input,
			Output:       fs.Tokens.Output,
			CacheRead:    fs.Tokens.CacheRead,
			CacheWrite:   fs.Tokens.CacheWrite,
			TotalCostUSD: 0, // subscription tool — cost reconciles server-side
			IsEstimated:  false,
		},
		Activity: schema.Activity{
			TurnCount:         fs.TurnCount,
			Mode:              mode,
			IsAgentic:         fs.IsAgentic,
			FilesTouched:      fs.FilesTouched,
			FilesTouchedCount: len(fs.FilesTouched),
		},
		CodeOutput: schema.CodeOutput{
			LinesAdded:   loc.LinesAdded,
			LinesDeleted: loc.LinesDeleted,
			IsCommitted:  len(commits) > 0,
			CommitHashes: commits,
		},
		Repository: schema.Repository{
			Name:       repoName(repo),
			OriginCWD:  repoCWD(repo, cwd),
			Branch:     repoBranch(repo),
			RawBranch:  repoRaw(repo),
			IsWorktree: repo != nil && repo.IsWorktree,
		},
		Attribution: schema.Attribution{
			Confidence: 0,
			Signals:    []string{schema.SourceLocalJSONL},
			Method:     schema.AttrBranchParse,
		},
		Quality: schema.Quality{
			HallucinationRisk: schema.HallucinationNone,
		},
		Meta: schema.Meta{
			CapturedAt:    r.Now().UTC(),
			AgentVersion:  AgentVersion,
			DataSources:   []string{schema.SourceLocalJSONL, schema.SourceGitDiff},
			SchemaVersion: schema.SchemaVersion,
		},
	}
	return s, nil
}

// discoverSessionFiles walks the configured root looking for files named
// `session.jsonl`. We're tolerant of missing roots — returns an empty
// slice rather than an error.
func discoverSessionFiles(root string) ([]string, error) {
	if _, err := os.Stat(root); errors.Is(err, fs.ErrNotExist) {
		return nil, nil
	}
	var out []string
	err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil // skip unreadable subtrees
		}
		if d.IsDir() {
			return nil
		}
		if d.Name() == "session.jsonl" {
			out = append(out, path)
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

func repoName(r *git.Repo) string {
	if r == nil {
		return ""
	}
	return filepath.Base(r.OriginCWD)
}
func repoCWD(r *git.Repo, fallback string) string {
	if r == nil {
		return fallback
	}
	return r.OriginCWD
}
func repoBranch(r *git.Repo) string {
	if r == nil {
		return "unknown"
	}
	return r.Branch
}
func repoRaw(r *git.Repo) string {
	if r == nil {
		return ""
	}
	return r.RawBranch
}
func safeOr(s, fallback string) string {
	if s == "" {
		return fallback
	}
	return s
}
func typeName(err error) string {
	if err == nil {
		return ""
	}
	return fmt.Sprintf("%T", err)
}
