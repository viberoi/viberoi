# Functional Specification Document (FSD)
## Product: [Name TBD] — AI Engineering Intelligence Platform
**Version:** 1.0 | **Status:** Draft | **Date:** 2026-05-28
**Reference:** BRD v1.0, Architecture doc (VibeROI-DataSource-Master.md)

---

## 1. RBAC Matrix

| Action | Org Admin | Team Lead | Developer |
|---|---|---|---|
| View all developers' data | ✅ | ✅ (own team only) | ❌ |
| View own session data | ✅ | ✅ | ✅ |
| View KPI dashboards | ✅ all | ✅ team | ❌ |
| View My Activity | ✅ | ✅ | ✅ |
| Access Unknown Queue | ✅ all | ✅ team only | ❌ |
| Assign unattributed sessions | ✅ | ✅ | Own only |
| Manage team members | ✅ | ✅ (own team) | ❌ |
| Connect integrations (GitHub/Jira) | ✅ | ❌ | ❌ |
| Declare AI tools for org/team | ✅ | ✅ (own team) | Add personal only |
| View billing / subscription | ✅ | ❌ | ❌ |
| Export data | ✅ | ✅ | Own only |
| Delete sessions | ❌ (no one) | ❌ | ❌ |

---

## 2. Authentication Flows

### F-AUTH-01: Signup
**Trigger:** User visits /signup
**Steps:**
1. User enters work email (e.g. adnan@company.com)
2. System validates: not a consumer domain (gmail, yahoo, hotmail, outlook blocked)
3. System checks: domain not already registered (prevents duplicate orgs)
4. System sends verification email with 6-digit OTP + magic link (10-minute expiry)
5. User clicks link or enters OTP
6. Org created with domain lock (only @company.com emails can join)
7. User becomes Org Admin, 14-day trial begins
8. Redirect to /onboarding/step-1

**Error states:**
- Consumer email → "Please use your work email address"
- Domain already registered → "Your team is already on [Product]. Ask your admin to invite you."
- OTP expired → "This link has expired. Resend verification email."

### F-AUTH-02: Login
1. Enter email → verify domain lock
2. Send magic link (passwordless) OR Google/GitHub OAuth (if domain matches)
3. JWT issued (access: 1h, refresh: 30d, httpOnly cookie)
4. Redirect to /dashboard

### F-AUTH-03: Team Invite
1. Admin enters email(s) or GitHub usernames in Manage Team
2. System validates email domain matches org domain
3. Invite email sent with personalised agent install command + signup link
4. Invitee signs up → auto-joins org (no second admin approval)
5. Role assigned as set by admin (Team Lead or Developer default)

### F-AUTH-04: Session management
- JWT refresh: silent background refresh 5 minutes before expiry
- Logout: invalidate refresh token, clear cookies
- Simultaneous sessions: allowed (web + agent use different token types)

---

## 3. Onboarding Flow

### F-ONB-01: Step 1 — Email verified → Welcome
- Screen: "Welcome to [Product]. Let's set up your workspace."
- Progress bar: 0/5 steps complete
- CTA: "Connect your repositories →"

### F-ONB-02: Step 2 — Connect Source 3
**GitHub connection:**
1. Click "Connect GitHub" → GitHub App install page
2. Select repos (or "All repositories")
3. Return to app → show: "Connected. Syncing 90 days of history..."
4. Background job starts (Jira/Linear tickets + PRs backfilled)
5. Live progress: "Synced 847 tickets, 12 sprints" (updates every 10s via SSE)

**Ticketing connection (shown after GitHub):**
- Options: Jira / Linear / GitHub Issues (use existing GitHub connection)
- Jira: OAuth → show board list → user selects boards to track
- Linear: OAuth → show teams → user selects teams
- GitHub Issues: no extra auth, auto-configured from Step 2

**Backfill messaging:** "We're importing your last 90 days of tickets and PRs.
This creates your baseline — AI cost data starts when agents are installed."

### F-ONB-03: Step 3 — Configure AI tools
- Org-level tool selection: checkboxes for Claude Code, Cursor, Kiro, Copilot
- Sub-steps triggered per tool:
  - Kiro selected → "Enter your S3 bucket name + IAM role ARN"
  - Copilot selected → "Connect your GitHub org for usage data"
- Note: "You can configure different tools per team later"

### F-ONB-04: Step 4 — Add team members
- Input: paste emails or GitHub usernames (one per line, or comma-separated)
- Role selector per member (Team Lead / Developer)
- Optional hourly rate per developer (for Cost per ticket KPI)
- CTA: "Send invitations"
- After send: shows list with status (Invited / Installed / Pending)

