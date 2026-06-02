# Business Requirements Document (BRD)
## Product: [Name TBD] — AI Engineering Intelligence Platform
**Version:** 1.0 | **Status:** Draft | **Date:** 2026-05-28
**Reference:** Architecture doc (VibeROI-DataSource-Master.md) for all technical decisions

---

## 1. Executive Summary

Engineering teams are spending $200–$2,000 per developer per month on AI coding tools with no visibility into whether that spend is producing value. There is no tool today that connects AI session activity to tickets, sprints, and business outcomes — at the granularity needed to make decisions.

This product closes that gap. It captures AI usage data from developers' local machines, attributes it to tickets and sprints, and gives engineering leaders the metrics needed to justify, optimize, and govern AI spend.

---

## 2. Problem Statement

| Who | Pain |
|---|---|
| Engineering Manager | Gets a monthly AI bill with no breakdown by feature, team, or outcome. Cannot prove ROI to leadership. Cannot identify developers who are stuck in loops. |
| Tech Lead | Has no visibility into which tickets are consuming disproportionate AI time. Cannot detect hallucination loops early. Attribution of AI work to PRs is manual. |
| Developer | Doesn't know their own AI usage patterns. Has no data on whether their prompting style is effective. |
| CFO / VP Eng | Cannot answer "what did we get for $X in AI tool spend last quarter?" |

---

## 3. Product Vision

**One sentence:** Give engineering leaders exact, ticket-attributed AI cost and quality metrics — without reading a single prompt or line of code.

**Core principle:** Privacy-first. We never store prompts, code, or diffs. All intelligence comes from metadata: token counts, timestamps, file paths, session patterns.

---

## 4. Target Users

### Persona 1 — Engineering Manager (Primary Buyer)
- Title: VP Eng, Director of Engineering, Engineering Manager
- Company size: 15–500 developers
- Uses: Weekly/monthly reviews, sprint planning, board reporting
- Primary goal: Prove AI ROI, optimise tool spend, catch struggling developers early
- Key screens: ROI view, AI Insights, Capacity Overview, Sprint dashboard

### Persona 2 — Tech Lead (Primary Daily User)
- Title: Tech Lead, Senior Engineer, Staff Engineer
- Uses: Daily, often between meetings
- Primary goal: Monitor team quality, manage attribution, catch loops
- Key screens: Team Dashboard, Unknown Queue, Developer profiles

### Persona 3 — Developer (Optional Access)
- Title: Any developer with agent installed
- Uses: Occasionally, when nudged
- Primary goal: Understand own patterns, tag unattributed sessions
- Key screens: My Activity (own data only)
- Cannot see: Any other developer's data

---

## 5. Business Objectives

| Objective | Metric | Target (12 months) |
|---|---|---|
| Revenue | MRR | $50,000 |
| Adoption | Active orgs | 100+ |
| Retention | Monthly churn | <3% |
| Activation | Trial→paid conversion | >25% |
| NPS | Developer NPS | >30 (trust metric) |
| Time to value | First attributed session | <24 hours from signup |

---

## 6. Core Features — V1 Scope

### F1 — Agent data capture
- Lightweight Go agent installed per developer machine
- Reads IDE local files: Claude Code, Cursor, Kiro, GitHub Copilot
- Reads local git: branch switches, LOC changes (numbers only, no code)
- Pushes session objects to backend on session end
- Offline queue for network failures

### F2 — Attribution engine
- 5-signal confidence scoring (branch, file overlap, temporal, developer match, explicit mention)
- Sprint cohesion + ticket criticality modifiers
- Unknown queue for unattributed sessions
- Manager UI to manually assign/ignore unattributed sessions

### F3 — Source 3 integrations
- GitHub, GitLab (version control)
- Jira, Linear, GitHub Issues (ticketing)
- OAuth 2.0 / GitHub App
- 90-day historical backfill on connect

### F4 — KPI dashboard
- 24 KPIs across 4 views (AI Insights, ROI, People, Capacity)
- Real-time live counters (SSE)
- Drill-down from sprint → ticket → session
- Hallucination loop alerts (KPI 5)

### F5 — Notification system
- Slack, Microsoft Teams, Email, Google Chat
- Hallucination alerts, weekly digest, unknown queue reminders
- Agent install DM on team invite

### F6 — Onboarding
- Company email + domain verification
- 6-step guided setup with live progress
- 14-day trial, 5 devices, no card required

### F7 — Team management
- Invite by email or GitHub username
- Roles: Org Admin, Team Lead, Developer
- Per-developer hourly rate for cost KPIs
- Tool declaration per org/team/developer

---

## 7. Out of Scope — V1

| Feature | Reason | Target version |
|---|---|---|
| Prompt reading or content analysis | Privacy principle — never | Never |
| Code diff reading | Privacy principle | Never |
| Windsurf, JetBrains AI agents | Not yet verified | V1.5 |
| SAML/SSO | Enterprise complexity | V2 |
| SCIM provisioning | Enterprise complexity | V2 |
| ML-based attribution weight learning | Needs correction history first | V2 |
| LLM suggestion assistant (unknown queue) | Nice to have | V1.5 |
| Custom KPI builder | Too open-ended | V2 |
| Mobile app | Desktop-first | V2 |
| API for external consumers | Build internal first | V2 |
| On-prem deployment | Enterprise only | V2 |
| Azure DevOps, Bitbucket | Tier 2 tools | V1.5 |
| Shortcut, Asana, ClickUp | Tier 2/3 ticketing | V1.5 |

---

## 8. Constraints

| Constraint | Detail |
|---|---|
| Privacy | Never store prompts, code, diffs, or user-generated content |
| Data residency | AWS us-east-1 primary. Enterprise can request region preference |
| Agent footprint | <50MB RAM, <5% CPU peak, <10MB binary |
| Agent permissions | Read-only on IDE files and git repo. No write access. |
| Authentication | Company email only (no consumer email providers) |
| Compliance | SOC 2 Type II target (12 months post-launch) |

---

## 9. Success Criteria for V1

- [ ] Agent installs in <2 minutes on Windows, Mac, Linux
- [ ] First attributed session captured within 24 hours of signup
- [ ] Attribution confidence >80% for teams following branch naming conventions
- [ ] Dashboard loads KPI summary in <500ms
- [ ] Zero instances of prompt or code content stored
- [ ] 14-day trial → paying conversion rate >25%

---

## 10. Assumptions

1. Developers follow branch naming conventions (TICKET-ID in branch name). Attribution quality depends on this. The product educates and incentivises but does not enforce.
2. Teams are on GitHub or GitLab for version control. Other VCS is V1.5.
3. One company = one Jira/Linear instance. Multi-instance is V2.
4. Agent is installed voluntarily with developer awareness. No silent/covert install.
5. The product is sold top-down (EM buys, developers install). Not bottom-up.

