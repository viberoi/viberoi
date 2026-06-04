# CLAUDE.md — agent

Go binary that reads AI-coding-tool session metadata from local files
and POSTs to the Ingest service. Separate language, separate rules
from the Python backend. Privacy is non-negotiable: only metadata,
never prompts/code/diffs/PR bodies.

## Layout

```
agent/
  cmd/
    viberoi-agent/main.go      # entry — CLI dispatch
  pkg/
    config/                    # ~/.viberoi/config.yaml — token + ids
    schema/                    # Session v1.0 mirror of Pydantic
    state/                     # ~/.viberoi/state.json — idempotency
    ingest/                    # HTTP client, Bearer auth, retries
    git/                       # branch + commit hashes + LOC numbers
    sources/
      claudecode/              # local-cli-sessions/.../session.jsonl
    runner/                    # discover → read → enrich → push
  testdata/
    claudecode/                # fixture JSONL files
  go.mod
  CLAUDE.md
```

## Current scope

- **Two tools: Claude Code + Cursor.**
- **Claude Code** — two artifact kinds:
  - CLI `session.jsonl` + `subagents/agent-*.jsonl` — subagents folded
    into the parent session's totals.
  - AGENT MODE `audit.jsonl` (Cowork) — separate root, separate reader.
- **Cursor** — single SQLite (`state.vscdb`) holds N composers; each
  composer becomes one session. Tokens summed across bubbles, excluding
  refunded ones (`isRefunded`). Files extracted from
  `toolFormerData.args.file_path` / `path` / `target`. Modes
  (`agent`/`chat`/`edit`) honored from composer's `unifiedMode`.
- `ANTHROPIC_API_KEY` env-var detection (CLI path) + `apiKeySource`
  field detection (AGENT MODE path). Both flip the session's
  `tool.pricing_model.type` from `subscription` to `api_key` so the
  backend reconciler knows to bill at API rates.
- Cursor's `isRefunded` propagates to `Quality.IsRefunded` — backend
  excludes refunded sessions from billed cost.
- State keyed per-(tool, session_id) so Cursor `composerId` collisions
  with Claude Code session ids don't cross-deduplicate.

## Deferred to V3

- Reconciliation against the Anthropic Admin / Usage API.
- Reconciliation against Cursor's usage API (via `usageUuid`).
- `aiCodeTrackingLines` for native AI-code→commit attribution.
- Cline-in-Cursor overlap dedup.
- Kiro / Copilot / Windsurf / JetBrains readers.
- Installer + service mode (Windows service / launchd / systemd).
- Auto-update.

## Commands

```bash
viberoi-agent register --org-id ... --developer-id ... --token ... --url https://api/ingest
viberoi-agent push       # one-shot scan + upload
viberoi-agent run        # daemon — polls every `poll_interval_minutes`
viberoi-agent version
```

## Auth wire

Every POST carries:

```
Authorization: Bearer <token>            # Argon2id-verified server side
X-VibeROI-Org-Id: <uuid>
X-VibeROI-Developer-Id: <uuid>
```

Token is generated server-side once at agent install. The agent
NEVER writes the plaintext token to logs.

## Rules

- Never log a token, JWT, prompt, file content, commit body, or any
  free-form user text. Logs carry `session_id`, `tool`, `dur_ms`,
  `error_type`, and counts only.
- Never `os/exec` arbitrary commands with user-controlled args.
  The only allowed shell-out is `git` with a fixed argv built from
  validated repo paths.
- Never read files that aren't AI-tool session metadata or git refs.
  Reading source code or `.env` files is a bug.
- Always include `schema_version` in the Session struct. Bump it (and
  the Pydantic mirror) for any breaking change.
- No third-party deps in `cmd/`. Keep dependencies tight to stdlib +
  `gopkg.in/yaml.v3` for config. Go-git is heavy; shell out to `git`
  instead.

## Tests

`go test ./...` runs unit tests. Fixtures live in `testdata/`. An
integration test against a real Ingest backend lives in
`pkg/runner/runner_integration_test.go` and is `t.Skip()`-gated unless
`VIBEROI_INTEGRATION=1`.