### F-ONB-05: Step 5 — Install agent
- Shows personalised install command (org_token embedded)
- Three tabs: Windows / Mac / Linux
- Windows: `iwr https://get.[product].io/install.ps1 | iex -OrgToken ORG_TOKEN`
- Mac: `curl -fsSL https://get.[product].io/install.sh | sh -s ORG_TOKEN`
- "Send via Slack/Teams" optional button
- Enterprise MDM download button (generates .msi/.pkg with org_token baked in)
- Status: "3 of 8 agents installed" (live, updates as agents register)

### F-ONB-06: Waiting for first session
- Shows animated waiting state
- "Your team is set up. Waiting for the first AI session..."
- When first session arrives: confetti animation → "First session captured!"
- Shows: which developer, which tool, which ticket (if attributed)
- CTA: "View your dashboard →"

**Persistent onboarding checklist** (shown in corner until complete):
```
✅ Email verified
✅ GitHub connected
✅ Jira connected
✅ AI tools configured
⬜ Team added (0/8 invites accepted)
⬜ First session captured
```

---

## 4. Screen Specifications

### S-01: Team Dashboard (default landing)
**Route:** /dashboard
**Access:** Org Admin, Team Lead
**Purpose:** High-level health overview across all KPIs

**Header:**
- Product logo + org name
- Date range picker (7d / 30d / 90d / custom) — default 30d
- Team filter dropdown (All teams / specific team)
- Notification bell
- User avatar + role badge

**KPI summary row (4 cards):**
1. AI-Assisted Code Contribution % (status: HEALTHY/WATCH/AT RISK)
2. AI Productivity Lift (multiplier, e.g. 1.44x)
3. AI Code Quality % (status badge)
4. Total AI Spend ($ in period)

**Middle row:**
- AI Usage Percentage chart (line, weekly, % active developers)
- AI Tools Breakdown (donut: Cursor 52%, Claude Code 22%, Kiro 14%, Copilot 12%)

**Bottom row:**
- AI PR Size (AT RISK badge if avg LOC >1000)
- AI Commits per Dev per Day (trend)

**Hallucination alert banner** (shows when KPI 5 triggered):
- "⚠️ 2 developers may be stuck. View alerts →"
- Dismissible, re-surfaces on next alert

**Empty state:** "No data yet. Install agents on developer machines to start."

---

### S-02: AI Insights
**Route:** /insights
**Access:** Org Admin, Team Lead
**Purpose:** Deep AI adoption and quality metrics

**Sections:**
1. AI-Assisted Code Contribution % — bar chart by developer (anonymised if team lead, named if admin)
2. AI Productivity Lift — trend over time + comparison to baseline
3. AI Code Quality — churn rate breakdown
4. AI Usage Percentage — heatmap by developer × week
5. AI Tools Breakdown — donut + table with cost per tool
6. AI PR Size — histogram, flag PRs >1000 LOC
7. AI Commits Per Dev Per Day — sparklines per developer

**Filters:** Tool filter (All / Claude Code / Cursor / Kiro / Copilot), Developer filter

---

### S-03: ROI View
**Route:** /roi
**Access:** Org Admin, Team Lead
**Purpose:** Financial view — the CFO screen

**Summary cards:**
- Blended AI ROI (multiplier, e.g. 3.8x)
- Total AI Spend ($)
- Average Engineer AI Spend ($/dev/month)
- Hours Saved estimate (requires baseline data)

**Daily AI ROI heatmap** (last 90 days, loss/breakeven/gain per day)

**Spend by Feature/Epic table:**
| Feature | AI Cost | LOC | ROI |
|---|---|---|---|
| Auth & Onboarding | $6,000 | 14.2k | +3.8x |
| Data Pipelines | $3,600 | 6.4k | -0.8x (red) |

Negative ROI rows highlighted in red. Clickable to drill into sessions.

**Tabs:** Summary / Developer Impact / How AI Is Used / Features / Activity

---

### S-04: Developer Profiles (People)
**Route:** /people
**Access:** Org Admin (all), Team Lead (own team)
**Purpose:** Per-developer AI usage and spend

**List view:**
- Table: Developer name, role, team, spend (30d), sessions, efficiency score, agent status
- Sort by any column
- Click row → detail view

**Detail view (/people/:id):**
- 7-day summary cards: Sessions/day, Agent interactions/day, Files changed/day
- LOC changed (+ added / - deleted per day)
- Mode breakdown: Ask% / Agent% / Plan% / Edit%
- Tokens in/out per day
- Commits: count + accepted lines, broken out by tool
- Model usage breakdown
- Tab: "Agent Sessions" → chronological list of sessions with attribution

**Privacy rule in code:** Developer can only access /people/:their-own-id. Lead can access team. Admin accesses all. Enforced at API layer + RLS.

---

### S-05: Capacity Overview
**Route:** /capacity
**Access:** Org Admin, Team Lead
**Purpose:** Cycle time and delivery intelligence

