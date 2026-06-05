// Package schema mirrors the Pydantic Session v1.0 from
// `backend/packages/shared/viberoi_shared/types/session.py`.
//
// Any breaking change here MUST be matched on the Python side, with a
// schema_version bump on both. The Worker accepts current + previous
// version for one release after a bump.
package schema

import "time"

const SchemaVersion = "1.0"

// Tool enum values — keep in sync with viberoi_shared.types.enums.Tool.
const (
	ToolClaudeCode  = "claude-code"
	ToolCursor      = "cursor"
	ToolKiro        = "kiro"
	ToolCopilot     = "copilot"
	ToolWindsurf    = "windsurf"
	ToolJetBrainsAI = "jetbrains-ai"
)

const (
	SurfaceCLI               = "cli"
	SurfaceDesktopApp        = "desktop_app"
	SurfaceVSCodeExtension   = "vscode_extension"
	SurfaceStandaloneIDE     = "standalone_ide"
)

const (
	CaptureLocalExact     = "local_exact"
	CaptureLocalEstimated = "local_estimated"
	CaptureAPIOnly        = "api_only"
)

const (
	PricingSubscription = "subscription"
	PricingAPIKey       = "api_key"
	PricingCredits      = "credits"
	PricingSeat         = "seat"

	PricingUnitTokens          = "tokens"
	PricingUnitCredits         = "credits"
	PricingUnitPremiumRequests = "premium_requests"
)

const (
	ModeAgent = "agent"
	ModeChat  = "chat"
	ModePlan  = "plan"
	ModeEdit  = "edit"
	ModeAsk   = "ask"
)

const (
	AttrBranchParse   = "branch_parse"
	AttrKiroNative    = "kiro_native"
	AttrManual        = "manual"
	AttrManualConfirm = "manual_confirm"
)

const (
	HallucinationNone  = "none"
	HallucinationWatch = "watch"
	HallucinationAlert = "alert"
)

const (
	SourceLocalJSONL        = "local_jsonl"
	SourceLocalSQLite       = "local_sqlite"
	SourceGitDiff           = "git_diff"
	SourceWorktreeMap       = "worktree_map"
	SourceAWSS3CSV          = "aws_s3_csv"
	SourceGitHubAPI         = "github_api"
	SourceAnthropicAdminAPI = "anthropic_admin_api"
)

// Pricing mirrors viberoi_shared.types.session.Pricing.
type Pricing struct {
	Type    string  `json:"type"`
	Unit    string  `json:"unit"`
	RateUSD float64 `json:"rate_usd"`
}

type ToolInfo struct {
	Name         string  `json:"name"`
	Surface      string  `json:"surface"`
	Version      string  `json:"version"`
	Model        string  `json:"model"`
	CaptureMode  string  `json:"capture_mode"`
	PricingModel Pricing `json:"pricing_model"`
}

type Timing struct {
	StartedAt            time.Time  `json:"started_at"`
	EndedAt              time.Time  `json:"ended_at"`
	ActiveDurationMin    int        `json:"active_duration_min"`
	FirstCommitAt        *time.Time `json:"first_commit_at,omitempty"`
	TimeToFirstCommitMin *int       `json:"time_to_first_commit_min,omitempty"`
}

type Tokens struct {
	Input         int        `json:"input"`
	Output        int        `json:"output"`
	CacheRead     int        `json:"cache_read"`
	CacheWrite    int        `json:"cache_write"`
	TotalCostUSD  float64    `json:"total_cost_usd"`
	IsEstimated   bool       `json:"is_estimated"`
	Reconciled    bool       `json:"reconciled"`
	ReconciledAt  *time.Time `json:"reconciled_at,omitempty"`
}

type Activity struct {
	TurnCount         int      `json:"turn_count"`
	Mode              string   `json:"mode"`
	IsAgentic         bool     `json:"is_agentic"`
	SubagentCount     int      `json:"subagent_count"`
	FilesTouched      []string `json:"files_touched"`
	FilesTouchedCount int      `json:"files_touched_count"`
}

type CodeOutput struct {
	LinesAdded       int      `json:"lines_added"`
	LinesDeleted     int      `json:"lines_deleted"`
	LinesAccepted    int      `json:"lines_accepted"`
	LinesReverted    int      `json:"lines_reverted"`
	IsCommitted      bool     `json:"is_committed"`
	CommitHashes     []string `json:"commit_hashes"`
	UncommittedAtEnd bool     `json:"uncommitted_at_end"`
}

type Repository struct {
	Name       string `json:"name"`
	OriginCWD  string `json:"origin_cwd"`
	Branch     string `json:"branch"`
	RawBranch  string `json:"raw_branch,omitempty"`
	IsWorktree bool   `json:"is_worktree"`
}

type Attribution struct {
	TicketID   string   `json:"ticket_id,omitempty"`
	EpicID     string   `json:"epic_id,omitempty"`
	SprintID   string   `json:"sprint_id,omitempty"`
	Confidence float64  `json:"confidence"`
	Signals    []string `json:"signals"`
	Method     string   `json:"method"`
}

type Quality struct {
	SessionRestarts     int    `json:"session_restarts"`
	FileOscillations    int    `json:"file_oscillations"`
	TokenSpikeDetected  bool   `json:"token_spike_detected"`
	NoCommitDurationMin int    `json:"no_commit_duration_min"`
	IsRefunded          bool   `json:"is_refunded"`
	HallucinationRisk   string `json:"hallucination_risk"`
}

type Meta struct {
	CapturedAt    time.Time `json:"captured_at"`
	AgentVersion  string    `json:"agent_version"`
	DataSources   []string  `json:"data_sources"`
	SchemaVersion string    `json:"schema_version"`
}

// Session is the wire envelope sent to /ingest/session.
type Session struct {
	SessionID   string `json:"session_id"`
	DeveloperID string `json:"developer_id"`
	OrgID       string `json:"org_id"`
	// Stable per-machine hex hash from `viberoi-agent/pkg/machineid`.
	// Backend writes it to `developers.machine_id_hash` on first push
	// for this developer; subsequent pushes from a different machine
	// flag cross-device reuse for the active-device meter.
	MachineID string `json:"machine_id"`

	Tool        ToolInfo    `json:"tool"`
	Timing      Timing      `json:"timing"`
	Tokens      Tokens      `json:"tokens"`
	Activity    Activity    `json:"activity"`
	CodeOutput  CodeOutput  `json:"code_output"`
	Repository  Repository  `json:"repository"`
	Attribution Attribution `json:"attribution"`
	Quality     Quality     `json:"quality"`
	Meta        Meta        `json:"meta"`
}
