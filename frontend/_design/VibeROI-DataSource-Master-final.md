# VibeROI — Master Data-Source Map

**Purpose:** Document, with *verified real data*, exactly where each IDE / AI coding tool stores its data, what fields are available, their token fidelity, and which KPIs they power. No assumptions — every "✅ verified" entry below was confirmed by reading actual bytes on a real machine.

**Last updated:** 2026-05-27
**Verified on:** Windows 11, user `AdnanKhan`, Claude Pro subscription

---

## The 3-Source Architecture (recap)

| Source | Role | Captured by |
|---|---|---|
| **1. IDE local data** | Granular per-session/per-turn detail — the "what happened" | Lightweight agent (+ optional extension) |
| **2. Model billing API** | Exact totals, accuracy correction — the "what it cost" | Backend, server-side OAuth |
| **3. GitHub + ticketing** | Attribution + review context — the "what it was for" | Webhooks / GitHub App / OAuth |

**Hard rules locked:**
- Agent reads two scopes: IDE log files **and** local git (read-only)
- Git is source of truth for LOC/churn; JSONL for tokens/turns
- Uncommitted work captured via `git diff --numstat` — **numbers only, never code**
- Never transmit prompt text or code; score prompt-quality locally if at all
- Branch name → ticket ID is the join key (ticketing API deferred)

---

## The 6 KPIs (what every field must serve)

1. **Token cost per ticket** — sum of session token costs attributed to a ticket
2. **Prompt efficiency score** (no prompt reading) — churn 40% / restarts 30% / time-to-clean-commit 20% / token spike 10%
3. **Cost per ticket closed** — token_cost + (dev_hours × rate) — the CFO number
4. **Sprint-level AI spend** — sum of ticket costs in sprint window, vs prior sprint
5. **Hallucination loop detection** — token spike >3× avg / file oscillation >5× in 2h / >3 restarts in 4h / >90min no-commit
6. **Developer efficiency trend** — improvement trajectory, never raw rankings

---

## Tool Coverage Status

| Tool | Local verified? | API verified? | Token fidelity | Status |
|---|---|---|---|---|
| **Claude Code (desktop)** | ✅ real data | ✅ (none for Pro) | EXACT | **COMPLETE** |
| **Kiro (AWS agentic IDE)** | ✅ real data | ✅ S3 CSV + CUR (teams) verified via docs | local input-only; cost via AWS | **COMPLETE** |
| **VS Code + Copilot** | ✅ real data | ✅ GitHub metrics + billing API (per user/model/day) | local text+model; cost server-side → token-based Jun 1 2026 | **COMPLETE** |
| **Cursor** | ✅ real data (richest) | ✅ server join keys present (usageUuid) | EXACT (per-message, local) | **COMPLETE** |
| Windsurf | ⬜ not installed | ⬜ | TBD | install + verify |
| JetBrains AI | ⬜ not installed | ⬜ | TBD | install + verify |

---

# Profile Template (every tool follows this)

```
TOOL: <name>
  Surface:           desktop app / CLI / VS Code extension / standalone IDE
  Local file?:       yes/no + exact path(s)
  File format:       JSONL / JSON / SQLite
  Token fidelity:    EXACT / ESTIMATED / via-API-only
  Storage systems:   how many distinct stores, how they join
  Fields we get:     actual fields from real data
  Git context:       branch? cwd? worktree mapping?
  Billing modes:     subscription vs API key — how detected
  Powers KPIs:       which of the 6
  Gaps + fills:      what's missing, how we compute it
  Access method:     agent reads file / backend hits API
```

---

# TOOL #1 — Claude Code (Desktop "Code" mode + CLI)  ✅ COMPLETE

**Verified by reading real session files on a Pro account.** Token data is exact and per-turn — the gold standard among all tools.

## Storage: THREE distinct systems, joined by IDs

```
┌─ claude-code-sessions/<acct>/<grp>/local_XXX.json ── INDEX ─┐
│   timing, title, model, worktree→branch map                │
│   field: cliSessionId  ──────────┐                          │
└───────────────────────────────────┼──────────────────────────┘
                                     ▼
┌─ .claude/projects/<encoded-path>/<cliSessionId>.jsonl ── TOKENS ─┐
│   exact per-turn usage, tool calls, thinking                     │
│   subagents/agent-*.jsonl  ── per-subagent token detail          │
└───────────────────────────────────────────────────────────────────┘

┌─ local-agent-mode-sessions/.../audit.jsonl ── AGENT MODE (Cowork) ─┐
│   HMAC-signed events, apiKeySource, completedTurns, tool list      │
└─────────────────────────────────────────────────────────────────────┘
```

### Exact paths (Windows)
```
INDEX:   %APPDATA%\Claude\claude-code-sessions\<accountId>\<groupId>\local_<id>.json
TOKENS:  %APPDATA%\Claude\.claude\projects\<encoded-cwd>\<cliSessionId>.jsonl
         (note: also seen under the repo at <repo>\.claude\projects\…)
SUBAGENTS: <same>\<cliSessionId>\subagents\agent-<id>.jsonl  (+ .meta.json)
AGENT MODE: %APPDATA%\Claude\local-agent-mode-sessions\<acct>\<grp>\local_<id>\audit.jsonl
WORKTREE MAP: %APPDATA%\Claude\git-worktrees.json
DAILY TALLY:  %APPDATA%\Claude\buddy-tokens.json
MCP CONFIG:   %APPDATA%\Claude\claude_desktop_config.json
```

## Fields available (from real data)

### From the INDEX file (`local_XXX.json`) — the Rosetta Stone
| Field | Example | Use |
|---|---|---|
| `sessionId` | `local_d7f613d2-…` | joins to git-worktrees `leasedBy` |
| `cliSessionId` | `cbc2a536-…` | **joins to the JSONL filename** |
| `cwd` | `…\worktrees\xenodochial-…` | working dir |
| `originCwd` | `C:\Users\AdnanKhan\wvp-backend` | **REAL repo root** |
| `sourceBranch` | `organized` | **REAL parent branch** |
| `branch` | `claude/xenodochial-…` | worktree branch |
| `createdAt` | `1778059712815` | **session start** |
| `lastActivityAt` | `1778064170826` | **session end** → duration = 74 min |
| `model` | `claude-sonnet-4-6` | model |
| `title` | "Refactor CI/CD…" | auto-summary |
| `permissionMode` | `acceptEdits` / `plan` | autonomy level |
| `planPath` | `…\plans\….md` | plan file |
| `completedTurns` *(in audit)* | `4` | turn count |

### From the TOKENS file (`.jsonl`) — per assistant turn
| Field | Example | Use |
|---|---|---|
| `message.usage.input_tokens` | `3` | exact input |
| `message.usage.output_tokens` | `226` | exact output |
| `message.usage.cache_read_input_tokens` | `163906` | cache reads (bulk of cost base) |
| `message.usage.cache_creation_input_tokens` | `188` | cache writes |
| `message.model` | `claude-sonnet-4-6` | model per turn |
| `timestamp` | ISO 8601 | per-event time |
| `gitBranch` | `claude/xenodochial-…` | branch at turn |
| `cwd` | full path | working dir |
| `entrypoint` | `claude-desktop` | surface |
| `version` | `2.1.128` | client version |
| `type` | `user` / `assistant` | turn role |
| `isSidechain` | `false` / `true` | main vs subagent |
| `parentUuid` / `uuid` | … | thread linkage |
| `content[].type` | `text` / `thinking` / `tool_use` | turn content |
| tool_use `name` + `input.file_path` | `Write`, `…\.husky\pre-commit` | **files touched** |

### From AGENT MODE (`audit.jsonl`) — Cowork/agentic runs
| Field | Example | Use |
|---|---|---|
| `apiKeySource` | `"none"` | **billing-mode detector** (none = subscription) |
| `model` | `claude-sonnet-4-6` | model |
| `claude_code_version` | `2.1.142` | version |
| `completedTurns` | `4` | turn count |
| `tools[]` | full list | capabilities that session |
| `mcp_servers[]` | name + status | connected servers |
| `client_platform` | `desktop_app` | surface |
| `_audit_timestamp` | ISO 8601 | per-event time |
| `_audit_hmac` | hex | **tamper-evident signature** |

## Token fidelity: **EXACT**
Real per-turn counts for input, output, cache-read, cache-write. Cost must aggregate all four across all turns AND all subagents — there is **no rolled-up total**; the file just ends.

```
true_cost = Σ over every assistant turn (main + subagents):
    input_tokens        × input_price
  + output_tokens       × output_price        (incl. thinking tokens)
  + cache_creation      × cache_write_price
  + cache_read          × cache_read_price     (~10% of input price)
```

## Billing modes
| Account | Exact local source | API accuracy layer |
|---|---|---|
| Pro / Max (subscription) | ✅ JSONL (only source) | ❌ none — flat fee, no per-token API |
| API key / Console | ✅ JSONL | ✅ Anthropic Admin/Usage API |
| Team / Enterprise | ✅ JSONL | ✅ Admin usage API |

Detector: `apiKeySource` in audit init. `"none"` = subscription → local is the only truth. **Landmine:** if `ANTHROPIC_API_KEY` is set in the shell, Claude Code silently bills at API rates regardless of subscription — agent must surface this.

## Powers which KPIs
- **KPI 1/3/4 (cost):** exact tokens → exact cost per ticket/sprint
- **KPI 2 (efficiency):** turn count (`completedTurns`), token-per-turn for spike signal, files-touched for churn
- **KPI 5 (hallucination):** per-turn token series (spikes), tool_use file paths (oscillation), session timing (no-commit window)
- **KPI 6 (trend):** all of the above over time

## Git context
- `gitBranch` in JSONL = worktree branch (`claude/…`), **not** the feature branch
- Resolved via `git-worktrees.json` + index `sourceBranch`/`originCwd` → real branch + repo
- Real LOC/churn still comes from `git diff --numstat` against `originCwd`, not the JSONL

## Gaps + how we fill them
| Gap | Fill |
|---|---|
| No rolled-up token total | Aggregate all turns + subagents |
| Worktree branch ≠ feature branch | `git-worktrees.json.sourceBranch` + index `originCwd` |
| Lines actually written | `git diff --numstat` on real repo (numbers only) |
| Uncommitted AI work | `git diff --numstat` on dirty working dir; mark `uncommitted`, reconcile on commit |
| Pro has no usage API | Accept local JSONL as sole truth for subscription users |

## Access method
**Agent reads files** (all three systems). No API needed for Pro. For API-key/enterprise accounts, backend additionally pulls Anthropic Admin/Usage API as the accuracy layer.

---

# TOOL #2 — Kiro (AWS agentic, spec-driven IDE)  ✅ COMPLETE

**Verified by reading real session + task files on a real install.** Kiro is a VS Code fork. It stores the full conversation locally but **no exact token counts** — fidelity is ESTIMATED. It compensates with the strongest **native task attribution** of any tool.

## Storage: VS Code-fork layout + Kiro's own task/spec system

```
┌─ .kiro/tasks/<id>/<spec-name>.meta.json ── TASK MODEL (native attribution) ─┐
│   taskId, executionStatus, executionHistory[].executionId + chatSessionId   │
│   specUri → the spec's tasks.md                                              │
└──────────────────────────┬───────────────────────────────────────────────────┘
              executionId / chatSessionId
                           ▼
┌─ Kiro\User\globalStorage\kiro.kiroagent\sessions\<id>.json ── CONVERSATION ─┐
│   history[] full turns, promptLogs[], model, maxTokens (ceiling, NOT usage)  │
└──────────────────────────┬───────────────────────────────────────────────────┘
              workspace path (Base64-encoded)
                           ▼
┌─ …\kiro.kiroagent\workspace-sessions\<base64-path>\ ── PER-PROJECT GROUPING ─┐
│   folder name decodes to C:\Users\…\makemyitinerary etc.                     │
└─────────────────────────────────────────────────────────────────────────────┘

ALSO: …\globalStorage\state.vscdb  (SQLite, single ItemTable — VS Code UI state)
```

### Exact paths (Windows)
```
KIRO HOME:    %USERPROFILE%\.kiro\  (tasks, specs, steering, skills, settings)
TASK META:    %USERPROFILE%\.kiro\tasks\<hash>\<spec-name>.meta.json
SESSIONS:     %APPDATA%\Kiro\User\globalStorage\kiro.kiroagent\sessions\<uuid>.json
WORKSPACE:    %APPDATA%\Kiro\User\globalStorage\kiro.kiroagent\workspace-sessions\<base64>\
SQLITE:       %APPDATA%\Kiro\User\globalStorage\state.vscdb   (one table: ItemTable)
SPECS (repo): <repo>\.kiro\specs\<spec-name>\tasks.md
```

## Fields available (from real data)

### From the TASK META file — native attribution (no branch parsing needed!)
| Field | Example | Use |
|---|---|---|
| `taskId` | "7. Create WebSocket Lambda handlers" | task identity + description |
| `specUri` | `…/.kiro/specs/…/tasks.md` | **links task → spec → repo** |
| `executionHistory[].chatSessionId` | `e0640f59-…` | **joins to session JSON** |
| `executionHistory[].executionId` | `ca549e0c-…` | per-execution join |
| `executionHistory[].timestamp` | epoch ms | task timing |
| `executionStatus` | `succeed`/`failed`/`running`/`queued` | **native outcome signal** |
| `createdAt` / `updatedAt` | epoch ms | time-to-complete per task |
| (multiple executions) | task 5 = 3 runs | **native retry/restart signal** |