**AI-assisted vs human-only cycle time:**
- Line chart: weekly P50 cycle time, two lines (AI-assisted teal, human-only red)
- Annotation: "AI-assisted PRs close ~3x faster"

**Lifecycle decomposition:**
- Stacked horizontal bar: prompt→commit / commit→PR / PR→review / review→merge
- Two bars: AI-assisted vs human-only
- Shows exactly where time is spent and where AI compresses it

**Sprint selector:** Last 4 / 8 / 12 sprints

**Team filter:** All teams / specific team

---

### S-06: Unknown Attribution Queue
**Route:** /queue
**Access:** Org Admin (all), Team Lead (team only)
**Purpose:** Assign unattributed sessions to tickets

**Table:**
| Developer | Tool | Duration | Cost | Branch | Suggested Ticket | Actions |
|---|---|---|---|---|---|---|
| Adnan | Claude Code | 74 min | $0.42 | patch-2 | — | [Assign][Ignore][Exploratory] |
| Sara | Cursor | 45 min | $1.20 | wip-auth | JIRA-155 (48%) | [Confirm][Assign][Ignore] |

**Assign action:** Opens modal with search box → search tickets by ID or title → select → save
**Ignore:** Marks as non-attributable overhead (excluded from ticket KPIs)
**Exploratory:** Marks as exploratory/R&D work (separate cost category)
**Confirm:** Accepts the suggested ticket → becomes confirmed attribution

**Filter:** By developer, by tool, by date range, by status (pending/assigned/ignored)

**Summary banner:** "12 sessions ($8.40) need attribution. This represents 3% of sprint spend."

---

### S-07: My Activity
**Route:** /me
**Access:** All roles (own data only)
**Purpose:** Developer's view of their own AI usage

**Cards:** Sessions today, tokens today, sessions this week, cost this week (estimate)

**Session list:** Chronological, own sessions only
- Each row: timestamp, tool, duration, branch, attributed ticket (or "Unattributed" with tag button), cost

**Tag unattributed:** Click "Tag" → search own tickets → assign

**No comparison to other developers anywhere on this screen.**

---

### S-08: Settings — Integrations
**Route:** /settings/integrations
**Access:** Org Admin only

**Sections:**
- Version Control: GitHub (connected/not), GitLab (add)
- Ticketing: Jira (connected), Linear (add), GitHub Issues (auto)
- AI Tool Setup: per-tool Source 2 config (S3 bucket for Kiro, API key for Copilot)
- Notification Channels: Slack (connected), Teams (add), Email (always on)

Each integration shows: status, last sync time, connected by, disconnect button

---

### S-09: Settings — Manage Team
**Route:** /settings/team
**Access:** Org Admin (all), Team Lead (own team)

**Sections:**
- Team list table: name, email, role, team, agent status (installed/pending/offline), last active
- Invite button → opens invite modal
- Per-developer: edit role, set hourly rate, resend install link, remove from org

**Teams management (admin only):**
- Create team, name team, assign members, assign team lead
- Tool declarations per team (overrides org default)

**Agent status badges:**
- Green dot: installed + active last 7 days
- Yellow dot: installed + inactive >7 days
- Grey dot: installed + never sent session
- Red dot: invited + not installed

---

### S-10: Settings — Billing
**Route:** /settings/billing
**Access:** Org Admin only

**Shows:**
- Current plan (Starter/Growth/Scale/Enterprise)
- Active device count this month (with breakdown of active vs inactive)
- Current month estimated bill
- Next billing date
- Payment method (card on file or invoice)
- Usage history (last 6 months, monthly breakdown)

**Upgrade/downgrade:** Shows tier comparison, CTA to upgrade
**Trial users:** Shows days remaining, devices used, conversion CTA with real usage data

---

## 5. Error States (Global)

| Error | UI Response |
|---|---|
| API timeout | "Something took too long. Refresh or try again." + retry button |
| No data (empty state) | Context-specific empty state with install/setup CTA |
| Agent offline | Yellow banner: "Agent offline on X machines. [View →]" |
| Integration sync failed | Warning icon on integration → "Last sync failed 2h ago. [Retry]" |
| Attribution confidence < 50% | WATCH badge + "Low confidence — check unknown queue" |
| Hallucination loop detected | Alert banner on dashboard + Slack/Teams notification |
| Trial expired | Full-page gate: "Your trial ended. [View your data] [Upgrade]" |
| Billing failed | Banner: "Payment failed. Update payment method to restore access." |
| 403 Forbidden | "You don't have access to this. Ask your admin." |
| 404 | "This page doesn't exist." + back link |

---

## 6. Notification Specifications

### N-01: Agent install invite
**Trigger:** Admin invites a developer
**Channel:** Email + Slack DM (if connected)
**Content:** "Your team is using [Product]. Install the agent in 2 minutes:" + personalised command

