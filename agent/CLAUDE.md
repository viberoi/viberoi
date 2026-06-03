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

## V1 scope

- **One tool: Claude Code (CLI session.jsonl).** Subagent aggregation,
  AGENT MODE audit, ANTHROPIC_API_KEY landmine detection deferred.
- One source per session, no reconciliation against the Anthropic Admin API.
- Tracks `last_session_id + last_uploaded_at` per tool in `state.json`
  so re-running `push` doesn't re-upload.

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
