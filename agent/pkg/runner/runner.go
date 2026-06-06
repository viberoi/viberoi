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
	"strings"
	"time"

	"github.com/viberoi/viberoi/agent/pkg/config"
	"github.com/viberoi/viberoi/agent/pkg/git"
	"github.com/viberoi/viberoi/agent/pkg/ingest"
	"github.com/viberoi/viberoi/agent/pkg/machineid"
	"github.com/viberoi/viberoi/agent/pkg/schema"
	"github.com/viberoi/viberoi/agent/pkg/sources/claudecode"
	"github.com/viberoi/viberoi/agent/pkg/sources/claudecode_agentmode"
	"github.com/viberoi/viberoi/agent/pkg/sources/copilot"
	"github.com/viberoi/viberoi/agent/pkg/sources/cursor"
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
	Cfg       *config.Config
	State     *state.Store
	Client    *ingest.Client
	MachineID string // cached at construction; same for every session
	Now       func() time.Time // injectable for tests
	Logger    func(string, ...any)
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
		MachineID: machineid.Get(),
		Now:       time.Now,
		Logger:    func(msg string, kv ...any) { fmt.Println(append([]any{msg}, kv...)...) },
	}
}

// Run executes one full pass: discover + parse + push for BOTH the
// Claude Code CLI sessions and the AGENT MODE audit logs.
func (r *Runner) Run(ctx context.Context) (Result, error) {
	var res Result
	if r.Cfg.ClaudeCodePath == "" {
		return res, errors.New("runner: ClaudeCodePath not configured")
	}

	// ANTHROPIC_API_KEY landmine: when this env var is set, Claude Code
	// silently bills at API rates regardless of the user's Pro/Team
	// subscription. Surface it every run so it's not invisible.
	if os.Getenv("ANTHROPIC_API_KEY") != "" {
		r.Logger(
			"anthropic_api_key_set_billing_landmine",
			"hint", "ANTHROPIC_API_KEY is set; sessions may bill at API rates regardless of subscription",
		)
	}

	// ── CLI sessions ──────────────────────────────────────────────────
	files, err := discoverCLISessionFiles(r.Cfg.ClaudeCodePath)
	if err != nil {
		return res, fmt.Errorf("discover cli: %w", err)
	}
	for _, path := range files {
		if ctx.Err() != nil {
			return res, ctx.Err()
		}
		res.Discovered++
		session, err := r.buildCLISession(ctx, path)
		if err != nil {
			r.Logger("session_build_failed", "path", path, "error_type", typeName(err))
			res.Failed++
			continue
		}
		if err := r.pushIfNew(ctx, session, &res); err != nil {
			return res, err
		}
	}

	// ── AGENT MODE sessions (optional) ────────────────────────────────
	if r.Cfg.ClaudeCodeAgentModePath != "" {
		audits, err := discoverAgentModeAuditFiles(r.Cfg.ClaudeCodeAgentModePath)
		if err != nil {
			return res, fmt.Errorf("discover agent mode: %w", err)
		}
		for _, path := range audits {
			if ctx.Err() != nil {
				return res, ctx.Err()
			}
			res.Discovered++
			session, err := r.buildAgentModeSession(ctx, path)
			if err != nil {
				r.Logger("agent_mode_build_failed", "path", path, "error_type", typeName(err))
				res.Failed++
				continue
			}
			if err := r.pushIfNew(ctx, session, &res); err != nil {
				return res, err
			}
		}
	}

	// ── Cursor (optional) ─────────────────────────────────────────────
	// Cursor's storage is ONE SQLite file per install but N sessions
	// per file. Read all, enumerate per composer.
	if r.Cfg.CursorDBPath != "" {
		cursorSessions, err := cursor.ReadAllSessions(r.Cfg.CursorDBPath)
		if err != nil {
			// Don't fail the whole run — a missing/broken Cursor DB is
			// recoverable on next iteration.
			r.Logger("cursor_read_failed", "error_type", typeName(err))
		} else {
			for i := range cursorSessions {
				if ctx.Err() != nil {
					return res, ctx.Err()
				}
				res.Discovered++
				session, err := r.buildCursorSession(ctx, &cursorSessions[i])
				if err != nil {
					r.Logger("cursor_build_failed", "composer_id", cursorSessions[i].ComposerID, "error_type", typeName(err))
					res.Failed++
					continue
				}
				if err := r.pushIfNewCursor(ctx, session, &res); err != nil {
					return res, err
				}
			}
		}
	}

	// VS Code Copilot — N chat-session JSON files under workspaceStorage.
	// Sessions whose id is prefixed `claude-code:/` are Claude Code chats
	// surfaced through Copilot's UI shell and are deduped here per Master
	// spec § 460.
	if r.Cfg.CopilotPath != "" {
		copilotFiles, err := copilot.Discover(r.Cfg.CopilotPath)
		if err != nil {
			r.Logger("copilot_discover_failed", "error_type", typeName(err))
		} else {
			for _, path := range copilotFiles {
				if ctx.Err() != nil {
					return res, ctx.Err()
				}
				session, err := r.buildCopilotSession(ctx, path)
				if err != nil {
					r.Logger("copilot_build_failed", "path", path, "error_type", typeName(err))
					continue
				}
				if session == nil {
					continue // empty session / dedup against Claude Code
				}
				res.Discovered++
				if err := r.pushIfNewCopilot(ctx, session, &res); err != nil {
					return res, err
				}
			}
		}
	}

	return res, nil
}