### N-02: Hallucination loop alert
**Trigger:** KPI 5 threshold crossed (token spike >3x OR file oscillation >5 in 2h OR >3 restarts in 4h)
**Channel:** Slack/Teams DM to Team Lead
**Content:** "⚠️ [Developer] may be stuck on [JIRA-142]. 3h session, $4.20 spent, no commit. Worth checking in."

### N-03: Weekly digest
**Trigger:** Monday 08:00 org timezone
**Channel:** Team Lead + Org Admin email + optional Slack channel
**Content:** Sprint AI spend vs last sprint, top cost tickets, unattributed session count

### N-04: Unknown queue reminder
**Trigger:** Weekly, if queue has >5 sessions
**Channel:** Team Lead DM
**Content:** "12 sessions ($8.40) need attribution. [Review queue →]"

### N-05: Trial ending
**Trigger:** 3 days before trial end, 1 day before, day of
**Channel:** Email to Org Admin
**Content:** Usage summary + upgrade CTA with real numbers

---

## 7. Agent Registration Flow

1. Agent starts → reads org_token from config file (~/.vibeROI/config.json)
2. POST /ingest/register with { org_token, machine_id, os, version, declared_tools }
3. Backend validates org_token → resolves org
4. Checks machine_id not already registered to a different org → flags if so
5. Creates/updates developer record (matches by machine user identity)
6. Returns { developer_id, org_config, tools_config }
7. Agent stores developer_id locally, begins monitoring declared tools

**Re-registration:** If developer_id is already known, updates last_seen + version. No duplicate creation.

---

## 8. Key User Flows

### Flow 1: EM sees a spike in AI spend
1. EM opens ROI view → sees "Data Pipelines: -0.8x ROI" in red
2. Clicks row → drill into sessions for that epic
3. Sees: 5 sessions on JIRA-151, 3 of them flagged with hallucination risk
4. Clicks JIRA-151 → session detail → sees token spike at turn 12
5. Sends Slack DM to developer: "Saw you hit a wall on JIRA-151 — need help?"

### Flow 2: Developer has unattributed sessions
1. Developer opens My Activity → sees 3 sessions marked "Unattributed"
2. Clicks "Tag" on first session → searches "payment" → finds JIRA-142
3. Assigns → session now attributed
4. Admin sees Unknown Queue shrink by 1

### Flow 3: New org onboards
1. EM signs up with work email → verifies → creates org
2. Connects GitHub → connects Jira → 90-day backfill runs
3. Configures tools (Cursor + Claude Code for their team)
4. Invites 15 developers → they receive Slack DMs with install commands
5. 12 of 15 install within an hour
6. First session captured → EM gets Slack notification: "First session attributed to JIRA-142"
7. EM opens dashboard → sees first real data


---

## 9. Additional Screen Specifications

### S-11: General Metrics
**Route:** /metrics
**Access:** Org Admin, Team Lead
**Purpose:** Engineering health metrics — the DORA-adjacent view that gives context before AI was introduced and shows where AI is compressing delivery

**Summary cards (top row):**
- Deployment Frequency (per week, trend arrow)
- Lead Time for Changes (hours, P50)
- Change Failure Rate (%)
- Mean Time to Recovery (hours)

**Second row — AI context:**
- AI-assisted PRs this sprint (count + % of total)
- Average PR size: AI vs human (LOC comparison)
- Code review iterations: AI vs human (avg comments per PR)
- First-time pass rate: AI vs human (% PRs merged without revision)

**Charts:**
- Weekly commit cadence (bar chart, last 12 weeks, AI-touched vs clean)
- PR merge time distribution (histogram, AI vs human two colours)
- Lines of code per developer per week (sparklines, each developer)
- Model usage breakdown (which models used, by session count)

**Filters:** Sprint selector, team filter, tool filter

**Insight callout:** Auto-generated sentence at top:
"AI-assisted PRs are merging 2.3x faster than human-only PRs this sprint."

---

### S-12: Agentic Insights
**Route:** /agentic
**Access:** Org Admin, Team Lead
**Purpose:** Deep view into how developers are using AI in agentic mode — the highest-cost, highest-value sessions

**What is agentic mode:** Sessions where the AI agent autonomously uses tools (Write, Read, Edit, bash commands) rather than just chatting. Higher token cost, higher potential value.

**Summary cards:**
- Agentic sessions this period (count + % of all sessions)
- Avg cost per agentic session ($)
- Avg duration per agentic session (minutes)
- Avg files touched per agentic session (count)

**Agentic session breakdown table:**
| Developer | Sessions | Avg Cost | Avg Duration | Files Touched | Commit Rate | Hallucination Risk |
|---|---|---|---|---|---|---|
| Adnan | 12 | $1.20 | 84 min | 6.3 | 91% | 1 watch |
| Sara | 8 | $0.85 | 62 min | 4.1 | 88% | 0 |

