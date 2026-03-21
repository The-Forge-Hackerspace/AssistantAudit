# Dallas — Session History

## Plugin Installations

- 📦 Plugin `frontend-web-dev` installed from `github/awesome-copilot` (2026-03-21) — skills: `playwright-explore-website`, `playwright-generate-test`; agent template: `expert-react-frontend-engineer`

## Project Knowledge

- AssistantAudit UI displays security audit findings and framework assessments
- Users select frameworks, run audits, review findings
- Dashboard: findings overview, compliance status, remediation actions
- Auth flow: login → JWT token storage → authenticated API calls

## Patterns

(To be filled as work progresses)

## Key Files

- App layout: `frontend/app/layout.tsx`
- Pages: `frontend/app/` (audit, dashboard, framework-selector, etc.)
- Components: `frontend/app/components/`
- Styles: Tailwind config `frontend/tailwind.config.ts`
- API client: `frontend/lib/api.ts` (or similar)

## Learnings

### Monkey365 UI Component Structure
- Page located at `frontend/src/app/outils/monkey365/page.tsx`
- Three tabs: Launch scan, History, Details
- History tab displays scan list with filtering by entreprise_id
- Details tab shows full scan results with configuration snapshot
- Scan deletion uses backend DELETE endpoint `/tools/monkey365/scans/{result_id}`
- Authentication mode (MSAL interactive desktop) is stored in `force_msal_desktop` boolean field

### Monkey365 Data Model
- `Monkey365ScanResultSummary` - minimal fields for list views (id, status, scan_id, findings_count, timestamps)
- `Monkey365ScanResultDetail` - extends summary with: auth_mode, force_msal_desktop, powershell_config, config_snapshot, output_path, error_message
- Backend returns full scan details including PowerShell parameters used and auth configuration
- Archiving path removed from UI (was `/data/enterprise/Cloud/M365/{GUID}`)

### Component Library Structure
- shadcn/ui components live in `components/ui/` (26 installed)
- Feature-specific components in subdirectories (e.g., `evaluation/`)
- Layout components at root: `app-layout.tsx`, `auth-guard.tsx`
- All UI primitives use CSS variables for theming (dark mode ready)

### Routing Patterns
- Pure App Router (no `pages/` directory)
- Nested routes under `app/[route]/page.tsx`
- Dynamic routes use search params (`?assessmentId=N`) not file-based `[id]`
- Protected routes handled by `AuthGuard` wrapper in providers
- Layout hierarchy: RootLayout → Providers → AuthGuard → AppLayout → Page

### API Integration Approach
- Axios client in `lib/api-client.ts` with request/response interceptors
- JWT auto-injected via request interceptor (reads from js-cookie)
- 401 errors trigger logout + redirect in response interceptor
- API methods in `services/api.ts` (one file, 800+ lines, all endpoints)
- SWR hooks in `hooks/use-api.ts` for data caching (8 hooks)
- Manual `mutate()` after CRUD operations (no automatic invalidation)

### State Management Strategy
- **Auth:** Context API (`AuthContext`) for user object + login/logout
- **Server data:** SWR for lists/entities (cache + revalidation)
- **Local UI:** `useState` for forms, modals, filters
- No Redux/Zustand (intentionally simple)
- `useCallback` for handlers, `useMemo` for computed values

### TypeScript Patterns
- Strict mode enabled, only 5 `any` uses (all in error handling)
- API types in `types/api.ts` (23KB, comprehensive)
- Generic pagination: `PaginatedResponse<T>`
- Union types with `as const` (e.g., `AuditStatus`)
- Props use interfaces (not `Record<>` shortcuts)

### Styling Conventions
- Tailwind CSS v4 with inline `@theme` config
- oklch color space for theme variables
- Dark mode via `next-themes` (class-based)
- `cn()` utility for conditional classes (`clsx` + `tailwind-merge`)
- Status colors in `lib/constants.ts` (no hardcoded Tailwind classes)

### Form Handling Pattern
- Controlled components with `useState` (manual state)
- react-hook-form + Zod installed but **unused**
- No frontend validation (relies on backend errors)
- Error extraction from Axios errors (verbose, repeated)

### Pain Points Identified
1. **No token refresh** — Users logged out after 15 min
2. **401 redirect uses `window.location.href`** — causes full reload
3. **Heavy libraries not lazy loaded** — React Flow, xterm.js, recharts
4. **SWR revalidation disabled** — data becomes stale
5. **No form validation** — Zod schemas not defined
6. **Repeated error handling** — no centralized error normalization

## Work Completed: Monkey365 Audit Interface UI/UX Fixes

### Issue 1: Scan Deletion Button (FIXED)
- **Problem:** History view had no working delete button for removing old scans
- **Solution:**
  - Added `deleteMonkey365Scan()` API method to `services/api.ts` calling DELETE `/tools/monkey365/scans/{resultId}`
  - Added state `deleting` to track deletion in progress
  - Added `handleDeleteScan()` function with confirmation dialog
  - Added delete button (X icon) to history table with red styling
  - Added delete button to Details card header
  - Both buttons properly handle click propagation and disable during deletion
- **Files Modified:**
  - `frontend/src/services/api.ts` - Added API method
  - `frontend/src/app/outils/monkey365/page.tsx` - Added UI and handlers

### Issue 2: Missing ForceMSALDesktop Display (FIXED)
- **Problem:** PowerShell overview didn't show `ForceMSALDesktop = $true` setting
- **Solution:**
  - Added `ForceMSALDesktop = $true` to PowerShell preview in launch tab (line 198)
  - Added ForceMSALDesktop to "Fixed Parameters" info box (line 371)
  - Added auth_mode and force_msal_desktop fields to Details view (lines 529-544)
  - Display shows "✓ Activé" or "✗ Désactivé" with green/gray colors
- **Files Modified:**
  - `frontend/src/app/outils/monkey365/page.tsx` - Updated PowerShell preview and details display
  - `frontend/src/types/api.ts` - Added missing fields to `Monkey365ScanResultDetail` type

### Issue 3: Misleading Automatic Archiving Message (FIXED)
- **Problem:** UI displayed stale message about automatic archiving to `/data/enterprise/Cloud/M365/{GUID}`
- **Solution:**
  - Removed the archiving path reference from the Alert message
  - Simplified message to: "Mode simplifié : INTERACTIVE auth (navigateur), collecte des 5 modules M365 standard, export JSON + HTML."
  - Message now accurately reflects actual scan behavior without referencing outdated archiving
- **Files Modified:**
  - `frontend/src/app/outils/monkey365/page.tsx` - Updated Alert component (lines 274-280)

### TypeScript Type Updates
- Extended `Monkey365ScanResultDetail` interface with:
  - `auth_mode?: string | null` - Authentication method used (e.g., "interactive")
  - `force_msal_desktop?: boolean` - Whether MSAL interactive desktop auth was enabled
  - `powershell_config?: Record<string, unknown> | null` - Full PowerShell parameters
- File: `frontend/src/types/api.ts`

### Build Verification
- Next.js build completed successfully (5.6s compile, 636.2ms page generation)
- All 21 routes compiled without errors
- No TypeScript errors after type updates