### From the SESSION JSON — full conversation, no tokens
| Field | Example | Use |
|---|---|---|
| `history[].message.role` | `user` / `assistant` | turn role |
| `history[].message.content` | full text | **prompt+completion (we never transmit)** |
| `history[].executionId` | `ff2b82a7-…` | **joins to task meta** |
| `contextItems[]` | attached context | context size signal |
| `promptLogs[].modelTitle` | `Agent` | which model/mode |
| `promptLogs[].completionOptions.model` | `agent` | model id |
| `promptLogs[].completionOptions.maxTokens` | `4000` | **ceiling only — NOT actual usage** |
| folder name (workspace-sessions) | Base64 → real path | **per-project attribution** |

## Token fidelity: **NO trustworthy local cost source** (verified by exhaustion)
Kiro inverts the Claude Code pattern: local files are excellent for *attribution/quality* but useless for *cost*. Four candidate sources were checked with real data; none gives recoverable cost:

| Candidate local source | What's there | Why it fails for cost |
|---|---|---|
| Session JSON + `default\*.chat` (60+ files) | full conversation text, `maxTokens` ceiling | no token usage at all |
| `dev_data\devdata.sqlite` `tokens_generated` table | `model, provider, tokens_prompt, tokens_generated, timestamp` | **output always 0** for `provider:kiro/model:agent`; **5,843 rows, 36.4M prompt tokens, 0 generated**; data runs Aug 2025–Feb 2026 (**ends because user stopped using Kiro in Feb — NOT a logging failure; mechanism is valid**); no session/task join key |
| `dev_data\tokens_generated.jsonl` | same shape, still appending today | same: input-only, no join, model masked as `"agent"` |
| Credit balance (the real $ unit) | — | not cached on disk locally; BUT **fully available server-side via AWS** (see below) |

Kiro bills in **credits** (fractional, complexity-based — vibe/spec requests), not tokens. The only `model:"agent"` mask hides the real Bedrock-Claude model, so even the input tokens can't be priced locally. The non-zero rows are a different provider (`qdev` = Amazon Q Developer path), which DOES log input+output.

## Source 2 — AWS server-side cost (VERIFIED from Kiro docs): FOUR channels
For teams/enterprise with admin access, Kiro cost is cleanly and programmatically available:

| Channel | What it gives | Access |
|---|---|---|
| **S3 daily per-user CSV** (PRIMARY) | credits, messages, conversations, client type (IDE/CLI/Plugin), per user — daily at 02:00 UTC to your S3 bucket | admin enables user-activity report export → S3; query via Glue/Athena (AWS ships a sample Streamlit dashboard doing exactly this) |
| **AWS Cost & Usage Report (CUR)** | exact $ per user (subscription cost) with resource IDs → **the CFO number (KPI 3)** | Billing & Cost Management → Data Exports, "Include resource IDs" |
| **CloudTrail** | API calls / invocation events on behalf of the account | standard CloudTrail → S3 |
| **CloudWatch** | invocation counts, daily active users, custom alarms | CloudWatch metrics |
| **Kiro admin dashboard** | aggregate + per-user metrics, hourly refresh | Kiro console (AWS), admin only |

Auth for programmatic access: **Kiro API key** (Pro/Pro+/Power), created at app.kiro.dev; credits used via API key decrement the subscription. NOTE: console shows both "Amazon Q" and "Kiro" branding post-rebrand — target the **Kiro console / app.kiro.dev** path specifically.

### S3 daily activity CSV — VERIFIED exact schema (from AWS sample dashboard repo)
Fixed 11-column schema (not variable-width — the model-message variant is a different report):

| Column | Type | Meaning |
|---|---|---|
| `date` | string | activity day (YYYY-MM-DD) |
| `userid` | string | **IdP user ID — JOIN KEY** (resolvable to name/email via `identitystore.describe_user`) |
| `client_type` | string | `KIRO_IDE` / `KIRO_CLI` / `PLUGIN` |
| `chat_conversations` | int | conversations that day |
| `credits_used` | double | **THE COST UNIT** — base-plan credits consumed |
| `overage_cap` | double | overage limit (or plan max if overage off) |
| `overage_credits_used` | double | credits used beyond cap |
| `overage_enabled` | string | overage on/off |
| `profileid` | string | profile — **bridge to local Kiro profile** |
| `subscription_tier` | string | Pro / ProPlus / Power |
| `total_messages` | int | prompts + tool calls + responses |

**Granularity = per-user-per-day-per-client.** NO session/task/branch/ticket in this CSV. The finest unit is "userid spent X credits on date Y via client_type Z."

**Pipeline (verified from repo):** S3 daily CSV → Glue crawler (auto-discovers table) → Athena SQL → app. We replicate this server-side. Path: `s3://{bucket}/AWSLogs/{accountId}/KiroLogs/user_report/{region}/`. Identity resolution via IAM Identity Center (`identity_store_id`).

**Ready-made KPI queries (from repo):**
- KPI 4 (period spend): `SELECT date, SUM(credits_used), SUM(overage_credits_used) GROUP BY date`
- KPI 1/3 base: `SELECT userid, month, SUM(credits_used) GROUP BY userid, month`
- cost by surface: `SELECT client_type, SUM(credits_used) GROUP BY client_type`

### Local↔S3 attribution (the one Kiro-specific design piece)
S3 cost is daily; local task/session detail is granular. To get per-task cost:
```
allocate each day's S3 credits_used (for a userid) across that userid's
local task-sessions on the same date, weighted by activity (messages/turns/duration)
```
This daily-credit→task allocation is Kiro's extra step. Claude Code doesn't need it (per-turn cost is native); Kiro's real cost only exists at day granularity server-side.

### Second CSV — subscription export (Kiro Console, on-demand)
`Download CSV` on Users & Groups → subscription/tier/license fields per user. Use alongside the activity CSV (who is licensed at what tier vs how much they actually used).

**Conclusion:** Kiro cost = **Source 2 (AWS S3 CSV + CUR)** for teams, which is clean and programmatic. Local `dev_data` is a valid secondary (real input-token history for the period used) but cannot price on its own. This is the opposite of Claude Code Pro, where local IS the only source.

```
Claude Code Pro → cost from LOCAL (exact), no API
Kiro (team)     → cost from AWS S3 daily CSV + CUR (credits + $), clean & programmatic
Kiro (individual)→ in-IDE credit dashboard (server-side) + local dev_data (input only)
```

## Billing modes
| Account | Local source | Accuracy layer |
|---|---|---|
| Individual | ✅ session JSON (text → estimate) | ❌ none confirmed |
| Team / Pro (Amazon Q Developer) | ✅ session JSON | ⚠️ Q Developer admin dashboard — **line metrics, not tokens; Kiro→Q mapping UNVERIFIED** |

The Amazon Q Developer dashboard exposes per-user metrics (`Inline_AICodeLines`, `Dev_GeneratedLines`, `Dev_AcceptedLines`, `*_RejectedLineAdditions`, `Chat_MessagesSent`, etc.) — all **line/event based, zero token/cost**. Whether a Kiro team deployment surfaces this same dashboard is **not yet verified** (Kiro and Amazon Q Developer are distinct AWS products).

## Powers which KPIs
- **KPI 1/3/4 (cost):** weak — must estimate tokens from local text; no exact source for individuals
- **KPI 2 (efficiency):** **strong** — `executionStatus` + retry count are native; Q dashboard's generated-vs-accepted lines = churn at source
- **KPI 5 (hallucination):** **strong & native** — `failed` status + multiple executions per task = struggle signal with no inference
- **KPI 6 (trend):** task success rate over time

## Git context
- Repo attribution does **not** need git worktree mapping — the Base64 `workspace-sessions` folder name decodes to the real project path
- `specUri` also embeds the repo path
- Real LOC/churn still from `git diff --numstat` against the decoded workspace path

## Gaps + how we fill them
| Gap | Fill |
|---|---|
| Local has no priceable cost (input-only, model masked) | **Pull cost from AWS S3 daily per-user CSV (credits) + CUR ($)** — verified available for teams |
| Local `dev_data` is input-only | Valid secondary signal (input-token volume, timestamps) for the period actually used; not a cost source |
| Individual users (no admin/S3 export) | In-IDE credit dashboard (server-side) + local `dev_data`; no clean programmatic export at individual tier |
| `model:"agent"` mask | Real model/cost resolved server-side via S3 CSV / CUR, not locally |
| Real LOC/churn | `git diff --numstat` on the decoded Base64 workspace path (numbers only) |

## Access method
**Split — and both halves verified:** Agent reads **local files** for *attribution + quality* (task model `executionId`/status/retries, `.chat`/session text, Base64 workspace→project, `dev_data` input-token history). Backend pulls **AWS S3 daily per-user CSV** (credits, messages, per client) + **CUR** (exact $) for *cost*, authenticated via Kiro API key. Kiro is a **Source 1 (attribution) + Source 2 (cost)** tool — unlike Claude Code Pro (Source 1 only).

---

# TOOL #3 — VS Code + GitHub Copilot  ✅ COMPLETE

**Verified by reading real VS Code storage.** Copilot Chat stores conversation text + model + timing locally, but **no token counts** and **no cost** — cost is server-side (GitHub). Key finding: **VS Code Chat is a multi-model router** — some "Copilot" sessions actually run Claude Code as the backend, creating a double-count risk.

## Storage: VS Code-native (per-workspace + global SQLite)

```
workspaceStorage\<hash>\chatSessions\<uuid>.json  ── per-workspace chat (text, no tokens)
workspaceStorage\<hash>\state.vscdb               ── per-workspace SQLite
workspaceStorage\<hash>\workspace.json            ── maps hash → real repo path (attribution)
globalStorage\state.vscdb  ItemTable              ── session index, model prefs, model cache
globalStorage\github.copilot-chat\               ── agent .md configs, CLI launcher scripts (no data)
```

### Exact paths (Windows)
```
CHAT SESSIONS: %APPDATA%\Code\User\workspaceStorage\<hash>\chatSessions\<uuid>.json
WORKSPACE MAP: %APPDATA%\Code\User\workspaceStorage\<hash>\workspace.json
GLOBAL STORE:  %APPDATA%\Code\User\globalStorage\state.vscdb  (table: ItemTable)
SESSION INDEX: key `chat.ChatSessionStore.index` inside the global state.vscdb
```

## Fields available (from real data)

### Chat session JSON (`chatSessions\<uuid>.json`)
| Field | Example | Use |
|---|---|---|
| `requesterUsername` | `Adnan029` | **GitHub identity → join key** |
| `responderUsername` | `GitHub Copilot` | responder |
| `sessionId` | `401e5069-…` | session id |
| `creationDate` / `lastMessageDate` | epoch ms | timing |
| `requests[]` | (text turns) | prompt/response text — **no token counts** |
| `initialLocation` | `panel` | surface |

### Session index (`chat.ChatSessionStore.index` in global state.vscdb) — the gold field
| Field | Example | Use |
|---|---|---|
| `title` | "Design multi-service monorepo CI/CD…" | auto-summary |
| `selectedModel.identifier` | `claude-code/claude-haiku-4.5` | **actual model used** |
| `selectedModel.vendor` | `claude-code` | **model vendor — detects routing** |
| `mode.kind` | `agent` | chat vs agent mode |
| `timing.created / lastRequestStarted / lastRequestEnded` | epoch ms | **per-request timing** |
| `isExternal` | `true` | **data lives in another tool's store** |
| `isEmpty` | `false` | populated or not |
| `sessionId` | `claude-code:/cbc2a536-…` | **prefix reveals backend tool** |

Other useful global keys: `chatModelRecentlyUsed`, `chat.cachedLanguageModels.v2`, `chat.currentLanguageModel.panel.claude-code`, `chat.modelsControl`.

## Token fidelity: **NO local tokens; cost is server-side via GitHub API** (and improving June 1, 2026)
Chat sessions are text + model + timing only. Searched global + workspace stores: **no premium/quota/entitlement/billing keys.** Cost lives **server-side at GitHub**, but it IS retrievable — verified channels:

### Source 2 — GitHub Copilot usage/billing (VERIFIED, programmatic)
| Channel | What it gives | Access |
|---|---|---|
| **Org metrics REST API** | Copilot usage metrics per org | `GET /orgs/{org}/copilot/metrics` (Bearer token, `X-GitHub-Api-Version`) |
| **Premium-request billing API** | premium-request usage report for an org | `GET .../billing/usage` premium-request report endpoint |
| **Async usage report (CSV)** | **one row per user, per model, per day** | request via API/console → generated async → emailed to admin |
| **Org-level dashboard** | adoption/usage metrics (public preview Feb 2026) | org admins, no enterprise tier needed |
| **In-editor display** | user's own usage vs limit | VS Code Copilot status-bar icon |

Granularity (per user / per model / per day) ≈ Kiro's S3 CSV — **same join shape** (user + day + model).

### ⚠️ BILLING MODEL CHANGES June 1, 2026 — improves fidelity in our favor
- **Before:** unit = **premium requests** (1 prompt = 1 request × model multiplier; coarse; agentic tool-calls were free)
- **After (June 1, 2026):** unit = **GitHub AI Credits = TOKENS** (input + output + cached, at per-model API rates)
- Net: Copilot cost becomes **token-accurate**, matching Claude Code's fidelity. The "no token granularity" weakness is fixed by GitHub itself.
- Side effect: agentic/autonomous work that was "free" under premium-requests now **consumes tokens** → cost profile of agent sessions rises post-June-1.