// pushIfNew sends a Claude Code session unless its id is already in
// state. Auth failures surface to the caller (no retry). All other
// errors increment the failed counter and continue.
func (r *Runner) pushIfNew(
	ctx context.Context, session *schema.Session, res *Result,
) error {
	return r.pushIfNewForTool(ctx, session, schema.ToolClaudeCode, res)
}

// pushIfNewCursor — Cursor variant; state is keyed per-tool so a
// composer_id colliding with a Claude Code session_id can't cross-deduplicate.
func (r *Runner) pushIfNewCursor(
	ctx context.Context, session *schema.Session, res *Result,
) error {
	return r.pushIfNewForTool(ctx, session, schema.ToolCursor, res)
}

// pushIfNewCopilot — Copilot chat sessions are keyed per-tool too.
func (r *Runner) pushIfNewCopilot(
	ctx context.Context, session *schema.Session, res *Result,
) error {
	return r.pushIfNewForTool(ctx, session, schema.ToolCopilot, res)
}

func (r *Runner) pushIfNewForTool(
	ctx context.Context, session *schema.Session, tool string, res *Result,
) error {
	if r.State.Has(tool, session.SessionID) {
		res.Skipped++
		return nil
	}
	if err := r.Client.PushOne(ctx, *session); err != nil {
		if errors.Is(err, ingest.ErrAuth) {
			return err
		}
		r.Logger(
			"session_push_failed",
			"tool", tool,
			"session_id", session.SessionID,
			"error_type", typeName(err),
		)
		res.Failed++
		return nil
	}
	if err := r.State.Mark(tool, session.SessionID); err != nil {
		r.Logger("state_mark_failed", "tool", tool, "session_id", session.SessionID)
	}
	res.Pushed++
	return nil
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

// buildCLISession parses a Claude Code session.jsonl (with its
// subagents/ folded in) and enriches with git data.
func (r *Runner) buildCLISession(ctx context.Context, jsonlPath string) (*schema.Session, error) {
	fs, err := claudecode.ReadFile(jsonlPath)
	if err != nil {
		return nil, err
	}

	mode := schema.ModeAgent
	if !fs.IsAgentic {
		mode = schema.ModeChat
	}

	return r.assembleSession(ctx, sessionInputs{
		SessionID:     fs.SessionID,
		Surface:       schema.SurfaceCLI,
		Model:         fs.Model,
		StartedAt:     fs.StartedAt,
		EndedAt:       fs.EndedAt,
		Input:         fs.Tokens.Input,
		Output:        fs.Tokens.Output,
		CacheRead:     fs.Tokens.CacheRead,
		CacheWrite:    fs.Tokens.CacheWrite,
		TurnCount:     fs.TurnCount,
		SubagentCount: fs.SubagentCount,
		Mode:          mode,
		IsAgentic:     fs.IsAgentic,
		FilesTouched:  fs.FilesTouched,
		// CLI doesn't expose apiKeySource — fall back to env-var detection.
		UsingAPIKey: os.Getenv("ANTHROPIC_API_KEY") != "",
	}), nil
}

// buildAgentModeSession parses an AGENT MODE audit.jsonl and enriches
// with git data. AGENT MODE sessions are always agentic; mode is fixed
// to "agent". apiKeySource is authoritative here (no env fallback).
func (r *Runner) buildAgentModeSession(ctx context.Context, jsonlPath string) (*schema.Session, error) {
	a, err := claudecode_agentmode.ReadFile(jsonlPath)
	if err != nil {
		return nil, err
	}
	return r.assembleSession(ctx, sessionInputs{
		SessionID:    a.SessionID,
		Surface:      schema.SurfaceDesktopApp, // AGENT MODE runs in the desktop Cowork UI
		Model:        a.Model,
		StartedAt:    a.StartedAt,
		EndedAt:      a.EndedAt,
		Input:        a.Tokens.Input,
		Output:       a.Tokens.Output,
		CacheRead:    a.Tokens.CacheRead,
		CacheWrite:   a.Tokens.CacheWrite,
		TurnCount:    a.TurnCount,
		Mode:         schema.ModeAgent,
		IsAgentic:    true,
		FilesTouched: a.FilesTouched,
		UsingAPIKey:  a.UsingAPIKey(),
		DataSources: []string{
			schema.SourceLocalJSONL,
			schema.SourceGitDiff,
		},
	}), nil
}

// buildCursorSession takes one composer's parsed data and assembles a
// Session envelope. Cursor sessions get tool=cursor, surface=
// standalone_ide (Cursor's a VS Code fork shipped as a standalone app).
func (r *Runner) buildCursorSession(ctx context.Context, cs *cursor.CursorSession) (*schema.Session, error) {
	mode := mapCursorMode(cs.Mode)
	s := r.assembleSession(ctx, sessionInputs{
		SessionID:    cs.ComposerID,
		Surface:      schema.SurfaceStandaloneIDE,
		Model:        cs.Model,
		StartedAt:    cs.StartedAt,
		EndedAt:      cs.EndedAt,
		Input:        cs.Tokens.Input,
		Output:       cs.Tokens.Output,
		TurnCount:    cs.TurnCount,
		Mode:         mode,
		IsAgentic:    cs.IsAgentic,
		FilesTouched: cs.FilesTouched,
		DataSources: []string{
			schema.SourceLocalSQLite,
			schema.SourceGitDiff,
		},
	})
	// Patch the tool name — assembleSession defaults to Claude Code.
	s.Tool.Name = schema.ToolCursor
	// Cursor's refunded flag travels on the Quality block. The Worker
	// treats refunded sessions specially in cost rollups.
	s.Quality.IsRefunded = cs.IsRefunded
	return s, nil
}

// buildCopilotSession parses one chatSessions JSON and assembles a
// Session envelope. Tokens are 0 — Copilot keeps them server-side; the
// backend reconciler will fill in via GitHub copilot metrics. Mode
// derives from the Copilot agent id (editsAgent → agent, default → chat).
//
// Returns (nil, nil) for empty files (zero requests) and Claude Code
// proxy sessions surfaced through Copilot's UI shell (deduped per
// Master spec § 460).
func (r *Runner) buildCopilotSession(ctx context.Context, jsonlPath string) (*schema.Session, error) {
	parsed, err := copilot.ReadFile(jsonlPath)
	if err != nil {
		return nil, err
	}
	if parsed == nil {
		return nil, nil
	}
	if parsed.IsClaudeProxy() {
		return nil, nil
	}

	mode := schema.ModeChat
	if strings.Contains(parsed.AgentID, "edit") {
		mode = schema.ModeAgent
	}

	s := r.assembleSession(ctx, sessionInputs{
		SessionID:    parsed.SessionID,
		Surface:      schema.SurfaceVSCodeExtension,
		Model:        parsed.Model,
		StartedAt:    parsed.CreatedAt,
		EndedAt:      parsed.UpdatedAt,
		Input:        0, // server-side reconciliation; agent emits 0
		Output:       0,
		TurnCount:    parsed.TurnCount,
		Mode:         mode,
		IsAgentic:    strings.Contains(parsed.AgentID, "edit"),
		FilesTouched: parsed.FilePaths,
		DataSources: []string{
			schema.SourceLocalJSONL,
			schema.SourceGitDiff,
		},
	})
	s.Tool.Name = schema.ToolCopilot
	// Copilot is subscription-priced; never API-keyed locally. Worker
	// reconciles to a per-seat amortization or to the metrics API once
	// configured.
	s.Tokens.IsEstimated = true
	return s, nil
}

// mapCursorMode collapses Cursor's mode strings onto our SessionMode
// enum. Cursor uses "chat", "agent", "edit", "ask"; anything else falls
// back to "chat".
func mapCursorMode(m string) string {
	switch m {
	case schema.ModeAgent, schema.ModeChat, schema.ModePlan,
		schema.ModeEdit, schema.ModeAsk:
		return m
	default:
		return schema.ModeChat
	}
}

// sessionInputs aggregates everything assembleSession needs so the two
// builders stay declarative and don't drift apart.
type sessionInputs struct {
	SessionID                                   string
	Surface, Model, Mode                        string
	StartedAt, EndedAt                          time.Time
	Input, Output, CacheRead, CacheWrite        int
	TurnCount, SubagentCount                    int
	IsAgentic                                   bool
	FilesTouched                                []string
	UsingAPIKey                                 bool
	DataSources                                 []string // overrides default
}

// assembleSession is the shared builder for CLI and AGENT MODE sessions.
// It folds in git data and applies the ANTHROPIC_API_KEY pricing flip.
func (r *Runner) assembleSession(ctx context.Context, in sessionInputs) *schema.Session {
	cwd, _ := os.Getwd()
	repo, _ := git.Inspect(ctx, cwd)
	var commits []string
	loc := git.LOCDiff{}
	var firstCommitAt time.Time
	uncommittedAtEnd := false
	if repo != nil && !in.StartedAt.IsZero() {
		commits, _ = git.CommitsSince(ctx, repo.OriginCWD, in.StartedAt, 50)
		loc, _ = git.LOCSince(ctx, repo.OriginCWD, in.StartedAt)
		firstCommitAt, _ = git.FirstCommitTimeSince(ctx, repo.OriginCWD, in.StartedAt)
		uncommittedAtEnd, _ = git.IsDirty(ctx, repo.OriginCWD)
	}

	durMin := int(in.EndedAt.Sub(in.StartedAt).Minutes())
	if durMin < 0 {
		durMin = 0
	}

	// time_to_first_commit: minutes from session start to earliest commit
	// in the window. Nil when there's no commit yet (no signal to derive).
	var firstCommitPtr *time.Time
	var ttfcPtr *int
	if !firstCommitAt.IsZero() {
		fca := firstCommitAt
		firstCommitPtr = &fca
		mins := int(firstCommitAt.Sub(in.StartedAt).Minutes())
		if mins < 0 {
			mins = 0
		}
		ttfcPtr = &mins
	}

	// Pricing: subscription unless we detect the API-key landmine.
	pricingType := schema.PricingSubscription
	if in.UsingAPIKey {
		pricingType = schema.PricingAPIKey
	}

	sources := in.DataSources
	if len(sources) == 0 {
		sources = []string{schema.SourceLocalJSONL, schema.SourceGitDiff}
	}

	return &schema.Session{
		SessionID:   in.SessionID,
		DeveloperID: r.Cfg.DeveloperID,
		OrgID:       r.Cfg.OrgID,
		MachineID:   r.MachineID,
		Tool: schema.ToolInfo{
			Name:        schema.ToolClaudeCode,
			Surface:     in.Surface,
			Version:     "unknown",
			Model:       safeOr(in.Model, "unknown"),
			CaptureMode: schema.CaptureLocalExact,
			PricingModel: schema.Pricing{
				Type:    pricingType,
				Unit:    schema.PricingUnitTokens,
				RateUSD: 0,
			},
		},
		Timing: schema.Timing{
			StartedAt:            in.StartedAt,
			EndedAt:              in.EndedAt,
			ActiveDurationMin:    durMin,
			FirstCommitAt:        firstCommitPtr,
			TimeToFirstCommitMin: ttfcPtr,
		},
		Tokens: schema.Tokens{
			Input:        in.Input,
			Output:       in.Output,
			CacheRead:    in.CacheRead,
			CacheWrite:   in.CacheWrite,
			TotalCostUSD: 0, // reconciliation happens server-side
			IsEstimated:  false,
		},
		Activity: schema.Activity{
			TurnCount:         in.TurnCount,
			Mode:              in.Mode,
			IsAgentic:         in.IsAgentic,
			SubagentCount:     in.SubagentCount,
			FilesTouched:      in.FilesTouched,
			FilesTouchedCount: len(in.FilesTouched),
		},
		CodeOutput: schema.CodeOutput{
			LinesAdded:       loc.LinesAdded,
			LinesDeleted:     loc.LinesDeleted,
			IsCommitted:      len(commits) > 0,
			CommitHashes:     commits,
			UncommittedAtEnd: uncommittedAtEnd,
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
			DataSources:   sources,
			SchemaVersion: schema.SchemaVersion,
		},
	}
}

// discoverCLISessionFiles walks the Claude Code CLI sessions root.
// Accepts two layouts:
//   - Desktop: <root>/<account>/<group>/<id>/session.jsonl
//   - CLI:     <root>/<projectSlug>/<sessionId>.jsonl
//
// Skips any `subagents/` subtree (those are folded into their parent
// session by the reader) and `audit.jsonl` files (AGENT MODE — handled
// by the sibling package). Missing root → empty slice, no error.
func discoverCLISessionFiles(root string) ([]string, error) {
	if _, err := os.Stat(root); errors.Is(err, fs.ErrNotExist) {
		return nil, nil
	}
	var out []string
	err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if d.IsDir() {
			if d.Name() == "subagents" {
				return fs.SkipDir
			}
			return nil
		}
		name := d.Name()
		if name == "session.jsonl" {
			out = append(out, path)
			return nil
		}
		if strings.HasSuffix(name, ".jsonl") && name != "audit.jsonl" {
			out = append(out, path)
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// discoverAgentModeAuditFiles walks the AGENT MODE sessions root for
// `audit.jsonl`. Missing root → empty slice, no error.
func discoverAgentModeAuditFiles(root string) ([]string, error) {
	return walkForName(root, "audit.jsonl")
}

func walkForName(root, name string) ([]string, error) {
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
		if d.Name() == name {
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