**Charts:**
- Agentic vs chat session ratio over time (stacked bar, weekly)
- Cost distribution: agentic sessions (histogram — shows long tail)
- Tool call frequency (which tools called most: Write, Read, Edit, Bash)
- Subagent spawn rate (Claude Code only — sessions that spawned subagents)

**Mode breakdown donut:**
Ask / Chat / Agent / Plan / Edit — % of all sessions by mode

**Note:** Data availability varies by tool. Claude Code and Cursor have full agentic detail. Kiro is always agentic by design. Copilot has limited mode data.

---

### S-13: Sprint Detail Drill-Down
**Route:** /sprints/:sprintId
**Access:** Org Admin, Team Lead
**Purpose:** Everything about one sprint — AI spend, tickets, quality

**Reached from:** ROI view → click a sprint row

**Header:**
- Sprint name + dates
- Status badge (Active / Completed)
- Summary: X tickets, Y developers, Z AI sessions

**Four summary cards:**
- Total AI spend for sprint ($)
- Tickets completed (count)
- AI cost per completed ticket (avg $)
- Sprint AI ROI (multiplier if baseline exists)

**Tickets table (main content):**
| Ticket | Developer | AI Cost | Sessions | AI Contribution % | Status | ROI |
|---|---|---|---|---|---|---|
| JIRA-142 | Adnan | $4.20 | 3 | 82% | Done | +3.2x |
| JIRA-151 | Sara | $8.40 | 7 | 71% | In Progress | watch |

- Red row: negative ROI or hallucination risk
- Click ticket → goes to S-14 (Ticket Detail)