```
Claude Code  → tokens, local        → EXACT (local)
Kiro         → credits, AWS S3       → cost via AWS
Copilot      → premium-reqs → TOKENS (June 1 2026), GitHub API → server-side, token-accurate soon
```

## ⚠️ Critical edge case: multi-model routing & double-counting
VS Code Chat is a **router**. Real proof from this machine: a "Copilot" session index entry had
`sessionId: claude-code:/cbc2a536-…` — **the exact same ID as the Claude Code JSONL in Tool #1.**
The work ran through the Copilot UI but executed on **Claude Haiku 4.5 via the claude-code backend**, and VS Code flags it `isExternal: true`.

**Implication:** the same session can appear in BOTH Copilot's index AND Claude Code's store. Naive summing double-counts cost.
**Dedupe rule:** if `selectedModel.vendor == "claude-code"` OR `sessionId` starts with `claude-code:/` OR `isExternal == true` → the authoritative data is the external tool's store (Claude Code JSONL); count it once, there.

## Billing modes
| Account | Local cost? | Cost source |
|---|---|---|
| Individual (Free/Pro/Pro+) | ❌ | GitHub Copilot usage/billing (server-side); premium-request metering |
| Business / Enterprise | ❌ | GitHub org Copilot metrics + billing API (per-seat + premium requests) |

## Powers which KPIs
- **KPI 1/3/4 (cost):** weak locally — needs GitHub usage API (server-side); local has no tokens/cost
- **KPI 2 (efficiency):** medium — session count, per-request timing, model used; text for local-only estimation if ever needed
- **KPI 5 (hallucination):** medium — request timing + session restarts; file oscillation from git, not Copilot
- **KPI 6 (trend):** model-mix and session trends over time

## Git context
- `workspace.json` maps the workspace hash → real repo path (URL-encoded `file:///c%3A/...`) → attribution
- Real LOC/churn from `git diff --numstat` against that repo (numbers only)

## Gaps + how we fill them
| Gap | Fill |
|---|---|
| No local tokens | GitHub Copilot usage API (server-side) for cost; local text estimate only if necessary |
| No local cost/premium-request count | GitHub org billing/usage API |
| Multi-model double-count | Dedupe via `vendor==claude-code` / `claude-code:/` prefix / `isExternal` → count in source tool |
| Which workspace = which repo | `workspace.json` decode |

## Access method
**Split:** Agent reads local `chatSessions` + global `state.vscdb` session index for *attribution, model, timing, dedupe flags*. Backend pulls **GitHub Copilot usage/billing API** for *cost* (premium requests, per-seat). Always apply the dedupe rule so Claude-routed sessions aren't counted twice.

---

# Architecture note — DECLARED TOOLS AT INSTALL (locked decision)

The agent does **not** blind-scan every possible store. At install, the developer/admin **declares which tools the team uses**, and the agent loads only those parsers.

```
VibeROI agent install → "Which AI tools does your team use?"
  ☑ Claude Code   ☑ GitHub Copilot   ☐ Cursor
  ☐ Kiro          ☐ Windsurf         ☐ JetBrains AI
→ agent loads only selected parsers; ignores the rest
```

Why this is better, not just easier:
- **Faster / leaner** — no crawling dead or empty stores
- **Privacy & security** — scoped file access is far easier for enterprise IT to approve than broad AppData scanning
- **Informs dedupe** — declaring "Copilot + Claude Code" tells the agent to expect and dedupe `isExternal`/`claude-code:/` routed sessions (the double-count edge case)
- **Same philosophy as branch-naming/tagging** — a little declared structure up front buys clean, attributable data later

This is an onboarding step, mirroring the "tagging discipline" principle: light setup → clean data.

---

# TOOL #4 — Cursor (standalone VS Code-fork IDE)  ✅ COMPLETE

**Verified by reading real bytes — the richest local source of any tool.** EXACT per-message tokens locally (proven: summed 4.68M input / 226K output across 1,395 bubbles via one SQL query), PLUS native AI-code-to-git-commit tracking, PLUS server join keys for billing reconciliation.

## Storage: one big SQLite (107 MB), two tables

```
state.vscdb (107 MB)
├─ ItemTable      ── settings, auth, aiCodeTracking* (AI-code→commit map)
└─ cursorDiskKV   ── the AI brain:
     composerData:<id>   ── conversation header (createdAt, mode, git context)
     bubbleId:<composer>:<bubble>  ── per-MESSAGE: tokenCount, tools, code, git
     checkpointId:<id>   ── checkpoints
     codeBlockDiff:<id>  ── code diffs
```

### Exact paths (Windows)
```
DB:        %APPDATA%\Cursor\User\globalStorage\state.vscdb   (tables: ItemTable, cursorDiskKV)
BUBBLES:   cursorDiskKV  key = bubbleId:<composerId>:<bubbleId>   (1,424 on this machine)
COMPOSERS: cursorDiskKV  key = composerData:<composerId>          (~24 conversations)
AI-CODE:   ItemTable     key = aiCodeTrackingLines (1.4MB, ~9,696 commit-hash→composer maps)
EMBEDDED EXTENSIONS: globalStorage\saoudrizwan.claude-dev (Cline runs inside Cursor too)
```

## Fields available (from real data)

### Per-message bubble (`bubbleId:…`) — EXACT tokens + huge context
| Field | Example | Use |
|---|---|---|
| `tokenCount.inputTokens` | `110837` | **EXACT input per message** |
| `tokenCount.outputTokens` | `19039` | **EXACT output per message** |
| `serverBubbleId` | (uuid) | **join to Cursor server record** |
| `usageUuid` | (uuid) | **join to Cursor usage/billing API** |
| `requestId` | (uuid) | per-request server linkage |
| `isRefunded` | `false` | **refunded request = no charge** (cost signal) |
| `isAgentic` | `false` | agent vs chat mode |
| `toolFormerData` | `{tool, name:"list_dir", args, result}` | **tool calls → files touched, oscillation** |
| `codeBlocks` / `suggestedCodeBlocks` | … | code produced |
| `gitDiffs` / `commits` / `pullRequests` | … | **git context attached to message** |
| `allThinkingBlocks` | … | thinking content |
| `type` | `2` | message/turn type |

### Conversation header (`composerData:…`)
| Field | Example | Use |
|---|---|---|
| `composerId` | `750ff9d2-…` | conversation id |
| `createdAt` | `1753955141580` | start time |
| `unifiedMode` / `forceMode` | `chat` / `agent` | mode |
| `isAgentic` | `false` | agent flag |
| `usageData` | `{}` | usage slot (server-populated) |
| `context.selectedCommits / selectedPullRequests / gitDiff` | … | git context |

### `aiCodeTrackingLines` (ItemTable) — NATIVE AI-code→commit attribution
| Field | Example | Use |
|---|---|---|
| `hash` | `7adc7be` | **git commit hash containing AI code** |
| `metadata.source` | `composer` | produced by a conversation |
| `metadata.composerId` | `d35684be-…` | **which conversation produced it** |
| scale | ~9,696 entries | whole-history AI-code-to-commit map |

## Token fidelity: **EXACT (per-message, local)** — proven
One SQL query summed real tokens across all bubbles:
```sql
SELECT SUM(json_extract(value,'$.tokenCount.inputTokens')),
       SUM(json_extract(value,'$.tokenCount.outputTokens'))
FROM cursorDiskKV WHERE key LIKE 'bubbleId:%';
-- → 4,683,779 input / 226,647 output across 1,395 bubbles
```
Tool-call bubbles correctly show 0/0 (no model tokens); assistant generations carry real counts. `json_extract` works natively on the SQLite → trivial parser.

```
EXACT local cost:  Claude Code ✅,  Cursor ✅   ← the two dedicated AI-coding tools
Server-side cost:  Kiro (AWS S3),  Copilot (GitHub API)
```

## Billing modes
| Account | Local | Server reconciliation |
|---|---|---|
| Individual (Pro/Free) | ✅ exact tokens in DB | Cursor usage API via `usageUuid`/`serverBubbleId` (auth token in `cursorAuth/accessToken`) |
| Business / Teams | ✅ exact tokens in DB | Cursor admin/usage API (org-level) |

Cursor bills by request (model-dependent, "included" vs usage-based pricing). Local tokens give exact consumption; server API confirms billed amount and refunds (`isRefunded`).

## Powers which KPIs
- **KPI 1/3/4 (cost):** **STRONG** — exact per-message tokens locally; sum per composer/branch/ticket
- **KPI 2 (efficiency):** **STRONG** — `aiCodeTrackingLines` gives AI lines by commit; tool calls show churn; per-message tokens show spikes
- **KPI 5 (hallucination):** **STRONG** — per-message token series (spikes), `toolFormerData` file ops (oscillation), `isRefunded` (failed requests)
- **KPI 6 (trend):** all of the above over time

## Git context — best of any tool
- `aiCodeTrackingLines` maps **AI code → commit hash → composerId** natively (the attribution chain, pre-built)
- Each bubble carries `gitDiffs` / `commits` / `pullRequests`
- Real LOC/churn still cross-checked via `git diff --numstat`; but Cursor's own tracking is a strong primary signal

