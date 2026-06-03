package schema

import (
	"encoding/json"
	"strings"
	"testing"
	"time"
)

// roundTrip — encode + decode confirms our struct tags match the wire
// format the Python `Session` Pydantic model expects.
func TestSessionRoundTripJSON(t *testing.T) {
	now := time.Date(2026, 6, 3, 12, 0, 0, 0, time.UTC)
	s := Session{
		SessionID:   "sess-1",
		DeveloperID: "00000000-0000-0000-0000-000000000101",
		OrgID:       "00000000-0000-0000-0000-000000000001",
		Tool: ToolInfo{
			Name:        ToolClaudeCode,
			Surface:     SurfaceCLI,
			Version:     "0.5.0",
			Model:       "claude-opus-4-7",
			CaptureMode: CaptureLocalExact,
			PricingModel: Pricing{
				Type:    PricingSubscription,
				Unit:    PricingUnitTokens,
				RateUSD: 0,
			},
		},
		Timing: Timing{
			StartedAt:         now,
			EndedAt:           now.Add(20 * time.Minute),
			ActiveDurationMin: 20,
		},
		Tokens:     Tokens{Input: 1000, Output: 500, TotalCostUSD: 0.42, IsEstimated: false},
		Activity:   Activity{TurnCount: 4, Mode: ModeAgent, IsAgentic: true, FilesTouched: []string{"a.go"}, FilesTouchedCount: 1},
		CodeOutput: CodeOutput{LinesAdded: 10, LinesDeleted: 2},
		Repository: Repository{Name: "acme/web", OriginCWD: "/repo", Branch: "feature/x"},
		Attribution: Attribution{
			Confidence: 0.5,
			Signals:    []string{SourceLocalJSONL},
			Method:     AttrBranchParse,
		},
		Quality: Quality{HallucinationRisk: HallucinationNone},
		Meta: Meta{
			CapturedAt:    now,
			AgentVersion:  "0.1.0",
			DataSources:   []string{SourceLocalJSONL, SourceGitDiff},
			SchemaVersion: SchemaVersion,
		},
	}

	raw, err := json.Marshal(s)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	str := string(raw)
	// Spot-check the snake_case keys the Pydantic side expects.
	for _, want := range []string{
		`"session_id"`, `"developer_id"`, `"org_id"`,
		`"tool"`, `"capture_mode"`, `"pricing_model"`,
		`"timing"`, `"started_at"`, `"active_duration_min"`,
		`"tokens"`, `"total_cost_usd"`, `"is_estimated"`,
		`"activity"`, `"files_touched"`, `"is_agentic"`,
		`"code_output"`, `"lines_added"`, `"commit_hashes"`,
		`"repository"`, `"origin_cwd"`,
		`"attribution"`, `"signals"`, `"method"`,
		`"quality"`, `"hallucination_risk"`,
		`"meta"`, `"captured_at"`, `"schema_version":"1.0"`,
	} {
		if !strings.Contains(str, want) {
			t.Errorf("missing %s in marshalled JSON", want)
		}
	}

	// Decode back and confirm equality on a key field.
	var back Session
	if err := json.Unmarshal(raw, &back); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if back.SessionID != s.SessionID {
		t.Errorf("session_id round-trip lost: %q", back.SessionID)
	}
	if back.Meta.SchemaVersion != SchemaVersion {
		t.Errorf("schema_version mismatch: %q", back.Meta.SchemaVersion)
	}
}

func TestOptionalTimestampsOmittedWhenNil(t *testing.T) {
	s := Session{}
	raw, _ := json.Marshal(s)
	if strings.Contains(string(raw), `"first_commit_at"`) {
		t.Error("first_commit_at should be omitted when nil")
	}
	if strings.Contains(string(raw), `"reconciled_at"`) {
		t.Error("reconciled_at should be omitted when nil")
	}
}