**Bottom charts:**
- Daily spend within sprint (bar chart by day)
- Developer spend distribution (horizontal bar, each dev's % of sprint AI budget)
- Tools used this sprint (donut)

**Compare to previous sprint:** Toggle shows side-by-side with last sprint numbers

---

### S-14: Ticket Detail Drill-Down
**Route:** /tickets/:ticketId
**Access:** Org Admin, Team Lead
**Purpose:** Every AI session attributed to one ticket

**Reached from:** Sprint detail → click ticket, or Unknown Queue → click ticket

**Header:**
- Ticket ID + title (from Jira/Linear)
- Status, Assignee, Epic, Sprint
- Attribution confidence badge (if < 0.80 show WATCH)

**Cost summary:**
- Total AI cost for this ticket ($)
- Total human time estimate (hours × rate if set)
- True total cost (AI + human time)
- Lines of code (AI-generated, accepted, reverted)

**Sessions table:**
| Date | Developer | Tool | Duration | Cost | Mode | Quality | Branch |
|---|---|---|---|---|---|---|---|
| 28 May | Adnan | Claude Code | 74 min | $0.42 | Agent | ✅ | feature/JIRA-142 |
| 27 May | Adnan | Cursor | 45 min | $1.20 | Chat | ⚠️ spike | feature/JIRA-142 |

- Click session row → goes to S-15 (Session Detail)

**Timeline view:**
- Horizontal timeline showing: first session → commits → PR opened → PR merged
- Shows the prompt→commit→PR→merge lifecycle for this ticket specifically

**Attribution signals shown:**
- Which signals fired for this attribution
- Confidence score with breakdown
- Manual override option (manager can reassign)

---

### S-15: Session Detail
**Route:** /sessions/:sessionId
**Access:** Org Admin (all), Team Lead (team), Developer (own only)
**Purpose:** Everything about one AI session — the atomic unit of the product

**Reached from:** Ticket detail → click session, Developer profile → click session

**Header:**
- Session ID, date/time
- Developer name, tool, model
- Branch → attributed ticket (with confidence badge)
- Duration, total cost

**Six stat cards:**
- Input tokens
- Output tokens
- Cache reads (Claude Code only)
- Turn count
- Files touched (count)
- Subagents spawned (Claude Code only)

**Quality signals section:**
- Token spike: yes/no + which turns spiked
- File oscillations: count (which files)
- Session restarts: count for this ticket in 4h window
- Commit status: committed / uncommitted at end
- Hallucination risk: none / watch / alert with reason

**Files touched list:**
- List of file paths touched in session (no content)
- Each file: how many times touched (oscillation signal)

**Git output:**
- Lines added / deleted / accepted / reverted
- Commit hashes (clickable to GitHub)
- Branch name

**Timeline bar:**
- Visual: session start → first tool call → last tool call → commit
- Shows active vs idle time within session

**Cost breakdown:**
- Input tokens × rate
- Output tokens × rate
- Cache read × rate (Claude Code)
- Cache write × rate (Claude Code)
- Total (with is_estimated indicator if not exact)

**Source indicator:**
- "Data source: Local JSONL (exact)" or "Local SQLite (exact)" or "Estimated"
- Reconciled: yes/no + last reconciled time

---

### S-16: Hallucination Alerts Detail
**Route:** /alerts
**Access:** Org Admin, Team Lead
**Purpose:** Active and recent hallucination loop detections

**Alert list:**
| Developer | Ticket | Triggered | Signals | Session Cost | Status | Action |
|---|---|---|---|---|---|---|
| Adnan | JIRA-151 | 2h ago | Token spike + no commit | $4.20 | Active | [View Session] [DM Developer] |
| Sara | JIRA-155 | Yesterday | 3 restarts in 4h | $2.80 | Resolved | [View] |

**Alert detail (expanded row):**
- Which specific signals triggered
- Token spike chart: shows the turn where tokens went >3× avg
- Timeline of events: turn 1, turn 2... turn N (spike here)
- Recommended action: "Developer may be stuck. Consider checking in."

**Alert thresholds (shown for reference):**
- Token spike: >3× session average
- File oscillation: same file >5× in 2 hours
- Session restarts: >3 for same ticket in 4 hours
- No commit: >90 minutes with no commit in a 4-hour window

**Filters:** Active only / All / By developer / By tool / By date

**DM Developer button:** Opens notification composer → sends Slack/Teams DM to developer directly from this screen

---

### S-17: Login Screen
**Route:** /login
**Access:** Public

**Layout:** Centered card, clean, minimal

**Fields:**
- Email input (work email)
- "Send magic link" button (primary action — passwordless)

**Alternative:**
- "Continue with GitHub" (GitHub OAuth, if domain matches org)
- "Continue with Google" (Google OAuth, if domain matches org)

**States:**
- Default: email input + button
- Submitted: "Check your email — we've sent a magic link to adnan@company.com"
- Error: "No account found for this email. [Sign up instead →]"
- Wrong domain for OAuth: "This login doesn't match your organisation's email domain"

**Footer links:** "Don't have an account? Sign up" | "Need help? hello@[product].io"

---

### S-18: Signup Screen
**Route:** /signup
**Access:** Public

**Layout:** Centered card, step indicator (1 of 2)

**Step 1 — Email:**
- Work email input
- "Create account" button
- Validation: blocks gmail/yahoo/hotmail/outlook domains with message:
  "Please use your work email address"
- Checks if domain already exists: "Your team is already on [Product].
  Ask your admin to invite you instead."

**Step 2 — Verify:**
- "We've sent a 6-digit code to adnan@company.com"
- 6-digit OTP input (auto-focus, auto-advance)
- "Resend code" link (appears after 60 seconds)
- Magic link alternative: "Or click the link in your email"
- OTP expiry: 10 minutes — show countdown
- Error: "That code is incorrect. Try again or resend."

**After verification:**
- Auto-redirect to /onboarding/step-1
- Org created, domain locked, admin role assigned, 14-day trial begins

---

### S-19: Onboarding — Step 1 (Welcome)
**Route:** /onboarding/welcome
**Progress bar:** 0 of 5 steps

**Content:**
- Large welcome heading: "Welcome to [Product]"
- Subtext: "Let's get your team set up. Takes about 10 minutes."
- Three preview cards showing what they'll unlock:
  1. "See AI cost per ticket" → icon of ticket + dollar
  2. "Catch hallucination loops early" → icon of alert
  3. "Prove AI ROI to leadership" → icon of chart
- Primary CTA button: "Connect your repositories →"
- Skip text: "Already set up? [Go to dashboard]" (grayed out until complete)

---

### S-20: Onboarding — Step 2 (Connect Source 3)
**Route:** /onboarding/connect
**Progress bar:** 1 of 5

**Two sub-steps shown sequentially:**

**Sub-step A — Version Control:**
- Heading: "Connect your repositories"
- Single large button: "Connect GitHub App"
- On click: Opens GitHub OAuth in new tab → returns to this page
- After connect: Shows green checkmark + "4 repositories connected"
- Also shows: "Using GitLab? [Connect GitLab instead]"

**Sub-step B — Ticketing (appears after GitHub connected):**
- Heading: "Connect your ticketing tool"
- Three option cards side by side:
  - Jira → "OAuth" badge + Connect button
  - Linear → "OAuth" badge + Connect button
  - GitHub Issues → "Already connected" badge (auto from GitHub)
- After connect: Shows "847 tickets found, 12 sprints detected"
- Backfill progress bar: "Importing 90 days of history... 43%"
- Message below bar: "This sets your baseline. AI costs appear after agent install."
- CTA: "Continue →" (enabled even while backfill runs — non-blocking)

---

### S-21: Onboarding — Step 3 (Configure Tools)
**Route:** /onboarding/tools
**Progress bar:** 2 of 5

**Heading:** "Which AI tools does your team use?"

**Org-level selection (checkboxes, large cards):**
```
☑ Claude Code    ☑ Cursor    ☐ Kiro    ☐ Copilot    ☐ Windsurf
```

**Team override section (expandable):**
- "Configure per team →" — expands to show team list
- Each team row: team name + tool checkboxes
- "Platform team: ☑ Cursor ☑ Copilot ☐ Claude Code"

**Source 2 setup (shown per tool selected):**
- Kiro selected → input field: "S3 bucket name" + "IAM Role ARN"
  with link: "[How to set this up →]"
- Copilot selected → "Connect GitHub org for usage data"
  button: "Connect Copilot Metrics →"
- Claude Code → No extra setup needed
  small note: "Reading local JSONL files. No API required."
- Cursor → No extra setup needed
  small note: "Reading local SQLite. No API required."

**CTA:** "Continue →"

---

### S-22: Onboarding — Step 4 (Add Team)
**Route:** /onboarding/team
**Progress bar:** 3 of 5

**Heading:** "Add your team members"

**Input area:**
- Large text area: "Paste GitHub usernames or work emails, one per line"
- Placeholder: "adnan@company.com\nsara@company.com\nraj_dev"
- Role selector below: "Default role: [Developer ▼]" (can set per-person after)
- Optional: "Set hourly rate for cost tracking: $[___]/hour" (used for KPI 3)

**After paste + "Add members":**
- Shows parsed list with match status:
  "✅ adnan@company.com → Adnan Khan (matched GitHub)"
  "✅ sara@company.com → Sara Patel (matched GitHub)"
  "⚠️ raj_dev → No GitHub account found — will invite by email"
- Role can be changed per person in this list (dropdown)
- Remove button per person

**Send invitations button:**
- On click: Sends email + Slack DM (if channel connected) to each person
- Shows: "Invitations sent to 8 team members"
- Each developer will receive personalised agent install link

**CTA:** "Continue →"
**Note below:** "You can add more team members anytime from Manage Team"

---

### S-23: Onboarding — Step 5 (Install Agent)
**Route:** /onboarding/agent
**Progress bar:** 4 of 5

**Heading:** "Install the agent on your machine"

**Three OS tabs:**
- Windows | Mac | Linux (default: Windows)

**Windows command box:**
```
iwr https://get.[product].io/install.ps1 | iex -OrgToken YOUR_TOKEN_HERE
```
- Copy button on the right
- YOUR_TOKEN_HERE is pre-filled with their actual org token

**Mac/Linux:**
```
curl -fsSL https://get.[product].io/install.sh | sh -s YOUR_TOKEN_HERE
```

**Send via Slack button:** "📨 Send install link to team via Slack"
- Sends DM to each team member with their personalised command

**Enterprise MDM section (collapsed by default):**
"Enterprise deployment →" — expands to:
- Download .msi (Windows) / .pkg (Mac) / .deb (Linux)
- Pre-baked with org token
- "Deploy via Jamf/Intune with zero developer action"

**Live install status (updates in real time via SSE):**
```
Team members:
✅ Adnan Khan     → Agent installed (just now)
⏳ Sara Patel     → Invited, pending install
⏳ Raj Kumar      → Invited, pending install
```

**CTA:** "Continue →" (can skip — agents can be installed later)

---

### S-24: Onboarding — Step 6 (Waiting for First Session)
**Route:** /onboarding/waiting
**Progress bar:** 5 of 5 (almost complete)

**States:**

**State A — Waiting (no session yet):**
- Animated pulse indicator
- Heading: "Waiting for first AI session..."
- Subtext: "Open your AI coding tool and start working.
  The agent will capture the session automatically."
- Live status cards:
  "5 of 8 agents installed"
  "0 sessions captured"
  "Backfill: complete ✅"
- Checklist:
  ```
  ✅ Email verified
  ✅ GitHub connected (4 repos)
  ✅ Jira connected (847 tickets, 12 sprints)
  ✅ Tools configured (Claude Code, Cursor)
  ✅ Team added (8 members)
  ✅ 5 of 8 agents installed
  ⬜ First session captured ← waiting
  ```

**State B — First session captured:**
- Confetti animation
- Heading: "First session captured! 🎉"
- Shows the session details:
  "Adnan Khan · Claude Code · 74 min · $0.42
   Attributed to: JIRA-142 (confidence: 87%)"
- CTA: "View your dashboard →" (primary, large)
- Secondary: "View session detail →"

---

## 10. ROI View — All 5 Tabs (S-03 expanded)

### Tab 1: Summary (already specced in S-03)

### Tab 2: Developer Impact
**Purpose:** Per-developer contribution to AI ROI

**Table:**
| Developer | AI Cost (30d) | Tickets Closed | Cost/Ticket | AI Code % | Efficiency Score |
|---|---|---|---|---|---|
| Adnan | $142 | 8 | $17.75 | 84% | 78/100 |
| Sara | $98 | 6 | $16.33 | 71% | 82/100 |

- Sort by any column
- Click row → goes to developer profile (S-04)
- Efficiency score: colour-coded (green >75, yellow 50-75, red <50)
- Admin sees names. Team lead sees their team only.

**Bottom chart:** Scatter plot — Cost per ticket (x) vs Tickets closed (y)
- Each dot = one developer
- Top-right quadrant = high output, efficient (good)
- Bottom-left = low output, high cost (needs attention)
- No developer names on shared screens — dots are anonymous to peers

---

### Tab 3: How AI Is Used
**Purpose:** Break down of HOW the team uses AI — modes, models, tools

**Mode breakdown (donut):**
Ask 18% / Agent 62% / Plan 8% / Edit 12%

**Model usage (bar chart):**
- Which models used (claude-sonnet-4-6, claude-haiku, gpt-4o, etc.)
- Sessions per model (not cost — model pricing varies)

**Tool call distribution (horizontal bar):**
- Write, Read, Edit, Bash, Search, WebFetch — which tool calls dominate
- More Write/Edit = more autonomous output
- More Search/Fetch = more research sessions (different cost profile)

**Session length distribution (histogram):**
- Distribution of session durations (5-15min, 15-30, 30-60, 60-90, 90+)
- Shorter sessions = lighter tasks
- Very long sessions (90+ min no commit) = hallucination risk bucket

**Accepted vs reverted lines (stacked bar, weekly):**
- Green: lines that survived to merge
- Red: lines that were reverted/not accepted
- Ratio = churn rate over time

---

### Tab 4: Features
**Purpose:** Spend and ROI broken down by epic/feature area

**This is the key differentiator screen — no competitor shows this.**

**Feature table:**
| Feature Area | Epic | Tickets | AI Cost | LOC | Avg Cost/Ticket | ROI | Trend |
|---|---|---|---|---|---|---|---|
| Auth & Onboarding | EPIC-01 | 12 | $6,000 | 14.2k | $500 | +3.8x | ↑ |
| Checkout & Payments | EPIC-03 | 8 | $5,400 | 9.8k | $675 | +4.6x | ↑ |
| Data Pipelines | EPIC-07 | 5 | $3,600 | 6.4k | $720 | -0.8x | ↓ red |

- Negative ROI rows: red background, flagged
- Click row → filters Sprint Detail to that epic
- "What counts as ROI": estimated from ticket close rate × story points × team velocity constant. Requires baseline data. Shows methodology tooltip.

**Treemap chart:**
- Visual size = AI cost
- Visual colour = ROI (green=good, red=negative)
- At a glance: biggest spend + worst ROI bubbles to surface

---

### Tab 5: Activity
**Purpose:** Time-series activity view — when is AI being used

**Heatmap (GitHub contribution graph style):**
- X axis: days (last 90 days)
- Y axis: developers
- Cell colour: darker = more sessions that day
- Hover: "Adnan — 4 sessions, $8.40, 3 tickets touched"

**Daily active users chart (line, last 90 days):**
- Count of developers with ≥1 session per day
- Shows weekday/weekend pattern
- Shows adoption growth over time

**Session timing distribution:**
- Bar chart: sessions by hour of day (9am, 10am... 10pm)
- Shows when team is most active with AI tools
- Useful for understanding work patterns, not surveillance

**Peak sprint usage:**
- Which sprints had highest AI activity
- Correlation with sprint goals (heavy AI = feature sprint, low = bug sprint)

---

## 11. Global Navigation Specification

**Left sidebar (persistent, collapsible):**

```
[Product Logo + Name]

─── INSIGHTS ───────────
  Team Dashboard         /dashboard
  AI Insights            /insights
  ROI                    /roi
  Agentic Insights       /agentic
  General Metrics        /metrics
  Capacity Overview      /capacity

─── TEAM ───────────────
  My Activity            /me
  People                 /people

─── MANAGEMENT ─────────
  Unknown Queue          /queue      [badge: count]
  Alerts                 /alerts     [badge: active]

─── SETTINGS ───────────
  Integrations           /settings/integrations
  Manage Team            /settings/team
  Billing                /settings/billing
```

**Role-based nav visibility:**
- Developer sees: My Activity only (no dashboard, no insights, no queue)
- Team Lead sees: All except Billing
- Org Admin sees: Everything

**Top bar (persistent):**
- Date range picker (default: last 30 days)
- Team filter (All teams / specific team)
- Notification bell (badge when alerts or queue items)
- User avatar → dropdown: My Activity / Settings / Logout

**Breadcrumb (for drill-down screens):**
- Dashboard → Sprint 42 → JIRA-142 → Session detail
- Back button on all drill-down screens