## ⚠️ Edge case: embedded extensions (Cline)
`globalStorage\saoudrizwan.claude-dev` = the **Cline** extension running *inside* Cursor. Its sessions are a separate store (Cline's own), not Cursor's `cursorDiskKV`. Same multi-tool overlap pattern as Copilot↔Claude — declare + dedupe so Cline usage isn't double-counted as Cursor.

## Gaps + how we fill them
| Gap | Fill |
|---|---|
| Model name not in obvious field (`modelType` absent) | Model is recorded elsewhere (composer/usageData or server); resolve via `usageUuid`→API, or per-composer model setting |
| Server-billed amount vs local tokens | Reconcile via `usageUuid`/`serverBubbleId` → Cursor usage API |
| Refunds | `isRefunded` per bubble — exclude from cost |
| Cline-in-Cursor overlap | Declared-tools + dedupe |
| Real LOC | `git diff --numstat`, cross-checked with `aiCodeTrackingLines` |

## Access method
**Agent reads the SQLite directly** (`json_extract` on `cursorDiskKV`) — exact tokens, tool calls, git context, and the AI-code→commit map, all local. Backend *optionally* hits Cursor's usage API via `usageUuid` for billed-amount/refund reconciliation. Cursor is **Source 1-dominant** (like Claude Code) with an optional Source 2 accuracy layer.

---

*Next tools to verify: **Windsurf** and **JetBrains AI** — neither installed. Per the "real data at any cost" rule: install, generate a session, read real bytes before documenting (don't rely on docs alone).*

---

# SESSION OBJECT SCHEMA — LOCKED ✅

**Version:** 1.0 | **Locked:** 2026-05-28 | **Decisions applied:** tool_calls=file-paths-only, pricing_model=struct, subagents=rolled-up, reconciliation=single-object-with-flag

## Design principles
- One session object = one AI working session on one branch
- Only stores what was *observed* — computed KPIs are derived at query time
- Never stores prompt text, code content, or args/results — only metadata
- Every field has a verified source from a real tool's local store or API

```json
{
  // ── IDENTITY ──────────────────────────────────────────────────────────────
  "session_id":   "local_d7f613d2-dd58-4cc5-9238-a819ae844f4b",
  "developer_id": "dev_adnan_123",
  "org_id":       "org_rapyder_456",

  // ── TOOL ──────────────────────────────────────────────────────────────────
  "tool": {
    "name":         "claude-code",        // claude-code | cursor | kiro | copilot
    "surface":      "desktop_app",        // desktop_app | cli | vscode_extension
    "version":      "2.1.128",
    "model":        "claude-sonnet-4-6",
    "capture_mode": "local_exact",        // local_exact | local_estimated | api_only
    "pricing_model": {
      "type":     "subscription",         // subscription | api_key | credits | seat
      "unit":     "tokens",               // tokens | credits | premium_requests
      "rate_usd": 0.000003               // per unit cost; 0 if flat subscription
    }
  },

  // ── TIMING ────────────────────────────────────────────────────────────────
  "timing": {
    "started_at":              "2026-05-06T09:28:35Z",  // INDEX createdAt / composerData.createdAt
    "ended_at":                "2026-05-06T10:42:55Z",  // INDEX lastActivityAt / last bubble ts
    "active_duration_min":     74,
    "first_commit_at":         "2026-05-06T10:55:00Z",  // from git log (null if none)
    "time_to_first_commit_min": 86                       // KPI 2 signal
  },

  // ── TOKENS ────────────────────────────────────────────────────────────────
  "tokens": {
    "input":          3,          // JSONL message.usage.input_tokens / bubble tokenCount.inputTokens
    "output":         226,        // JSONL message.usage.output_tokens / bubble tokenCount.outputTokens
    "cache_read":     163906,     // Claude Code only: cache_read_input_tokens
    "cache_write":    188,        // Claude Code only: cache_creation_input_tokens
    "total_cost_usd": 0.0042,     // computed from tokens × pricing_model.rate_usd
    "is_estimated":   false,      // false = exact local; true = estimated or API-sourced
    "reconciled":     false,      // true = API accuracy layer has confirmed/corrected cost
    "reconciled_at":  null        // ISO timestamp of last reconciliation
  },

  // ── ACTIVITY ──────────────────────────────────────────────────────────────
  "activity": {
    "turn_count":      4,          // completedTurns (audit) / bubble count / requests[].length
    "mode":            "agent",    // agent | chat | plan | edit | ask
    "is_agentic":      true,       // Claude Code permissionMode=acceptEdits / bubble.isAgentic
    "subagent_count":  4,          // Claude Code only: number of subagent JSONL files
    "files_touched": [             // from tool_use Write/Read/Edit calls — paths only, no content
      "src/payments/gateway.ts",
      ".husky/pre-commit"
    ],
    "files_touched_count": 2
  },

  // ── CODE OUTPUT ───────────────────────────────────────────────────────────
  "code_output": {
    "lines_added":         47,    // git diff --numstat (committed) or dirty-diff (uncommitted)
    "lines_deleted":       12,
    "lines_accepted":      38,    // Cursor: aiCodeTrackingLines / Kiro: Q dashboard accepted lines
    "lines_reverted":      9,     // lines_added - lines_accepted
    "is_committed":        true,  // git status check at session end
    "commit_hashes":       ["7adc7be", "ce34db2"],  // git log (Cursor: aiCodeTrackingLines)
    "uncommitted_at_end":  false  // if true: KPI 5 Condition D trigger
  },

  // ── REPOSITORY ────────────────────────────────────────────────────────────
  "repository": {
    "name":            "wvp-backend",
    "origin_cwd":      "C:/Users/AdnanKhan/wvp-backend",  // real repo root, not worktree
    "branch":          "feature/JIRA-142-payment-gateway", // resolved real branch
    "raw_branch":      "claude/xenodochial-joliot-361764", // as recorded by tool (worktree)
    "is_worktree":     true                                 // Claude Code only
  },

  // ── ATTRIBUTION ───────────────────────────────────────────────────────────
  "attribution": {
    "ticket_id":    "JIRA-142",      // parsed from branch name / Kiro taskId / Copilot workspace
    "epic_id":      "EPIC-12",       // from ticketing API (Jira/Linear) — populated asynchronously
    "sprint_id":    "SPRINT-42",     // from ticketing API — populated asynchronously
    "confidence":   0.87,            // 1.0 for Kiro native / computed for others
    "signals": [                     // what drove the attribution
      "branch_match",                // branch name contains ticket ID
      "file_overlap",                // files touched match ticket's PR files
      "temporal_proximity"           // session time overlaps ticket active period
    ],
    "method":       "branch_parse"   // branch_parse | kiro_native | manual
  },

  // ── QUALITY SIGNALS ───────────────────────────────────────────────────────
  "quality": {
    "session_restarts":       0,      // sessions opened for same ticket in 4h window
    "file_oscillations":      1,      // same file modified >N times in session
    "token_spike_detected":   false,  // turn token count >3× session avg
    "no_commit_duration_min": 0,      // minutes of session with no commit (KPI 5 D)
    "is_refunded":            false,  // Cursor only: bubble.isRefunded
    "hallucination_risk":     "none"  // none | watch | alert (computed from above signals)
  },

  // ── METADATA ──────────────────────────────────────────────────────────────
  "meta": {
    "captured_at":   "2026-05-06T10:43:00Z",
    "agent_version": "0.1.0",
    "data_sources":  ["local_jsonl", "git_diff", "worktree_map"], // what fed this object
    "schema_version": "1.0"
  }
}
```

## Field source map — where each field comes from per tool

| Field | Claude Code | Cursor | Kiro | Copilot |
|---|---|---|---|---|
| `session_id` | INDEX `sessionId` | `composerData.composerId` | `audit.jsonl session_id` | `chatSessions uuid` |
| `tool.model` | `message.model` | via `usageUuid` API | `dev_data model` | `selectedModel.id` |
| `timing.started_at` | INDEX `createdAt` | `composerData.createdAt` | `task.createdAt` | `creationDate` |
| `timing.ended_at` | INDEX `lastActivityAt` | last bubble timestamp | `task.updatedAt` | `lastMessageDate` |
| `tokens.input` | JSONL `input_tokens` | bubble `tokenCount.inputTokens` | `dev_data tokens_prompt` | ❌ API only |
| `tokens.output` | JSONL `output_tokens` | bubble `tokenCount.outputTokens` | ❌ not recorded | ❌ API only |
| `tokens.cost_usd` | computed local | computed local | AWS S3 CSV `credits_used` | GitHub usage API |
| `tokens.is_estimated` | `false` | `false` | `true` | `true` |
| `activity.turn_count` | `completedTurns` | bubble count | `executionHistory` count | `requests[]` count |
| `activity.mode` | `permissionMode` | `composerData.unifiedMode` | task type | session mode |
| `activity.is_agentic` | audit `apiKeySource` | bubble `isAgentic` | always `true` | mode check |
| `activity.files_touched` | tool_use `file_path` | bubble `toolResults` paths | ❌ not present | ❌ not present |
| `code_output.lines_added` | `git diff --numstat` | `git diff --numstat` | `git diff --numstat` | `git diff --numstat` |
| `code_output.lines_accepted` | ❌ not present | `aiCodeTrackingLines` ✅ | Q dashboard | ❌ not present |
| `code_output.commit_hashes` | `git log` | `aiCodeTrackingLines` ✅ | `git log` | `git log` |
| `repository.branch` | INDEX `sourceBranch` | workspace Base64 decode | `specUri` path | `workspace.json` |
| `attribution.ticket_id` | branch name parse | branch name parse | `taskId` (native ✅) | branch name parse |
| `attribution.confidence` | computed | computed | `1.0` native | computed |
| `quality.session_restarts` | session count/ticket | `executionHistory` retries | `executionStatus` fails | session count |
| `quality.file_oscillations` | tool_use paths | bubble tool paths | ❌ | ❌ |
| `quality.token_spike` | per-turn series | per-bubble series | ❌ | ❌ |
| `quality.is_refunded` | ❌ | bubble `isRefunded` ✅ | ❌ | ❌ |

## Nullable fields by tool
Fields marked ❌ above are stored as `null` when not available. The schema is always the same shape regardless of tool — parsers fill what they can, null the rest.

---

# SOURCE 3 — VERSION CONTROL + TICKETING (Q1 + Q2 + Q3)

**Purpose:** Provide attribution context and ground truth for what the AI work was *for*. Local files (Source 1) tell us what happened; Source 3 tells us which ticket, which sprint, which PR it shipped in.

**Connection model:** GitHub App / OAuth 2.0 for all tools. Read-only scopes only. Webhooks push events to our backend in real time; REST/GraphQL API used for initial sync and backfill.

**Privacy rule:** We read ticket titles, IDs, sprint names, PR metadata, branch names, commit hashes, file paths, timestamps. We NEVER read commit diffs, PR descriptions, or code content.

---

## The JOIN KEY that connects everything

```
Branch name  →  Ticket ID  →  Epic  →  Sprint
"feature/JIRA-142-payment-gateway"
              ↑ parsed here
              JIRA-142 → queried from Jira API → epic EPIC-12, sprint SPRINT-42

Same pattern for Linear:
"feature/ENG-89-auth-refactor"
              ENG-89 → Linear GraphQL → cycle, project, team

For GitHub Issues:
"feature/123-fix-login"
              #123 → GitHub Issues API → milestone (= sprint proxy)
```

Branch naming convention is the **only required discipline** from developers. Without it, attribution confidence drops to ~40%. This is the "tagging" requirement documented earlier.

---

## Version Control Tools

### GitHub ✅ TIER 1

**Connection:** GitHub App (preferred over OAuth — scoped per-repo, no user token expiry)
**Scopes needed (read-only):** `contents:read`, `pull_requests:read`, `metadata:read`
**Webhook delivery:** HTTPS POST, HMAC-SHA256 signed (`X-Hub-Signature-256`)

**Events we subscribe to (from 73+ available):**

```
push                → branch push: developer committed
pull_request        → opened / closed / merged / synchronized
  action: opened    → PR raised, links branch to reviewers
  action: closed    → if merged: true → ticket work shipped
  action: synchronize → new commit pushed to open PR
create              → branch created (session start signal)
delete              → branch deleted (session end signal)
```

**Fields from `push` event we capture:**

```
ref                 → "refs/heads/feature/JIRA-142-..."  → branch name
after               → commit SHA (head after push)
before              → commit SHA (head before push)
repository.name     → repo name
repository.full_name → org/repo
pusher.name         → GitHub username (join key to developer)
commits[].id        → commit hash
commits[].timestamp → commit time
commits[].added[]   → file paths added (NO content)
commits[].modified[]→ file paths modified (NO content)
commits[].removed[] → file paths removed (NO content)
forced              → force push flag
```

**Fields from `pull_request` event we capture:**

```
action                  → opened | closed | synchronize | merged
pull_request.number     → PR number
pull_request.title      → PR title
pull_request.state      → open | closed
pull_request.merged     → true/false
pull_request.merged_at  → merge timestamp
pull_request.created_at → PR open timestamp
pull_request.head.ref   → source branch (feature/JIRA-142-...)
pull_request.base.ref   → target branch (main/develop)
pull_request.user.login → author (developer join key)
pull_request.additions  → lines added in PR
pull_request.deletions  → lines deleted in PR
pull_request.changed_files → file count
pull_request.commits    → commit count
pull_request.review_comments → review iteration count
```

**KPIs powered:**
- KPI 12: Spend by feature — PR merged = ticket closed signal
- KPI 21: AI-assisted vs human cycle time — PR open → merge timestamps
- KPI 22: Lifecycle decomposition — prompt→commit, commit→PR, PR→merge stages
- Attribution confidence boost — branch name + PR author = strong signal

**GitLab push limit note:** GitLab limits webhook triggers for push events that include more than 3 branches by default — no webhook fires if exceeded. Handle by supplementing with polling for high-volume push orgs.

---

### GitLab ✅ TIER 1

**Connection:** GitLab OAuth 2.0 + webhook registration via API
**Auth:** OAuth 2.0 (cloud) or Personal Access Token (self-hosted)
**Webhook header:** `X-Gitlab-Event` (event type) + `X-Gitlab-Token` (secret)
**Self-hosted note:** System hooks available for admin-level cross-project events

**Events we subscribe to:**

```
Push Hook           → code push, branch activity
Merge Request Hook  → opened / updated / merged / closed
  object_attributes.action:
    open    → MR raised
    update  → new commits pushed
    merge   → work shipped
    close   → abandoned
```

**Key fields from Push Hook:**

```
ref                         → branch name
checkout_sha                → HEAD commit
commits[].id                → commit hash
commits[].timestamp         → commit time
commits[].added/modified/removed → file paths (no content)
project.name                → repo name
project.path_with_namespace → org/repo
user_username               → developer join key
```

**Key fields from Merge Request Hook:**

```
object_attributes.action    → open | update | merge | close
object_attributes.iid       → MR number
object_attributes.title     → MR title
object_attributes.state     → opened | merged | closed
object_attributes.created_at / merged_at
object_attributes.source_branch → feature branch (attribution!)
object_attributes.target_branch → base branch
object_attributes.url       → MR URL
user.username               → author
```

**GitLab-specific advantage:** Group webhooks (Premium+) receive events from ALL projects in a group — single webhook for multi-repo orgs. Push events include branch name, before/after commit SHAs, and who pushed.

---

### Bitbucket ✅ TIER 2

**Connection:** OAuth 2.0 (Cloud) or HTTP Basic/Bearer (Data Center)
**Note:** Bitbucket Cloud and Data Center have separate APIs

**Events we subscribe to:**

```
repo:push               → push to branch
pullrequest:created     → PR opened
pullrequest:updated     → new commits
pullrequest:fulfilled   → PR merged ← use this for "ticket shipped"
pullrequest:rejected    → PR closed without merge
```

**Key fields (Cloud):**

```
push.changes[].new.name     → branch name (attribution key)
push.changes[].commits[].hash → commit hash
pullrequest.source.branch.name → feature branch
pullrequest.destination.branch.name → target
pullrequest.author.account_id → developer
pullrequest.created_on / updated_on / merge_commit.hash
```

**Integration note:** Bitbucket Cloud and Jira share Atlassian identity — `account_id` from Bitbucket webhooks is the same `accountId` in Jira. Natural join with no extra mapping needed for Atlassian shops.

---

### Azure DevOps Repos ✅ TIER 2

**Connection:** Azure DevOps Service Hooks (webhook equivalent) + PAT or OAuth
**Events:** Git push, pull request created/updated/merged/completed
**Key advantage:** Single install covers both Repos (version control) AND Boards (ticketing) — one OAuth covers both for Microsoft shops

**Key fields from PR events:**
```
resource.pullRequestId      → PR number
resource.sourceRefName      → source branch (attribution!)
resource.targetRefName      → target branch
resource.createdBy.uniqueName → developer email
resource.creationDate / closedDate
resource.mergeStatus        → succeeded = shipped
resource.commits[].commitId → commit hashes
```

---

## Ticketing / Sprint Tools

### Jira ✅ TIER 1

**Connection:** OAuth 2.0 (cloud) or API token (server/DC)
**App type:** Atlassian Connect app or OAuth 2.0 3LO
**Key endpoint:** `GET /rest/agile/1.0/sprint/{sprintId}/issue`

**Webhook events we subscribe to:**

```
jira:issue_created      → new ticket
jira:issue_updated      → status change, sprint assignment
sprint_started          → sprint opened
sprint_closed           → sprint ended
```

**Fields we pull per ticket (REST API):**

```
issue.key               → "JIRA-142" ← the join key to branch names
issue.fields.summary    → ticket title
issue.fields.status.name → To Do | In Progress | Done
issue.fields.assignee.accountId → developer (join to Atlassian identity)
issue.fields.customfield_XXXXX  → sprint field (custom field, ID varies per org)
issue.fields.epic.key   → parent epic
issue.fields.story_points (or story_point_estimate)
issue.fields.created / updated / resolutiondate
```

**Sprint fields (Agile API):**

```
GET /rest/agile/1.0/board/{boardId}/sprint
  sprint.id, sprint.name, sprint.state (active/closed/future)
  sprint.startDate, sprint.endDate, sprint.completeDate

GET /rest/agile/1.0/sprint/{sprintId}/issue
  → all issues in sprint with their fields
```

**Critical Jira note:** Sprint is a custom field in Jira — not a standard field. The custom field ID (e.g., `customfield_11111`) varies per Jira instance and must be discovered at integration setup by calling the fields API. Our onboarding flow must auto-discover this ID per customer.

**Auth scope:** `read:jira-work` — read issues, sprints, boards. No write access ever.

---

### Linear ✅ TIER 1

**Connection:** OAuth 2.0 or Personal API Key
**API type:** GraphQL (same API Linear uses internally)
**Rate limit:** 2,000 requests/hour per API key
**Webhook signature:** HMAC-SHA256, `Linear-Signature` header

**Webhook events we subscribe to:**

```
Issue        → created, updated, removed
Cycle        → created, updated (Linear's name for sprint)
Project      → updated
```

Linear webhooks support data change events for Issues, Comments, Projects, Cycles, Labels, Users and Issue SLAs.

**GraphQL queries we run:**

```graphql
# Get issue by ID (called when branch matches ticket ID)
query GetIssue($id: String!) {
  issue(id: $id) {
    identifier      # "ENG-89" ← the join key
    title
    state { name }  # Todo | In Progress | Done
    assignee { email, displayName }
    cycle {         # = sprint in Linear
      id
      name
      number
      startsAt
      endsAt
    }
    project { id, name }
    team { id, name }
    createdAt
    completedAt
    estimate        # story points
  }
}

# Get all issues in a cycle (sprint)
query GetCycleIssues($cycleId: String!) {
  cycle(id: $cycleId) {
    issues {
      nodes {
        identifier, title, state { name }, assignee { email }
      }
    }
  }
}
```

**Linear advantage:** GraphQL means we request exactly the fields we need — no over-fetching. Cycles (sprints) are first-class objects with explicit start/end dates. Clean, modern API.

---

### GitHub Issues ✅ TIER 1

**Connection:** Same GitHub App used for version control — zero extra auth
**Events:** `issues` webhook event (created, labeled, milestoned, closed)
**Sprint proxy:** GitHub Milestones = sprint equivalent for teams using GitHub natively

**Fields from Issues API:**

```
issue.number        → #123 ← join key to branch "feature/123-..."
issue.title
issue.state         → open | closed
issue.assignee.login → developer
issue.milestone.title → sprint name proxy
issue.milestone.due_on → sprint end
issue.created_at / closed_at
issue.labels[].name  → tags (bug, feature, etc.)
```

**Note:** GitHub Issues has no native sprint concept — milestones are the closest proxy. Teams using GitHub Projects (v2) have a board/iteration model closer to sprints. We support both: milestone-based attribution and GitHub Projects iteration-based attribution.

---

### Azure DevOps Boards ✅ TIER 2

**Connection:** Same PAT/OAuth as Azure DevOps Repos — one install covers both
**API:** REST (`dev.azure.com/{org}/{project}/_apis/`)
**Sprint concept:** "Iterations" in Azure DevOps

**Key endpoints:**

```
GET _apis/work/teamsettings/iterations       → list sprints
GET _apis/wit/wiql                           → Work Item Query Language
GET _apis/wit/workitems/{id}                 → ticket detail
```

**Key fields:**

```
workItem.id             → ticket number
workItem.fields["System.Title"]
workItem.fields["System.State"]
workItem.fields["System.AssignedTo"].uniqueName → developer email
workItem.fields["System.IterationPath"]  → sprint
workItem.fields["Microsoft.VSTS.Scheduling.StoryPoints"]
workItem.fields["System.CreatedDate"] / ["Microsoft.VSTS.Common.ClosedDate"]
```

**Note:** Azure DevOps is one auth, two data streams (Repos + Boards). For Microsoft-stack enterprises this simplifies onboarding significantly.

---

### Shortcut ✅ TIER 2

**Connection:** API token, OAuth 2.0
**Webhook:** REST webhooks for story/epic/iteration events
**Sprint concept:** "Iterations"

**Key fields:**

```
story.id / story.name
story.workflow_state_id  → maps to state (In Progress, Done)
story.owner_ids[]        → developer IDs
story.iteration.name / start_date / end_date
story.epic_id
story.estimate           → story points
story.created_at / completed_at
```

---

## Tier 3 Tools (V2 — documented for completeness)

```
Tool         API type     Sprint concept    Notes
──────────────────────────────────────────────────────────
Asana        REST         Portfolios/Goals  No native sprint; sections proxy
Height       REST/WS      Sprints (native)  Clean modern API
ClickUp      REST         Sprints (native)  Flexible but noisy API
Trello       REST         No sprints        Power-ups only; very limited
Notion       REST         No sprints        Databases; very weak for sprint tracking
```

---

## Source 3 field map → session object

How Source 3 data populates the session object fields that were `null` after Source 1 capture:

```
SESSION FIELD         POPULATED FROM              TIMING
──────────────────────────────────────────────────────────────
attribution.ticket_id  branch name parse          at capture (Source 1)
attribution.epic_id    Jira/Linear API lookup     async, after capture
attribution.sprint_id  Jira sprint / Linear cycle async, after capture
attribution.confidence computed from signals      at capture + updated async
timing.first_commit_at GitHub push webhook        real-time
code_output.is_committed GitHub push webhook      real-time
code_output.commit_hashes GitHub push webhook     real-time
tickets.title          Jira/Linear REST/GraphQL   async sync
tickets.status         Jira/Linear webhook        real-time
tickets.closed_at      Jira/Linear webhook        real-time
sprints.*              Jira/Linear API            daily sync + webhook updates
```

---

## Integration setup flow (what happens when a customer connects)

```
1. Customer clicks "Connect GitHub" → OAuth GitHub App install
   → we receive: org name, repo list, install_id
   → we register webhooks for: push, pull_request, create, delete
   → we backfill: last 90 days of PR/branch data

2. Customer clicks "Connect Jira/Linear"
   → OAuth flow
   → we discover: boards, projects, custom field IDs (sprint field!)
   → we sync: all open + last-90-days tickets with sprint/epic
   → we register webhooks: issue updates, sprint events

3. Agent install on developer machines
   → declares tools (Q4 decision)
   → agent_id registered against org + developer

4. Attribution engine starts linking sessions → tickets
   → branch parse runs on every new session
   → confidence scored using signals (branch + file + temporal)
   → epic/sprint backfilled async from ticketing API
```

---

# Q5 — ATTRIBUTION ENGINE ✅ SEALED

**Purpose:** Given a session object (branch, files, timestamps, developer, tokens), determine which ticket it belongs to and how confident we are.

---

## RBAC — Who sees what

```
Org Admin    → everything: all developers, all KPIs, billing, unknown queue
Team Lead/EM → their team: all KPIs, all team sessions, unknown queue
Developer    → read-only: own sessions ONLY, own attribution
               CAN: tag own unattributed sessions
               CANNOT: see teammates' data, costs, rankings
```

Rationale: Developers need just enough transparency to trust the tool and not resist install. They see only their own data. Managers get full visibility. This is also what makes enterprise HR/security sign off.

---

## The 5 Signals + Modifiers

```
Signal 1 — Branch name parse          35%
  Regex: /([A-Z]+-\d+|ENG-\d+|#\d+)/i on branch name
  "feature/JIRA-142-payment" → JIRA-142 (confidence 1.0)
  "patch-2" → no match (0.0)
  Kiro: taskId IS Signal 1 (not bypassed — treated same as branch match)

Signal 2 — File path overlap           20% (sprint-cohesion adjusted)
  files_in_session ∩ files_in_ticket's_PR / files_in_session
  Per-file weight: 1 / number_of_tickets_touching_that_file
    → hot files decay toward zero; unique files = strong signal
  Sprint cohesion adjustment:
    Sprint >60% same epic → boost Signal 2 to 0.28
    Mixed sprint → dampen Signal 2 to 0.14

Signal 3 — Temporal proximity          15%
  Session active while ticket status = "In Progress"
  Tight overlap (same day) = 1.0, loose (same week) = 0.5

Signal 4 — Developer match             10%
  session.developer_id = ticket.assignee
  Alone = weak. Strong as tiebreaker with other signals.

Signal 5 — Explicit mention (NEW)      20%
  Regex on PR title + PR description + commit messages
  "Fixes JIRA-142" → 0.95
  "Related to JIRA-142" → 0.80
  Captured from GitHub/GitLab push webhook commit messages + PR webhook

MODIFIERS (additive, applied after base score):
  + Sprint cohesion     → adjusts Signal 2 weight (above)
  + Ticket criticality  → +0.05 if ticket.priority = P0/P1/Critical
  + Dominant ticket     → +0.08 if ticket accounts for >50% sprint story points
```

---

## Confidence thresholds

```
≥ 0.80  → auto-attribute, GREEN  (show clean, no indicator)
0.50–0.79 → attributed with WATCH flag, YELLOW
< 0.50  → UNATTRIBUTED → goes to Unknown Queue
```

Thresholds are adjustable per org. A wrong attribution is worse than an honest "unknown."

---

## Unknown Queue — manager UI

```
UNATTRIBUTED SESSIONS view (lead/EM/admin only):
  Developer | Tool | Duration | Cost | Branch | Suggested ticket | Action
  ─────────────────────────────────────────────────────────────────────────
  Adnan     | CC   | 74 min   | $0.42| patch-2 | —               | [Assign ▼][Ignore][Mark exploratory]
  Sara      | Cursor | 45min  | $1.20| wip-auth | JIRA-155 (0.48)| [Assign ▼][Confirm][Ignore]

Assign → manager types ticket ID → method="manual", confidence=1.0
Confirm → accepts the suggested ticket → method="manual_confirm"
Ignore → session marked as overhead/exploratory, excluded from ticket KPIs
```

Manual corrections stored in DB (for V2 per-org learning loop — data collected from V1).
Developers can tag ONLY their own unattributed sessions — same options minus team view.

---

## Branch switch handling

**Primary source: git reflog (agent reads locally, all tools)**

```bash
git reflog --format="%H %ci %gs"
# Output includes: checkout: moving from feature/JIRA-142 to hotfix/JIRA-198
# Timestamps give exact minutes spent on each branch
```

Token cost split = proportional to time-on-branch from reflog timestamps.
Works universally — no tool-specific parsing.
Claude Code per-turn gitBranch used as a secondary verification only.

---

## Edge cases — locked decisions

```
EC1 — No branch naming
  → Unknown queue + one-time in-IDE nudge to developer
  → Manager sees it in unknown queue and can assign

EC2 — Multi-ticket branch
  → Primary attribution: branch name ticket (Signal 1)
  → Flag secondary: if file overlap detects a second ticket
  → Show "primarily JIRA-142, possibly JIRA-139" — EM reviews

EC3 — Hot files / sprint focus
  → Per-file weight decay (1 / tickets_touching_that_file)
  → Sprint cohesion modifier adjusts Signal 2 weight
  → Dominant ticket boost (+0.08) if one ticket owns the sprint

EC4 — Kiro with/without spec
  → Attribution engine runs normally for ALL Kiro sessions
  → taskId = Signal 1 when present (confidence boost)
  → Free-vibe sessions (no taskId) = run all signals normally
  → No bypass — consistent treatment across all tools

EC5 — Branch switch mid-session
  → git reflog → time-on-branch split → proportional token allocation
  → Works for ALL tools via local git

EC6 — Delayed Source 3 data
  → Session stored immediately with partial attribution
  → reconciled=false, backfill job runs every 5 min
  → Epic/sprint/file-overlap updated when ticketing API responds
```

---

## Attribution engine flow

```
STEP 1 — Ingest (real-time, <50ms)
  Session arrives from agent
  Signal 1: branch parse → ticket_id
  Signal 3: temporal check against tickets table
  Signal 4: developer = assignee check
  Signal 5: scan commit messages + PR title if PR exists
  Signal 2: SKIP if no PR yet (marked pending)
  Score computed → stored, reconciled=false

STEP 2 — Backfill (background, every 5 min)
  For reconciled=false sessions:
    Pull epic_id, sprint_id from Jira/Linear
    Apply sprint cohesion + dominant ticket modifiers
    Run Signal 2 if PR now exists
    Recompute score
    Set reconciled=true

STEP 3 — PR webhook trigger (real-time)
  When pull_request:opened or pull_request:merged fires:
    Find all sessions with matching branch + developer
    Run Signal 2 now (file overlap available)
    Update confidence scores retroactively
    Re-check thresholds → may move from WATCH to auto-attributed

STEP 4 — Manual correction
  Manager assigns session in unknown queue
  method="manual", confidence=1.0
  Correction stored for V2 learning loop
```

---

## What's deferred to V2

```
Per-org learning loop:
  Collect all manual corrections from V1
  V2 uses them to adjust signal weights per org
  → "For org X, branch naming is 95% reliable → boost Signal 1 weight"
  → "For org Y, file overlap is unreliable → dampen Signal 2"
```

---

# Q8 + Q11 — MULTI-TENANT ISOLATION + ONBOARDING FLOW ✅ SEALED

---

## Q8 — Multi-tenant isolation

**Strategy: PostgreSQL Row Level Security (RLS) — row-level isolation, single database**

```sql
-- Every table has org_id. RLS enforces it at DB level.
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_isolation ON sessions
  USING (org_id = current_setting('app.current_org_id')::uuid);

-- Application sets org context at start of every request:
SET LOCAL app.current_org_id = 'org_rapyder_456';
-- From this point, ALL queries automatically scoped to that org.
-- No WHERE org_id = X needed. DB enforces it.
```

**Four isolation boundaries:**
```
1. DB layer     → PostgreSQL RLS on every table
2. API layer    → org_id from JWT, never trusted from request body
3. Redis layer  → keys: "org:{org_id}:kpi:{type}"
4. Storage layer → S3 paths: "orgs/{org_id}/..."
```

**Auth token chain:**
```
org_token (agent) → backend hashes + resolves org_id → RLS set → isolated
JWT (browser)     → org_id extracted from token → RLS set → isolated
```

---

## Q11 — Onboarding flow (final spec)

### Two tracks
```
TRACK A — Self-serve (< 50 devs, tech lead signs up directly)
  Goal: first attributed session within 24 hours
  No IT, no sales call

TRACK B — Enterprise (> 50 devs, IT-managed machines)
  Goal: IT deploys via MDM (Jamf/Intune) in one push
  White-glove setup, SSO/SCIM (V2)
```

---

### Signup: company email + domain verification

```
1. Enter work email → adnan@rapyder.com
2. Verification email sent → click to verify
3. Org created, domain locked to "rapyder.com"
4. Domain lock: only @rapyder.com can join this org
5. GitHub OAuth / Google OAuth supported as shortcuts
   → Only if OAuth email matches org domain
   → @gmail.com blocked even via OAuth

ENTERPRISE (V2): SAML/SSO via Okta, Azure AD, Google Workspace
```

---

### STEP 1 — Signup (2 min)
Company email verification → org created → org admin role assigned → 14-day trial, no card.

Post-signup: dashboard shell visible immediately (empty state with CTAs).
Setup banner persists at top until all steps complete.

---

### STEP 2 — Connect Source 3 (5 min)
```
Connect GitHub App → select repos (or all repos)
  Scopes: contents:read, pull_requests:read, metadata:read
  Webhooks registered: push, pull_request, create, delete

Connect ticketing (pick one, add more later):
  Jira → OAuth → auto-discover boards + sprint custom field IDs
  Linear → OAuth → teams + cycles synced
  GitHub Issues → zero extra auth (same GitHub App)
  Azure DevOps → PAT → repos + boards in one auth

Background backfill (90 days):
  WHAT IT GIVES: tickets, sprints, PRs, commit history, branch names
  WHAT IT DOESN'T GIVE: AI session costs (no agent = no cost data)
  PURPOSE 1: attribution readiness — tickets pre-loaded before first session
  PURPOSE 2: baseline metrics — PR cycle time, commits/dev/day (before-AI benchmark)

UI MESSAGE (set expectation correctly):
  "Importing last 90 days of tickets and PRs...
   This sets your baseline. AI cost data appears after
   agents are installed on developer machines."

  Complete:
  "✅ Baseline set: 847 tickets, 12 sprints, 34 PRs imported.
   Install agents to start tracking AI costs →"
```

---

### STEP 3 — Configure AI tools (admin, org/team level)

```
ORG LEVEL (admin sets default for all developers):
  ☑ Claude Code  ☑ Cursor  ☐ Kiro  ☐ Copilot  ☐ Windsurf

TEAM LEVEL (admin overrides per team):
  "Platform team: ☑ Cursor ☑ Copilot"
  "AI team: ☑ Claude Code ☑ Kiro"
  Different teams, different tool stacks — all supported

DEVELOPER LEVEL:
  Can ADD personal tools not in team stack
  Cannot REMOVE what org/team has set

SOURCE 2 SETUP (triggered by tool selection):
  Kiro selected     → admin pastes S3 bucket name + IAM role ARN
  Copilot selected  → GitHub OAuth (copilot_metrics scope, org-level)
  Claude Code       → nothing extra (local JSONL, no API needed)
                      Optional: Anthropic Admin API key (if API key mode users)
  Cursor            → nothing extra (local SQLite)
                      Optional: Cursor admin API key (reconciliation)
```

---

### STEP 4 — Add team members (Manage Team section)

```
Admin invites via:
  → Paste GitHub usernames or emails (bulk)
  → System auto-matches GitHub identities
  → Assign roles: Team Lead | Developer
  → Optional: set hourly rates per developer (for KPI 3)

Developer receives notification (see Step 4a — Notifications)
  with personalised one-liner install command

UI section: "Manage Team" (persistent, not just onboarding)
  Shows: all members, roles, agent status (installed/pending), tools declared
```

---

### STEP 4a — Notifications setup

```
CHANNELS:
  Slack          → V1, OAuth (channels:write + im:write)
  Microsoft Teams → V1, Incoming Webhook URL (simpler) + Teams Bot (V2)
  Google Chat    → V1.5, Google Chat API webhook
  Email          → V1, always on, no setup needed

USE CASES (same across all channels):
  1. Agent install DM → developer receives personalised install command
  2. Hallucination alert → team lead DM when KPI 5 triggers
  3. Weekly digest → optional channel post (sprint AI spend summary)
  4. Unknown queue reminder → weekly lead DM (N sessions need review)

SETUP:
  Admin connects one or more channels during onboarding
  Can connect multiple (Slack + email, Teams + email)
  Email always on as fallback regardless
```

---

### STEP 5 — Agent install (developer side, 2 min per machine)

```
SELF-SERVE (agent install page shows personalised command):
  Windows PowerShell:
  iwr https://get.vibeROI.io/install.ps1 | iex -OrgToken ORG_TOKEN

  Mac/Linux:
  curl -fsSL https://get.vibeROI.io/install.sh | sh -s ORG_TOKEN

  OrgToken is pre-filled for each developer
  Agent installs as OS native service
  First registration: { org_token, machine_id, username, OS, declared_tools }
  Backend creates developer profile, links to org

ENTERPRISE MDM (Track B):
  Admin downloads .pkg / .msi / .deb with org_token baked in
  Silent deploy via Jamf / Intune to all managed machines
  Zero developer action needed

PENDING INSTALLS:
  Admin sees "5 of 8 agents installed" in Manage Team
  Can resend install notification per developer
  Shows: last session, agent version, OS, tools detected
```

---

### STEP 6 — First attributed session (automatic)

```
Dashboard live status:
  "Waiting for first session..."
  → Developer works in declared tool
  → Agent captures session, pushes to backend
  → Attribution engine runs (< 50ms)
  → Dashboard: "First session attributed to JIRA-142 ✓"
  → Onboarding complete

SETUP CHECKLIST (persists until all done):
  ✅ Company email verified
  ✅ GitHub connected (4 repos)
  ✅ Jira connected (847 tickets, 12 sprints)
  ✅ AI tools configured (Claude Code, Cursor)
  ✅ Team added (8 members)
  ✅ 5/8 agents installed
  ⬜ First session attributed ← last step
```

---

### RBAC (locked in Q5, restated here for completeness)

```
Org Admin    → everything: all developers, all KPIs, billing,
               unknown queue (all teams), Manage Team
Team Lead/EM → their team only: all KPIs, unknown queue (their team),
               manage team members (their team)
Developer    → own sessions ONLY (read): own attribution,
               can tag own unattributed sessions
               cannot see: teammates' data, costs, rankings
```

---

### The backfill honest contract (product principle)

```
Backfill gives: attribution readiness + before-AI baseline
Backfill cannot give: historical AI session costs

"Before-AI baseline" metrics (shown from backfill data):
  → Average PR cycle time (last 90 days)
  → Average commits per developer per day
  → Sprint completion rate
  → These become the denominator for AI impact metrics

First AI session cost data: the moment agent installs and captures
No retroactive AI cost is possible — agent must be present to capture
This is communicated clearly in onboarding and in the UI
```

---

# Q9 — CLOUD DEPLOYMENT ARCHITECTURE ✅ SEALED

**Cloud:** AWS primary (us-east-1), GCP optional analytics layer
**Philosophy:** Managed services reduce ops burden. Start small, scale with revenue. No over-provisioning.

---

## Architecture overview

```
┌─────────────────────────────────────────────────────────────┐
│  DEVELOPER MACHINES (agent)                                 │
│  Go daemon → reads local IDE files + git reflog             │
│  → HTTPS POST to API Gateway (signed with org_token)        │
└─────────────────────┬───────────────────────────────────────┘
                       │ agent pushes sessions
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS us-east-1                                              │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ CloudFront  │  │ API Gateway  │  │ ALB              │   │
│  │ (CDN)       │  │ (webhooks)   │  │ (app traffic)    │   │
│  │ React SPA   │  │ GitHub/Jira  │  │                  │   │
│  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                │                    │             │
│         └────────────────┼────────────────────┘             │
│                          ▼                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ECS Fargate (app layer — serverless containers)      │  │
│  │                                                       │  │
│  │  API Service          Worker Service                  │  │
│  │  ─────────────        ─────────────────               │  │
│  │  Session ingest       Attribution engine              │  │
│  │  Auth / JWT           Backfill jobs                   │  │
│  │  Dashboard API        KPI snapshot refresh            │  │
│  │  Webhook receiver     Cost reconciliation             │  │
│  │  Unknown queue API    Unknown queue LLM assistant     │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                   │
│          ┌───────────────┼───────────────────┐              │
│          ▼               ▼                   ▼              │
│  ┌──────────────┐ ┌────────────┐ ┌────────────────────┐    │
│  │ RDS Postgres │ │ ElastiCache│ │ SQS (queues)       │    │
│  │ (Multi-AZ)   │ │ Redis      │ │ session_ingest     │    │
│  │ Primary DB   │ │ Live KPIs  │ │ webhook_events     │    │
│  │ + RLS        │ │ counters   │ │ attribution_jobs   │    │
│  └──────────────┘ └────────────┘ └────────────────────┘    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  S3 Buckets                                          │  │
│  │  vibeROI-org-data/     → per-org exports, reports   │  │
│  │  vibeROI-kiro-sync/    → Kiro S3 CSV landing zone   │  │
│  │  vibeROI-backups/      → daily DB snapshots         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Component decisions — why each choice

**ECS Fargate (not EC2, not Lambda):**
```
Lambda: cold starts hurt real-time session ingest (<50ms requirement)
EC2: we manage instances, patching, scaling — unnecessary ops burden
Fargate: serverless containers, pay per second of use, no server management
         auto-scales on load, right for a startup with variable traffic
```

**RDS PostgreSQL Multi-AZ (not Aurora, not self-managed):**
```
Self-managed: too much ops for a small team
Aurora Serverless: good but 2× cost for V1 traffic levels
RDS Multi-AZ: automatic failover, daily backups, managed patches
              right-sized: start db.t3.medium ($60/mo), scale when needed
              RLS works identically to self-managed PostgreSQL
```

**ElastiCache Redis (not Redis Cloud, not self-managed):**
```
Managed Redis for live KPI counters and session caching
cache.t3.micro for V1 ($15/mo)
Cluster mode off until needed — keep it simple
```

**SQS queues (not Kafka, not RabbitMQ):**
```
Three queues:
  1. session_ingest     → agent pushes here, workers consume
  2. webhook_events     → GitHub/Jira webhooks land here
  3. attribution_jobs   → sessions needing attribution/backfill

Why SQS not Kafka:
  Kafka = operational complexity, overkill for V1 throughput
  SQS = managed, scales to millions of messages, $0.40 per million
  Switch to Kafka/Kinesis only if real-time analytics demand it
```

**CloudFront + S3 (not EC2 for frontend):**
```
React SPA built and deployed to S3
CloudFront serves it globally with caching
$0 for static assets beyond S3 storage
~$0.01 per GB transfer — essentially free for a dashboard app
```

**API Gateway (for webhooks only):**
```
GitHub/Jira/Linear webhooks hit API Gateway → SQS
Lambda processes the queue → no always-on container needed for webhook processing
Handles burst traffic (100 PRs merged simultaneously) without scaling pressure
```

---

## MVP infrastructure cost estimate (V1, ~10 orgs, ~100 developers)

```
COMPONENT              SIZE          MONTHLY COST
────────────────────────────────────────────────────────
RDS PostgreSQL         db.t3.medium  $65
ElastiCache Redis      cache.t3.micro $15
ECS Fargate (API)      0.5 vCPU      ~$25 (pay per use)
ECS Fargate (Worker)   0.25 vCPU     ~$15 (pay per use)
SQS                    <1M msgs/mo   ~$1
S3                     10 GB         ~$1
CloudFront             low traffic   ~$2
API Gateway            <1M calls/mo  ~$1
Route 53               1 hosted zone $1
ACM (SSL)              free          $0
CloudWatch logs        basic         ~$5
────────────────────────────────────────────────────────
TOTAL MVP               ~$131/month

At 10 paying orgs on $49/mo plan = $490 revenue
Infrastructure = 27% of revenue at V1 scale ← acceptable
```

**At 100 orgs (~1,000 developers):**
```
Scale-up needed:
  RDS → db.t3.large ($130)
  Redis → cache.t3.small ($30)
  Fargate → auto-scaled (~$200 total)
  ClickHouse (optional, self-hosted on EC2) → $100
────────────────────────────────────────────────────────
TOTAL at scale          ~$500/month
At 100 orgs × $99/mo   = $9,900 revenue
Infrastructure = 5% of revenue ← very healthy
```

---

## Cost-saving principles (locked)

```
1. FARGATE over EC2
   No idle capacity. Pay only for what runs.
   Workers scale to zero overnight if no jobs queued.

2. RESERVED INSTANCES for RDS
   1-year reserved RDS saves ~40% vs on-demand
   Once V1 is stable (month 3+), commit to reserved.

3. SQS DECOUPLING
   Session ingest never directly hits the DB.
   SQS absorbs bursts, workers process at DB's pace.
   Prevents DB overload from simultaneous agent pushes.

4. CLOUDFRONT CACHING
   Dashboard API responses cached at edge for 60 seconds.
   Reduces Fargate + DB load by ~70% for read-heavy KPI queries.

5. PRE-COMPUTED KPI SNAPSHOTS
   Dashboard reads kpi_snapshots table, not raw sessions.
   Prevents expensive aggregation queries on every page load.
   Hourly refresh job updates snapshots (one DB write per hour
   vs thousands of ad-hoc aggregation queries).

6. S3 LIFECYCLE POLICIES
   Raw session backups: move to S3 Glacier after 90 days
   Cost drops from $0.023/GB to $0.004/GB for cold data.
```

---

## GCP optional layer (analytics)

```
If BigQuery analytics is desired (V2 decision):
  Sessions table replicated to BigQuery via Datastream (CDC)
  BigQuery handles complex analytical queries (slower but cheaper
  than running OLAP on PostgreSQL at scale)
  Cost: ~$5/TB queried (pay per query)
  Only activate if ClickHouse proves insufficient or too ops-heavy
```

---

## Security baseline (non-negotiable from day 1)

```
1. VPC with private subnets
   RDS + Redis never publicly accessible
   Fargate tasks in private subnets, NAT Gateway for outbound

2. IAM roles (not access keys)
   All AWS services communicate via IAM roles
   No hardcoded credentials anywhere

3. Secrets Manager
   DB passwords, Redis auth, API keys — all in Secrets Manager
   Rotated automatically (RDS supports rotation natively)

4. org_token stored HASHED (bcrypt)
   Never stored in plaintext — treated like a password
   Compared on each agent request, never returned in API responses

5. TLS everywhere
   ACM certificate on all ALB/API Gateway endpoints
   Agent-to-backend: TLS 1.3 minimum
   Internal VPC traffic: encrypted in transit

6. CloudWatch + CloudTrail
   All API calls logged
   Alerts on: failed auth spike, unusual data volume, cost anomaly
```

---

# Q12 — AGENT ARCHITECTURE ✅ SEALED

**Language:** Go (single native binary, no runtime, cross-platform, ~15MB RAM)
**Pattern:** Hybrid file watcher (awareness) + polling (session-end detection)

## Session detection

```
FILE WATCHER (fsnotify — OS-native events):
  Windows → ReadDirectoryChangesW
  Mac     → FSEvents
  Linux   → inotify
  Watches specific paths per declared tool only
  File change → marks "session active for tool X"
  Does NOT process on every write — just awareness

POLLING (every 60 seconds):
  Claude Code: INDEX lastActivityAt stopped updating
  Cursor:      no new bubbles in state.vscdb for 10+ min
  Kiro:        task executionStatus changed to succeed/failed
  Copilot:     chatSessions lastMessageDate stopped updating
  Inactivity > 10 min → session ended → parse + push
  Threshold configurable per org
```

## What it does at session end

```
1. Reads local IDE files (tool-specific parser, declared tools only)
2. Runs: git -C {repo} reflog --format="%ci %gs" -n 50
         → branch switches + time-on-branch split
3. Runs: git diff --numstat → lines added/deleted (numbers only, no content)
4. Builds session object (locked schema from Q7)
5. gzips payload (~70% size reduction)
6. HMAC-SHA256 signs payload with org_token
7. POST /ingest/session
8. Returns 202 → agent moves on (does not wait for processing)
```

## Offline handling

```
Local queue: ~/.vibeROI/queue.jsonl (append-only)
Failed push → appended to queue
On network recovery / next startup → retries all queued sessions
Max queue: 1000 sessions (~30 days average developer)
Beyond max: oldest dropped, logged (not silently lost)
```

## Auto-update

```
On startup:
  GET https://agent.vibeROI.io/version → { latest, url, sha256 }
  If newer: download → verify SHA256 → verify OS signature → replace → restart
  Rollback: keeps previous binary, auto-reverts if new version crashes
  Signed binaries: Apple notarization (Mac) + Authenticode (Windows)
```

## OS service

```
Windows → Windows Service
Mac     → launchd (~/Library/LaunchAgents/io.vibeROI.agent.plist)
Linux   → systemd (/etc/systemd/system/viberoi-agent.service)
All three: starts on login, restarts on crash, 50MB memory limit
```

---

# Q13 — BACKEND API DESIGN ✅ SEALED

**Style:** REST (not GraphQL — two simple clients, no flexible query need)
**Base:** https://api.vibeROI.io/v1/
**Versioning:** URL-based (/v1/, /v2/). v1 maintained 6 months after v2 ships.

## Endpoint groups

```
AGENT (org_token auth):
  POST /ingest/session          → push session (202 Accepted, async processing)
  POST /ingest/sessions         → batch push up to 100 sessions
  GET  /agent/config            → org config (tools, settings)
  GET  /agent/version           → update check

WEBHOOKS (HMAC signature auth):
  POST /webhooks/github
  POST /webhooks/gitlab
  POST /webhooks/jira
  POST /webhooks/linear
  → Always 200 immediately, never make sender wait

DASHBOARD (JWT auth):
  Auth: POST /auth/signup | /auth/verify | /auth/login | /auth/logout | /auth/refresh
  KPIs: GET /kpis/summary | /kpis/ai-insights | /kpis/roi | /kpis/capacity
        GET /kpis/developer/{id}
  Sessions: GET /sessions | /sessions/{id}
  Queue: GET /queue/unknown
         PATCH /queue/{sessionId}  → assign ticket (manual attribution)
         DELETE /queue/{sessionId} → ignore/exploratory
  Org: GET/PATCH /org/settings | /org/team | /org/integrations | /org/usage

QUERY PARAMS (consistent):
  ?from=2026-05-01&to=2026-05-31
  ?team_id=uuid | ?developer_id=uuid | ?tool=cursor | ?sprint_id=SPRINT-42
  ?page=1&limit=50
```

## Middleware stack (in order)

```
1. Rate limiter        (per IP unauthenticated, per org authenticated)
2. Request ID          (for distributed tracing)
3. Auth validator      (HMAC for agent, JWT for dashboard, HMAC for webhooks)
4. Org context setter  (SET LOCAL app.current_org_id = org_id)
5. RBAC checker        (role-based permission for endpoint)
6. Handler
```

---

# Q14 — DATA PIPELINE ✅ SEALED

## Full session flow (agent → dashboard)

```
CAPTURE (agent):
  ① Session end detected (inactivity threshold)
  ② Reads local files → builds session object
  ③ git reflog → branch splits | git diff --numstat → LOC
  ④ gzip + HMAC sign → POST /ingest/session
  ⑤ API validates → pushes to SQS session_ingest → 202 to agent

ATTRIBUTION (worker, <50ms):
  ⑥ Worker picks from SQS
  ⑦ Signals 1,3,4,5 run (Signal 2 skipped if no PR yet)
  ⑧ Confidence score + modifiers computed
  ⑨ Session stored in PostgreSQL (RLS active, org_id set)
  ⑩ Redis KPI counters incremented (live dashboard update)
  ⑪ reconciled=false if cost/attribution incomplete

BACKFILL (every 5 min):
  ⑫ SELECT sessions WHERE reconciled=false
  ⑬ Query Jira/Linear → epic_id, sprint_id
  ⑭ Recompute confidence with full context
  ⑮ reconciled=true when cost + attribution both confirmed

PR WEBHOOK (real-time trigger):
  ⑯ GitHub push pull_request:opened → SQS webhook_events
  ⑰ Worker finds sessions with matching branch + developer
  ⑱ Signal 2 runs (file overlap now available)
  ⑲ Confidence scores updated retroactively

KPI SNAPSHOTS (hourly cron):
  ⑳ Aggregate sessions → write kpi_snapshots table
  One row per KPI per dimension per org per period

DASHBOARD READ:
  ㉑ GET /kpis/summary
  ㉒ Read kpi_snapshots (historical, pre-computed, fast)
  ㉓ Read Redis (today's live counters)
  ㉔ Combined response <100ms
```

## Error handling

```
RETRIES:
  SQS visibility timeout: 30s
  Max retries per message: 3
  After 3 failures → Dead Letter Queue (DLQ)
  CloudWatch alarm fires on DLQ → admin alerted
  DLQ sessions visible in admin panel, manual retry available

IDEMPOTENCY:
  UNIQUE constraint on (org_id, session_id)
  Agent retry on network failure → duplicate push → ignored by DB
  Safe to retry without double-counting

CIRCUIT BREAKER (Jira/Linear):
  3× consecutive 429/5xx → backoff 15 min
  Queue sessions for retry, log clearly, don't fail silently
```

---

# Q15 — DASHBOARD FRONTEND ARCHITECTURE ✅ SEALED

**Framework:** React + TypeScript (SPA, not SSR — behind-auth dashboard)
**Served:** S3 + CloudFront (static, no server needed)
**Component library:** Tremor (purpose-built for analytics dashboards)
**Data fetching:** TanStack Query (React Query)
**Real-time:** Server-Sent Events (SSE) → Redis pub/sub → live counter updates
**Charts:** Recharts via Tremor

## Real-time updates

```
Dashboard connects: GET /live/kpis (SSE endpoint, persistent HTTP)
Agent pushes session → Redis pub/sub fires → backend pushes SSE event
React Query cache invalidated → refetch
"Today's spend" updates without page reload

Fallback: polling every 30s if SSE drops
Reconnection: every 5s automatically (browser SSE native behaviour)
```

## Page structure

```
/login | /signup | /onboarding/*        → public
/dashboard                              → Team Dashboard (overview)
/insights                               → AI Insights (KPIs 1–7)
/roi                                    → ROI view (KPIs 8–13)
/people | /people/{id}                  → Developer profiles (KPIs 14–20)
/capacity                               → Capacity Overview (KPIs 21–22)
/queue                                  → Unknown attribution queue
/settings/team | /integrations | /billing
```

## State management

```
Server state:  React Query (KPI data, sessions, tickets — cached, revalidated)
UI state:      useState / useContext (filters, date range, modals)
Auth state:    React Context + httpOnly cookie for JWT (not localStorage)
No Redux:      unnecessary for this complexity level
```

## Chart types per screen

```
KPI cards + sparklines:   all screens (Tremor AreaChart mini)
Bar charts:               sprint spend comparison, tool breakdown
Line charts:              trend over time, efficiency trajectory
Donut charts:             tool mix (Cursor 52%, Claude Code 22%)
Heatmap:                  daily AI ROI (loss → breakeven → gain)
Stacked bar:              lifecycle decomposition (prompt→commit→PR→merge)
Horizontal bar:           top users by spend / sessions
```

## Performance

```
Code splitting by route (React.lazy + Suspense)
KPI cards load first (above fold), charts load below
Skeleton loaders (no layout shift during fetch)
Static assets: content-hashed filenames → CloudFront caches forever
API responses: React Query caches for 5 min (staleTime)
               Refetches in background when stale (stale-while-revalidate)
```

---

# FINAL ARCHITECTURE — COMPLETE ✅ SEALED

## Agreed decisions summary

```
Cloud:          AWS primary (ECS Fargate), GCP optional analytics layer
                Apply Google for Startups ($200K + $150K AI bonus)
                Apply Microsoft Founders Hub (same week, easiest)
                Apply AWS Activate via PostHog partner ($25K-100K)
                Total potential: $350K+ across 3 clouds

Containers:     ECS Fargate V1 → EKS when DevOps capacity exists
                GKE Autopilot viable if Google credits approved
                (free control plane, pay per pod only)

Ingestion:      Agent → ALB → Ingest Service → S3 raw landing
                S3 Event → SQS session_ingest → Worker Service
                Raw data preserved in S3 (replayable if bugs found)
                S3 encrypted at rest (SSE), HTTPS in transit

Processing:     Agent = structured extractor (never raw files, never code)
                Server = intelligence (attribution, KPIs, aggregation)
                Git commands run on agent (LOC, branch switches)

Messaging:      SQS (not Kafka/MSK/RabbitMQ — right scale for V1)
                Switch to Kinesis/MSK at 100K+ developers

Agent frequency: Event-driven only — pushes when session ends
                 NOT continuous — 5-15 pushes per day per developer
                 Offline queue: ~/.vibeROI/queue.jsonl (retries on recovery)

Onboarding:     NOT a separate service
                API Service owns /onboarding/* endpoints
                Orchestrates Auth + Integration + Notification
                Backfill runs async via Worker Service (SQS job)
                Progress tracked in onboarding_progress table
```

---

## Final service map (6 ECS + 1 Lambda + EventBridge)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DEVELOPER MACHINES                                                 │
│  Go agent (fsnotify + 60s polling)                                 │
│  Reads: IDE files + git reflog + git diff --numstat                │
│  Sends: session object (gzip + HMAC signed) on session end         │
│  Never sends: code, prompts, diffs                                  │
│  Offline queue: ~/.vibeROI/queue.jsonl                             │
└────────────────────────┬────────────────────────────────────────────┘
                         │ HTTPS TLS 1.3
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AWS us-east-1                                                      │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  ALB (Application Load Balancer)                             │  │
│  │  → /ingest/*      → Ingest Service                          │  │
│  │  → /api/*         → API Service                             │  │
│  │  → /auth/*        → Auth Service                            │  │
│  │  → /webhooks/*    → API Gateway → Webhook Lambda            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │ SERVICE 1       │  │ SERVICE 2       │  │ SERVICE 3        │   │
│  │ Ingest Service  │  │ API Service     │  │ Auth Service     │   │
│  │─────────────────│  │─────────────────│  │──────────────────│   │
│  │ Validate token  │  │ Dashboard HTTP  │  │ Signup/login     │   │
│  │ Verify HMAC     │  │ KPI endpoints   │  │ JWT issue/verify │   │
│  │ Write to S3     │  │ Onboarding orch │  │ OAuth flows      │   │
│  │ Register agent  │  │ Settings/team   │  │ Domain verify    │   │
│  │ Create dev      │  │ Unknown queue   │  │ Invitations      │   │
│  │ profile         │  │ SSE /live/kpis  │  │ RBAC management  │   │
│  └────────┬────────┘  └────────┬────────┘  └──────────────────┘   │
│           │                    │                                    │
│           ▼                    │                                    │
│  ┌─────────────────┐           │                                    │
│  │ S3 Raw Landing  │           │                                    │
│  │ orgs/{org_id}/  │           │                                    │
│  │ sessions/       │           │                                    │
│  │ {date}/         │           │                                    │
│  │ {session}.json.gz│          │                                    │
│  │ SSE encrypted   │           │                                    │
│  │ 90d → Glacier   │           │                                    │
│  └────────┬────────┘           │                                    │
│           │ S3 Event           │                                    │
│           ▼                    │                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  SQS QUEUES                                                  │  │
│  │  session_ingest   ← S3 events (new session files)           │  │
│  │  webhook_events   ← Webhook Lambda (GitHub/Jira/Linear)     │  │
│  │  backfill_jobs    ← Integration Service (sync triggers)     │  │
│  │  notification_jobs← Worker + Cron (alert/digest triggers)  │  │
│  │  All queues: DLQ configured, 3 retries, CloudWatch alarm    │  │
│  └──────────────────────┬───────────────────────────────────────┘  │
│                         ▼                                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │ SERVICE 4       │  │ SERVICE 5       │  │ SERVICE 6        │   │
│  │ Worker Service  │  │ Integration     │  │ Notification     │   │
│  │─────────────────│  │ Service         │  │ Service          │   │
│  │ Reads S3 session│  │─────────────────│  │──────────────────│   │
│  │ Attribution     │  │ Jira/Linear API │  │ Slack SDK        │   │
│  │ engine (5 sigs) │  │ GitHub API      │  │ Teams webhook    │   │
│  │ Cost compute    │  │ Kiro S3 CSV     │  │ Google Chat API  │   │
│  │ KPI writes      │  │ Copilot API     │  │ Email (SES)      │   │
│  │ Redis increment │  │ OAuth refresh   │  │ Alert routing    │   │
│  │ Backfill jobs   │  │ Webhook register│  │ Digest generation│   │
│  │ Reprocess from  │  │ Rate limiting   │  │ Install invite   │   │
│  │ DLQ on retry    │  │ Circuit breaker │  │ DMs to devs      │   │
│  │                 │  │ Token storage   │  │                  │   │
│  │ SCALES:         │  │ Secrets Manager │  │                  │   │
│  │ Min 1 / Max 20  │  │                 │  │                  │   │
│  │ SQS depth trigger│  │                │  │                  │   │
│  └────────┬────────┘  └─────────────────┘  └──────────────────┘   │
│           │                                                         │
│           ▼                                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  DATA LAYER                                                  │  │
│  │                                                              │  │
│  │  RDS PostgreSQL (Multi-AZ)     ElastiCache Redis            │  │
│  │  ─────────────────────────     ─────────────────            │  │
│  │  sessions (primary table)      Live KPI counters            │  │
│  │  kpi_snapshots                 Session caching              │  │
│  │  tickets, sprints              Redis pub/sub                │  │
│  │  developers, orgs              (SSE live updates)           │  │
│  │  onboarding_progress           Namespaced per org           │  │
│  │  RLS on every table            "org:{id}:kpi:{type}"        │  │
│  │  org_id on every row                                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  EVENT-DRIVEN:                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  API Gateway → Webhook Lambda                                │  │
│  │  Validates HMAC per provider → pushes to SQS webhook_events │  │
│  │  GitHub / GitLab / Jira / Linear / Bitbucket / Azure DevOps │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  SCHEDULED (EventBridge):                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Cron Jobs                                                   │  │
│  │  Every hour:   KPI snapshot refresh                         │  │
│  │  02:30 UTC:    Kiro S3 CSV ingestion                        │  │
│  │  04:00 UTC:    Copilot GitHub usage API pull                │  │
│  │  04:30 UTC:    Jira/Linear full sync (safety net)           │  │
│  │  06:00 UTC:    Anthropic Admin API pull (API key orgs)      │  │
│  │  Monday 08:00: Weekly digest trigger → Notification Service │  │
│  │  1st of month: Monthly digest trigger                       │  │
│  │  Daily:        Offline queue cleanup, session expiry        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  FRONTEND:                                                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  React SPA (TypeScript) → S3 → CloudFront                   │  │
│  │  Tremor components, Recharts, TanStack Query                │  │
│  │  SSE for live KPI updates (Redis pub/sub → API Service)     │  │
│  │  Content-hashed assets, CloudFront cache forever            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Service responsibilities — final (no ambiguity)

| Service | Owns | Does NOT own |
|---|---|---|
| Ingest | Agent validation, S3 write, developer profile creation | Processing, attribution |
| API | Dashboard reads, onboarding orchestration, settings, SSE | Auth, external APIs |
| Auth | Users, JWT, OAuth, invitations, RBAC, domain lock | Sessions, KPIs |
| Worker | Attribution engine, session processing, KPI writes, Redis | External API calls |
| Integration | All external API calls (Jira/Linear/GitHub/Kiro/Copilot), OAuth tokens | Processing, alerts |
| Notification | All message delivery (Slack/Teams/Email/Chat) | Content generation (Worker generates, Notification delivers) |
| Webhook Lambda | HMAC validation per provider, SQS push | Processing |
| Cron Jobs | Scheduled triggers only | Processing (triggers Worker via SQS) |

---

## Onboarding workflow — cross-service (no dedicated service)

```
Step 1 Signup         → Auth Service (/auth/signup, /auth/verify)
Step 2 Connect tools  → Integration Service (OAuth, webhook register)
                        Worker Service (backfill job via SQS)
Step 3 Configure tools→ API Service (/onboarding/tools, saves to DB)
Step 4 Invite team    → Auth Service (creates invitations)
                        Notification Service (sends install links)
Step 5 Agent install  → Ingest Service (first registration)
Step 6 First session  → Worker Service (standard session processing)

Progress state:        onboarding_progress table in PostgreSQL
                       API Service reads/writes it
                       Frontend polls /onboarding/status
Backfill:             Async via SQS backfill_jobs queue
                       Frontend shows live progress bar
                       Does NOT block other onboarding steps
```

---

## Agent frequency — clarified

```
AGENT SENDS DATA:      Only when session ends (inactivity > 10 min)
AGENT IS SILENT:       During meetings, reading, sleep, machine off
TYPICAL VOLUME:        5-15 pushes per day per developer
PAYLOAD SIZE:          ~2-5KB gzipped per session
VOLUME AT 100 devs:    ~1,000 pushes/day = 0.7 per minute
                       SQS handles this trivially
OFFLINE HANDLING:      ~/.vibeROI/queue.jsonl
                       Retries on network recovery or restart
STARTUP BEHAVIOR:      Version check once + config pull once
                       Then retry any queued sessions
```

---

## Cloud credits — apply immediately

```
PRIORITY 1 — Microsoft Founders Hub (today, easiest)
  URL: foundershub.startups.microsoft.com
  No VC required, no funding requirement
  $1,000-5,000 immediately, up to $150K total
  Approval: same day to 3 days

PRIORITY 2 — Google for Startups (this week)
  URL: cloud.google.com/startup/apply
  Standard: $200,000 credits over 2 years
  AI-first bonus: +$150,000 (this product qualifies)
  + $12,000 Enhanced Support + Google Workspace
  Requirements: < 5 years old, pre-Series A, first-time applicant
  Approval: 7-21 days
  GKE Autopilot: free control plane, pay per pod
  → If approved, run all ECS services on GKE instead

PRIORITY 3 — AWS Activate (via PostHog partner)
  URL: posthog.com/startups
  $25,000-100,000 AWS credits
  No VC required via PostHog partner path
  Approval: 1-2 weeks

TOTAL POTENTIAL: $350,000+ across all three
  At $131/month infrastructure cost = 2+ years free
```

---

## Security baseline (non-negotiable)

```
VPC:           All services in private subnets, NAT for outbound
               RDS + Redis never publicly accessible
IAM:           Roles only, no hardcoded credentials anywhere
Secrets:       AWS Secrets Manager for all credentials
               Automatic rotation for RDS passwords
TLS:           1.3 minimum everywhere, ACM certificates on ALB
org_token:     Stored hashed (bcrypt), compared not returned
S3:            SSE encryption, lifecycle policies (90d → Glacier)
CloudTrail:    All API calls logged
CloudWatch:    Alerts on auth failures, cost anomalies, DLQ depth
HMAC signing:  Agent signs every payload, backend verifies
               Prevents spoofed sessions from external actors
```

---

# Q10 — SUBSCRIPTION PRICING MODEL ✅ SEALED

## Pricing unit: per active device (not per seat, not per token)

```
ACTIVE DEVICE DEFINITION:
  Agent installed AND captured ≥5 sessions in the billing month
  <5 sessions = not billed that month (inactive)
  Inactive devices cost us almost nothing — fair not to charge

WHY PER DEVICE (not per manager seat, not per token):
  Per manager seat → 50 devs, 3 managers = $45/month, wrong
  Per token → 4 tools, 4 billing units, discrepancy risk
  Per session-hour → measurement complexity, billing disputes
  Per device → binary, auditable, fair, matches value delivered

MANAGER/VIEWER SEATS: FREE at all tiers (unlimited)
  Analytics is why they stay — never gate it
```

---

## Free trial

```
Duration:     14 days
Devices:      Up to 5 active devices
Card:         NOT required
Features:     Full product, no limits
Abuse prevention:
  → 1 org per company email domain (domain lock)
  → Device 6+ requires card and ends trial immediately
  → Company email required (Gmail/Yahoo/Hotmail blocked)
  → Machine ID fingerprint flags cross-org reuse
  → Max 3 trial orgs per IP range per 30 days

AT TRIAL END:
  Agent stops capturing (data retained 30 days)
  Admin email shows real captured data:
  "You captured 847 sessions, attributed to 23 tickets.
   That's $50/month to continue on Starter."
  Trial devices count toward paid plan (no free carryover)
  Pay for all 5 devices if converting — no free tier holdover
```

---

## Tiers

```
STARTER:    1-15 devices     $10/device/month
            Monthly billing
            All features, unlimited manager seats
            Slack + Email notifications
            No annual option (simplicity)

GROWTH:     16-50 devices    $8/device/month
            Monthly or annual (annual = 2 months free, ~17% off)
            All features + API access
            All notification channels (Teams, Google Chat, Slack, Email)

SCALE:      51-150 devices   $6/device/month
            Annual billing, invoiced quarterly
            All features + priority support + custom reports
            Dedicated Slack channel with team

ENTERPRISE: 150+ devices     $4-5/device (negotiated)
            Annual contract, custom terms
            Adds: SSO/SAML, SCIM, custom data retention,
                  SLA guarantee, dedicated support,
                  on-prem agent option
```

---

## Real team costs

```
Team              Devices   Plan        Monthly    Annual
──────────────────────────────────────────────────────────
Small startup     10 devs   Starter     $100       $1,200
Mid startup       25 devs   Growth      $200       $2,000
Scale-up          75 devs   Scale       $450       $4,500
Enterprise        200 devs  Enterprise  ~$900      custom
```

---

## Margin analysis

```
Devices   Revenue    Our cost   Margin
──────────────────────────────────────
10        $100       $27        73% ✅
25        $200       $50        75% ✅
75        $450       $100       78% ✅
200       $900       $200       78% ✅
```

All tiers within 70-80% gross margin target.
Margin improves with scale as fixed costs dilute across more orgs.

---

## Annual discount mechanics

```
Growth annual:   $8 × 10 months = $80/device/year (vs $96 monthly)
Scale annual:    $6 × 10 months = $60/device/year (vs $72 monthly)
Payment:         Quarterly invoicing (not full year upfront)
                 → Reduces customer commitment friction
                 → We get 3-month revenue predictability

Annual only on Growth and above:
  Starter = monthly only (too small to lock in, friction not worth it)
  Growth+ = annual option because finance teams want predictability
```

---

## Competitive positioning

```
                Jellyfish   LinearB    Copilot     Ours
Manager seats   $$$         $$$        $$$         FREE
Developer cost  implicit    N/A        $19/seat    $6-10/device
AI cost/ticket  ❌          ❌         ❌          ✅
Token tracking  ❌          ❌         ❌          ✅ (exact)
Entry price     $1,000+/mo  $1,000+/mo $190/10dev  $100/10dev

Pitch in one line:
"11% of what you already spend on AI tools,
 to prove whether those tools are actually working."
(At $100/month for 10 devs spending ~$900/month on AI tools)
```
