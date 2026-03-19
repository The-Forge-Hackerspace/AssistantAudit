# Work Routing

How to decide who handles what.

## Routing Table

| Work Type | Route To | Examples |
|-----------|----------|----------|
| **Governance & Scope** | Keaton (PO) | Feature priorities, scope changes, deliverable validation, business alignment |
| **Sprint Coordination** | Verbal (SM) | Task routing, DoD enforcement, conflict resolution, blocker escalation |
| **Backend API/Services** | Fenster | API endpoints in backend/app/api/v1/, business logic in backend/app/services/ |
| **Backend Architecture** | Hockney | Data model design, API patterns, architectural review, breaking changes |
| **Backend Testing** | McManus | pytest tests, fixtures, mocks, backend test coverage |
| **Tool Integration** | Redfoot | backend/app/tools/ ONLY — Monkey365, ORADAD, PingCastle, Nmap bridges |
| **Database** | Kobayashi | Alembic migrations, SQLAlchemy queries, data model optimization |
| **Frontend Implementation** | Keaton-Jr | React pages, components in frontend/src/app/, API integration |
| **Frontend Architecture** | Arturro | Component structure, state management, routing patterns |
| **Frontend Testing** | Strausz | Jest/React Testing Library tests, UI validation |
| **UX Design** | Rabin | Wireframes, UX flows, interaction patterns (approval required before frontend implementation) |
| **Documentation** | Baer | CONCEPT.md, API.md, ARCHITECTURE.md, GitHub releases, version management |
| **Infrastructure** | Fortier | Docker, docker-compose, .env.example, deployment configuration |
| **Security Review** | Kujan | Auth code, file I/O, subprocess calls, external tools (AUTO-TRIGGERED) |
| **CI/CD & Security Automation** | Renault | GitHub Actions, pip/npm audit, SAST, secret scanning, Docker security |
| **Session logging** | Scribe | Automatic — never needs routing |
| **Work monitoring** | Ralph | "Ralph, go" → continuous work scanning until board is clear |

## Issue Routing

| Label | Action | Who |
|-------|--------|-----|
| `squad` | Triage: analyze issue, assign `squad:{member}` label | Verbal (SM) |
| `squad:{member}` | Pick up issue and complete the work | Named member |

### How Issue Assignment Works

1. When a GitHub issue gets the `squad` label, **Verbal (Scrum Master)** triages it — analyzing content, assigning the right `squad:{member}` label based on domain routing, and commenting with triage notes.
2. When a `squad:{member}` label is applied, that member picks up the issue in their next session.
3. Members can reassign by removing their label and adding another member's label (with SM approval).
4. The `squad` label is the "inbox" — untriaged issues waiting for Scrum Master routing.

## Rules

1. **Eager by default** — spawn all agents who could usefully start work, including anticipatory downstream work.
2. **Scribe always runs** after substantial work, always as `mode: "background"`. Never blocks.
3. **Quick facts → coordinator answers directly.** Don't spawn an agent for "what port does the server run on?"
4. **When two agents could handle it**, pick the one whose domain is the primary concern.
5. **"Team, ..." → fan-out.** Spawn all relevant agents in parallel as `mode: "background"`.
6. **Anticipate downstream work.** If a feature is being built, spawn the tester to write test cases from requirements simultaneously.
7. **Issue-labeled work** — when a `squad:{member}` label is applied to an issue, route to that member. Verbal handles all `squad` (base label) triage.
8. **Communication chain enforced** — All agents → Verbal → Keaton. No agent makes structural/security/architectural decisions without routing through this chain.
9. **Auto-triggered reviews** — Kujan (Security Auditor) is AUTOMATICALLY spawned when code touches: auth, file I/O, subprocess, external tools, or dependencies.
10. **Definition of Done enforced** — Verbal blocks any task from "done" status until all 7 DoD criteria are met.
