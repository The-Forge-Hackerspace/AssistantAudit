## Learnings

Project started 2026-03-19.

**Project:** AssistantAudit — Open-source IT infrastructure security auditing tool for pentesters and IT auditors.

**Scope:** Firewalls, Switches, Active Directory, Microsoft 365, Linux/Windows servers, network mapping with VLAN visualization.

**Tech Stack:**
- Backend: Python 3.13 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + JWT OAuth2
- Database: SQLite (dev) → PostgreSQL (prod) — Alembic migrations
- Frontend: Next.js 16 (App Router) + React + TypeScript + Tailwind CSS v4 + shadcn/ui
- Auth: JWT cookies + Axios interceptor + AuthGuard
- Frameworks: 12 dynamic YAML files, SHA-256 synced at startup
- Storage: data/{entreprise_slug}/{category}/{tool}/{scan_id}/

**Current State:**
✅ Phase 1 — Backend foundation (45 endpoints, 8 models, JWT auth)
✅ Phase 2 — 12 YAML frameworks with SHA-256 sync engine
✅ Phase 3 — Full React UI (dashboard, CRUD, assessments, dark mode)
🔄 Phase 4 — Tool integrations (IN PROGRESS)
⏳ Phase 5 — PDF/Word report generation
⏳ Phase 6 — AI-assisted remediation suggestions

**Owner:** T0SAGA97
**GitHub:** https://github.com/The-Forge-Hackerspace/AssistantAudit

---

### 2026-03-19 — Monkey365 Dynamic Authentication Form

**Task:** Implemented dynamic authentication form for Monkey365 that adapts to selected auth_mode.

**Implementation:**
- Added `Monkey365AuthMode` type to TypeScript API types ("interactive" | "device_code" | "ropc" | "client_credentials")
- Updated `Monkey365Config` interface to support new auth_mode field and optional username/password fields
- Modified Monkey365 page.tsx to render credential fields conditionally based on auth_mode selection
- Implemented visual badges for auth modes: 🟢 green for safest modes (interactive, device_code), 🟡 yellow for credential-based modes
- Added informative alerts for interactive (browser window) and device_code (device code flow) modes
- Updated PowerShell preview generator to display correct authentication parameters per mode
- Modified form validation to enforce required fields based on selected auth_mode

**Key UI Features:**
- Auth mode dropdown selector with visual badges indicating security level
- Dynamic form fields that appear/hide based on selection:
  - Interactive: No credentials required
  - Device Code: No credentials required
  - ROPC: TenantId + Username + Password
  - Client Credentials: TenantId + ClientId + ClientSecret
- Info badges explaining what each auth mode does
- Form validation tailored to each auth mode

**Pattern:** Dynamic form rendering based on enum selection with conditional validation.

---

### 2026-03-19 — Real-Time Scan Logs Panel for Monkey365

**Task:** Added live log panel to Monkey365 page showing real-time scan progress with polling and duration tracking.

**Implementation:**
- Added `elapsedSeconds` state to track scan duration in real-time
- Implemented polling hook: fetches scan status every 2 seconds while scan is RUNNING, auto-stops when complete
- Implemented ticker hook: increments elapsed time every second for running scans
- Enhanced `loadScanDetail` to initialize elapsed time from `created_at` timestamp or `duration_seconds`
- Replaced basic detail view with enhanced `ScanLogsPanel` component

**UI Features:**
- **Visual Status Indicators:**
  - RUNNING: Animated blue spinner + blue border + "En cours" badge
  - SUCCESS: Green checkmark + green border + "Succès" badge
  - FAILED: Red X + red border + "Échec" badge
- **Live Duration Display:** Shows elapsed time in human-readable format (e.g., "2min 15s"), updates every second
- **Timeline Events:**
  - ✅ Script generated (timestamp)
  - ✅ PowerShell launched (timestamp)
  - 📄 Output path (when available)
  - 🔄 Scan in progress (while running)
  - ✅ Scan completed with findings count (on success)
  - ❌ Scan failed with timestamp (on failure)
- **Error Alerts:** Red destructive alert showing error_message when scan fails
- **Configuration Snapshot:** JSON view of scan config in collapsible section

**Helper Functions Added:**
- `formatElapsedTime(seconds)`: Formats duration as "Xmin Ys" for live display
- `formatTimestamp(dateStr)`: Formats date as HH:MM:SS for timeline events
- Updated `formatDuration` to use "min" instead of "m" for consistency

**Pattern:** Real-time data polling with dual useEffect hooks (status poller + duration ticker) for live UX feedback during long-running operations.
