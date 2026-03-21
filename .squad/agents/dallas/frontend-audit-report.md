# Frontend Code Audit — AssistantAudit

**Date:** 2025-01-27  
**Auditor:** Dallas (Frontend Dev)  
**Tech Stack:** Next.js 16, React 19, TypeScript 5, Tailwind CSS v4, shadcn/ui

---

## Frontend Structure Map

### Directory Layout
```
frontend/src/
├── app/                    # Next.js App Router pages
│   ├── audits/            # Audit management pages
│   │   └── evaluation/    # Control assessment interface
│   ├── entreprises/       # Company management
│   ├── equipements/       # Equipment inventory
│   ├── frameworks/        # Framework library
│   ├── login/             # Authentication page
│   ├── outils/            # Tools suite (8 tools)
│   │   ├── ad-auditor/
│   │   ├── collecte/
│   │   ├── config-parser/
│   │   ├── monkey365/
│   │   ├── network-map/
│   │   ├── pingcastle/
│   │   ├── scanner/
│   │   └── ssl-checker/
│   ├── profile/
│   ├── sites/
│   ├── layout.tsx         # Root layout (fonts, metadata)
│   ├── page.tsx           # Dashboard
│   ├── providers.tsx      # Context providers wrapper
│   ├── error.tsx          # Error boundary
│   └── globals.css        # Tailwind + theme variables
├── components/
│   ├── ui/                # shadcn/ui components (26 components)
│   ├── evaluation/        # Assessment-specific components
│   ├── app-layout.tsx     # Authenticated app shell
│   ├── auth-guard.tsx     # Route protection
│   ├── skeletons.tsx      # Loading states
│   ├── theme-toggle.tsx   # Dark mode toggle
│   └── pingcastle-terminal.tsx
├── contexts/
│   └── auth-context.tsx   # Authentication state
├── hooks/
│   ├── use-api.ts         # SWR data fetching hooks
│   └── use-mobile.ts      # Responsive breakpoint hook
├── lib/
│   ├── api-client.ts      # Axios instance + JWT handling
│   ├── constants.ts       # UI constants (252 lines)
│   └── utils.ts           # Tailwind class merge utility
├── services/
│   └── api.ts             # API client methods (all endpoints)
└── types/
    ├── api.ts             # API response types (23KB)
    └── index.ts           # Re-exports
```

**Entry Points:**
- `app/layout.tsx` — Root layout with fonts (Geist Sans/Mono), providers
- `app/page.tsx` — Dashboard (landing after auth)
- `app/login/page.tsx` — Public login route

**Files:** 61 TypeScript files (63 total)

---

## Next.js Setup

### App Router Configuration

**next.config.ts:**
```typescript
distDir: process.env.NEXT_DIST_DIR || '.next'
```
- Minimal config, WSL-aware build cache path
- No custom webpack, no experimental features
- Standard App Router (RSC enabled)

**TypeScript Config:**
- **Strict mode:** ✅ `"strict": true`
- **Target:** ES2017
- **Module resolution:** bundler
- **Path aliases:** `@/*` → `./src/*`
- **JSX:** react-jsx (automatic runtime)

**Environment:**
- `NEXT_PUBLIC_API_URL` — Backend API base URL (default: `http://localhost:8000/api/v1`)

**Routes:**
- All pages under `app/` use file-based routing
- No `pages/` directory (pure App Router)
- Suspense boundaries in evaluation page for search params

---

## Component Structure

### Organization Pattern
- **UI primitives:** `components/ui/` (shadcn/ui)
- **Feature components:** `components/evaluation/`
- **Layout components:** `app-layout.tsx`, `auth-guard.tsx`
- **Page components:** Colocated in `app/[route]/page.tsx`

### Naming Conventions
- ✅ PascalCase for components
- ✅ kebab-case for file names
- ✅ Props interfaces inline or exported (not `Record<>` shortcuts)

### Existing Components

**shadcn/ui (26 components):**
- Layout: Card, Sidebar, Separator, Sheet, Tabs
- Forms: Input, Textarea, Label, Select, Checkbox, Switch, Form (react-hook-form)
- Feedback: Alert, AlertDialog, Dialog, Badge, Progress, Skeleton, Sonner (toast)
- Data: Table
- Overlays: Dropdown Menu, Tooltip
- Visuals: Avatar, Button, Chart

**Custom Components:**
- `app-layout.tsx` — Sidebar navigation, header with theme toggle
- `auth-guard.tsx` — Protected route wrapper
- `evaluation/attachment-section.tsx` — File upload/preview for assessments
- `pingcastle-terminal.tsx` — xterm.js integration for PingCastle
- `skeletons.tsx` — Loading state components
- `theme-toggle.tsx` — Dark mode switcher

**Component Patterns:**
- ✅ Client components marked with `"use client"`
- ✅ Server components by default (where possible)
- ✅ Props use TypeScript interfaces
- ⚠️ Forms mostly use controlled state (not react-hook-form except in UI lib)

---

## Routing Architecture

### App Router Structure

**Static Routes:**
- `/` — Dashboard
- `/login` — Login (public)
- `/profile` — User profile
- `/entreprises` — Companies list
- `/sites` — Sites list
- `/equipements` — Equipment inventory
- `/audits` — Audits list
- `/frameworks` — Framework library

**Dynamic Routes:**
- `/audits/evaluation?assessmentId=N` — Assessment detail (search params)

**Tools Suite (`/outils/`):**
- `/outils/scanner` — Network scanner (Nmap)
- `/outils/config-parser` — Config file parser
- `/outils/collecte` — SSH/WinRM data collection
- `/outils/ssl-checker` — SSL/TLS scanner
- `/outils/ad-auditor` — Active Directory auditor
- `/outils/network-map` — Network topology mapper
- `/outils/pingcastle` — PingCastle integration
- `/outils/monkey365` — Microsoft 365 auditor

**Layout Hierarchy:**
```
RootLayout (fonts, metadata)
  └─ Providers (theme, auth, tooltip, toaster)
       └─ AuthGuard (route protection)
            └─ AppLayout (sidebar, header) [authenticated only]
                 └─ Page content
```

**Protected Routes:** All routes except `/login` require authentication (handled by `AuthGuard`)

---

## TypeScript & Type Safety

### Strict Mode Coverage
- ✅ **TypeScript strict mode enabled**
- ✅ `noEmit: true` (Next.js handles compilation)
- ✅ `esModuleInterop: true`
- ✅ `isolatedModules: true` (required for Turbopack)

### Type Patterns
- **API types:** Comprehensive in `types/api.ts` (23KB, 800+ lines)
- **Interfaces for props:** ✅ Used consistently
- **Enums vs Union Types:** Union types with `as const` (e.g., `AuditStatus`)
- **Generic pagination:** `PaginatedResponse<T>`

### `any` Type Count
- **Total:** 5 occurrences (2 files)
- `app/page.tsx`: 2 uses in error handling (`catch (err: any)`)
- `app/outils/config-parser/page.tsx`: 3 uses in vendor matching logic

**Verdict:** ✅ Excellent type safety. Only 5 `any` uses, all in error handling or dynamic vendor matching.

### Type Safety Gaps
- ⚠️ Some API error responses use generic error handling without typed schemas
- ✅ All API response bodies are typed
- ✅ Form data structures have interfaces

---

## State Management

### Strategy: **React Hooks + Context API + SWR**

**Global State:**
- **AuthContext** (`contexts/auth-context.tsx`)
  - User object, login/logout, token refresh
  - Shared via `useAuth()` hook
  - Provider wraps entire app

**Server State (Data Fetching):**
- **SWR** (`hooks/use-api.ts`)
  - 8 hooks: `useEntreprises`, `useSites`, `useEquipements`, `useAudits`, `useFrameworks`, `useCampaigns`
  - Cache + revalidation
  - `revalidateOnFocus: false` (disabled automatic refetch)
  - Manual `mutate()` after updates

**Local State:**
- `useState` for form inputs, modals, pagination
- `useCallback` for event handlers (good memoization practice)
- `useMemo` for computed values (e.g., filtered lists)

**State Patterns:**
- ✅ Context for auth only (not overused)
- ✅ SWR for server data (proper cache invalidation)
- ✅ Local state for UI (modals, filters, search)
- ⚠️ Some pages use manual `useState + useEffect` instead of SWR (e.g., dashboard)

**No Redux, Zustand, or other state libraries** — intentional simplicity.

---

## Styling & Theme

### Tailwind CSS v4 Setup

**Config:** Inline `@theme` in `globals.css` (Tailwind v4 approach)
- **Base color:** Neutral (oklch color space)
- **CSS variables:** Yes (for shadcn/ui theming)
- **Prefix:** None
- **Plugins:** `tw-animate-css` (animation utilities)

**Theme System:**
- **Color Palette:** oklch format (modern, perceptually uniform)
- **Dark Mode:** ✅ Fully supported (class-based, `next-themes`)
  - `ThemeProvider` in `providers.tsx`
  - `ThemeToggle` component in header
  - Custom variant: `@custom-variant dark (&:is(.dark *))`
- **Radius:** Configurable via `--radius` (0.625rem base)
- **Fonts:**
  - Geist Sans (body): `--font-geist-sans`
  - Geist Mono (code): `--font-geist-mono`

**Custom Styles:**
- ✅ React Flow theme integration (minimap, controls match shadcn colors)
- ✅ Recharts axis/grid styling (fixes Turbopack CSS parser issues)
- ✅ Indeterminate progress animation

**Responsive Design:**
- ✅ `use-mobile.ts` hook for breakpoint detection
- ✅ Sidebar collapses on mobile
- ✅ Tables use horizontal scroll on small screens
- ⚠️ No explicit mobile-first media queries in custom components (relies on Tailwind defaults)

**Consistency:**
- ✅ `cn()` utility (`clsx` + `tailwind-merge`) used throughout
- ✅ Color constants in `lib/constants.ts` (no hardcoded Tailwind classes for status colors)

---

## shadcn/ui Integration

### Components in Use (26/50+)

**Installed:**
- alert, alert-dialog, avatar, badge, button, card, chart, checkbox, dialog, dropdown-menu, form, input, label, progress, select, separator, sheet, sidebar, skeleton, sonner, switch, table, tabs, textarea, tooltip

**Configuration:**
- **Style:** new-york
- **RSC:** ✅ Enabled
- **Base Color:** neutral
- **Icon Library:** lucide-react

### Customizations

**Color System:**
- ✅ All components use CSS variables
- ✅ Dark mode fully integrated
- ✅ Custom chart colors (5 variants)
- ✅ Sidebar color tokens (separate from card/background)

**Overrides:**
- React Flow controls/minimap styled to match shadcn theme
- Recharts selectors replaced with global CSS (Turbopack compatibility)

**Quality:** ✅ Excellent integration. No style conflicts, consistent theming, proper dark mode.

---

## API Client

### Backend Communication

**HTTP Client:** Axios (`lib/api-client.ts`)

**Base URL:** `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"`

**Configuration:**
```typescript
{
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000, // 30s
}
```

### Auth Header Handling

**Request Interceptor:**
```typescript
api.interceptors.request.use((config) => {
  const token = Cookies.get(TOKEN_KEY);
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```
- ✅ Auto-injects JWT from cookie
- ✅ Only if token exists

**Response Interceptor (401 handling):**
```typescript
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove(TOKEN_KEY);
      Cookies.remove(REFRESH_KEY);
      if (!window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
```
- ✅ Clears tokens on 401
- ✅ Redirects to login (except if already on login page)
- ⚠️ Hard redirect (not Next.js router) — causes full page reload

### Error Handling

**Pattern in API methods:**
```typescript
try {
  const { data } = await api.get<T>("/endpoint");
  return data;
} catch (error) {
  throw error; // Let caller handle
}
```
- ✅ Axios errors propagate to UI
- ✅ UI shows toast notifications (`sonner`)
- ⚠️ No centralized error shape normalization

**UI Error Display:**
- Toast notifications (sonner)
- Inline error messages in forms
- Error boundary (`app/error.tsx`) for unhandled errors

---

## Authentication Flow

### Login Flow

1. **User submits credentials** → `login/page.tsx`
2. **API call** → `authApi.login(username, password)`
   - POST `/auth/login` (form-urlencoded)
   - Returns `{ access_token, refresh_token }`
3. **Tokens stored** → `setTokens()` (js-cookie)
   - `aa_access_token` (15 min expiry)
   - `aa_refresh_token` (7 days)
   - `sameSite: "strict"`, `secure: true` (HTTPS only)
4. **Auth context refresh** → `authContext.refresh()`
   - Calls `/auth/me` to fetch user object
   - Stores in `AuthContext`
5. **AuthGuard redirect** → Navigates to `/`

### Token Storage

**Method:** `js-cookie` (client-side, not `httpOnly`)

**Security:**
- ✅ `sameSite: "strict"` (CSRF protection)
- ✅ `secure: true` (HTTPS only in production)
- ⚠️ Not `httpOnly` (client-side access needed for Authorization header)
- ⚠️ Tokens stored in plain text (standard for SPAs, but XSS-vulnerable)

**Token Expiry:**
- Access: 15 min (matches backend)
- Refresh: 7 days

### Token Refresh

**Status:** ❌ No automatic refresh implemented

**Current Behavior:**
- On 401, user is logged out and redirected to login
- No silent token refresh before expiry
- Refresh token stored but unused

**Recommendation:** Implement refresh logic in `api-client.ts` interceptor or `auth-context.tsx`.

### Protected Routes

**Implementation:** `auth-guard.tsx`

```typescript
const publicPaths = ["/login"];

useEffect(() => {
  if (!loading && !user && !isPublic) {
    router.replace("/login");
  }
  if (!loading && user && isPublic) {
    router.replace("/");
  }
}, [user, loading, isPublic, router]);
```

- ✅ Redirects unauthenticated users to `/login`
- ✅ Redirects authenticated users away from `/login`
- ✅ Shows loading spinner during auth check
- ✅ Wraps content with `AppLayout` for authenticated routes

---

## Form Handling

### Strategy: Controlled Components (Manual State)

**Pattern:**
```typescript
const [form, setForm] = useState<EntityCreate>({ /* fields */ });

const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  try {
    await api.create(form);
    toast.success("Created");
  } catch (err) {
    toast.error("Error");
  }
};

<Input value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })} />
```

**Libraries:**
- **react-hook-form:** ✅ Installed (v7.71.1)
- **zod:** ✅ Installed (v4.3.6)
- **@hookform/resolvers:** ✅ Installed (v5.2.2)
- ⚠️ **Not used** — Only `components/ui/form.tsx` has react-hook-form wrappers, but pages don't use them

### Validation

**Current:** ❌ No validation
- No Zod schemas defined
- No frontend validation (relies on backend errors)
- HTML5 validation (`required` attribute) only

### Error Handling

**Pattern:**
```typescript
try {
  await api.call();
} catch (err) {
  if (err && typeof err === "object" && "response" in err) {
    const axiosErr = err as { response?: { data?: { detail?: string } } };
    setError(axiosErr.response?.data?.detail || "Erreur");
  }
}
```

- ✅ Backend error messages displayed
- ⚠️ Error extraction is verbose and repeated
- ⚠️ No error normalization utility

### Accessibility

- ✅ Labels associated with inputs (`htmlFor` + `id`)
- ✅ `required` attribute for mandatory fields
- ✅ `autoComplete` attributes (username, current-password)
- ⚠️ No ARIA labels for error messages
- ⚠️ No focus management on validation errors

---

## UI Patterns

### Loading States

**Implementations:**
- ✅ Skeleton components (`skeletons.tsx`)
  - `DashboardSkeleton`, `TableSkeleton`, `CardSkeleton`
- ✅ Inline spinners: `<Loader2 className="animate-spin" />`
- ✅ Button loading state: `<Button disabled={loading}><Loader2 /> Text</Button>`
- ✅ Suspense boundaries in evaluation page

**Coverage:** ✅ Consistent across all pages

### Error States

**Implementations:**
- ✅ Error boundary: `app/error.tsx`
- ✅ Toast notifications: `sonner` (bottom-right, rich colors)
- ✅ Inline error messages in forms
- ⚠️ No error state components for failed data fetches (shows spinner indefinitely)

### Empty States

**Status:** ⚠️ Minimal implementation
- Some pages show "Aucun résultat" text
- No illustrated empty states
- No clear CTAs for empty lists

### Modals

**Implementation:** shadcn `Dialog`
- ✅ Used for CRUD operations (create, edit, delete confirmations)
- ✅ Proper focus trap, ESC to close
- ✅ Overlay backdrop

**Patterns:**
- Create/Edit forms in dialogs
- Delete confirmations in `AlertDialog`
- Detail views in `Sheet` (sidebar drawer)

### Notifications

**Library:** Sonner (shadcn/ui)
- ✅ Position: bottom-right
- ✅ Rich colors (success, error, info)
- ✅ Auto-dismiss
- ✅ Consistent usage across all pages

---

## Performance Assessment

### Bundle Size

**Status:** ⚠️ Not measured (no `next build` artifacts analyzed)

**Large Dependencies:**
- `@xyflow/react` (12.9.2) — Flow diagram library
- `recharts` (2.15.4) — Charts library
- `@xterm/xterm` (6.0.0) — Terminal emulator
- `axios` (1.13.5)

**Recommendations:**
- ✅ Dynamic imports for heavy tools (e.g., xterm.js in PingCastle)
- ⚠️ No code splitting for large libraries (recharts, react-flow)

### Lazy Loading

**Status:** ⚠️ Minimal
- ✅ Suspense in evaluation page (search params)
- ❌ No dynamic imports for routes
- ❌ No lazy loading of charts/flow diagrams

**Opportunities:**
- Lazy load React Flow (`@xyflow/react`) in network map
- Lazy load xterm.js (`@xterm/xterm`) in PingCastle terminal
- Lazy load recharts in dashboard

### Optimization Strategies

**Current:**
- ✅ SWR for data caching (reduces re-fetches)
- ✅ `useCallback` for event handlers
- ✅ `useMemo` for computed values
- ⚠️ `revalidateOnFocus: false` (disables smart revalidation)

**Missing:**
- ❌ Image optimization (no images in codebase)
- ❌ Font preloading (Next.js handles automatically for Geist)
- ❌ React.memo for expensive components
- ❌ Virtual scrolling for large tables

---

## Code Quality

### TypeScript Strictness

- ✅ **strict: true** — Full strict mode
- ✅ **any count:** 5 (excellent)
- ✅ **Type coverage:** 95%+ (estimate)

### Code Consistency

**Formatting:**
- ✅ Consistent indentation (2 spaces)
- ✅ Semicolons used
- ✅ Double quotes for strings
- ⚠️ No Prettier config file (manual formatting)

**Naming:**
- ✅ PascalCase for components
- ✅ camelCase for functions/variables
- ✅ UPPER_SNAKE_CASE for constants
- ✅ kebab-case for file names

**Component Patterns:**
- ✅ Consistent prop destructuring
- ✅ `"use client"` directive where needed
- ✅ TypeScript interfaces for props

### Comments

**Status:** ⚠️ Minimal
- ✅ Section headers in large files (`// ── Auth ──`)
- ⚠️ No JSDoc comments
- ⚠️ No prop documentation
- ✅ Inline comments for complex logic (e.g., token refresh logic)

### Linting

**Config:** `eslint.config.mjs`
- ✅ `eslint-config-next` (core-web-vitals + TypeScript)
- ✅ No custom rules
- ⚠️ No reported lint errors (not run during audit)

**Missing:**
- ❌ No Prettier
- ❌ No Husky pre-commit hooks
- ❌ No lint-staged

### Console Logs

**Count:** 10 occurrences (9 files)
- ✅ Mostly in error handlers (`console.error`)
- ⚠️ Some debug logs in outils pages
- ⚠️ Should be removed or replaced with proper logging

---

## Issues & Pain Points

### Bugs

1. **401 handling uses hard redirect** (`window.location.href = "/login"`)
   - Causes full page reload
   - Loses client-side state
   - Fix: Use Next.js `router.push()` or `router.replace()`

2. **No token refresh** — Users logged out after 15 minutes
   - Refresh token stored but unused
   - Fix: Implement silent refresh in API client or auth context

3. **SWR revalidation disabled** (`revalidateOnFocus: false`)
   - Data becomes stale when switching tabs
   - Fix: Enable or use `revalidateOnMount` conditionally

### UX Gaps

1. **No illustrated empty states** — Lists show plain text "Aucun résultat"
2. **No error state components** — Failed fetches show spinner indefinitely
3. **No loading state for data mutations** — Create/update buttons don't disable during save
4. **No optimistic updates** — UI waits for API response before updating

### Performance Issues

1. **No lazy loading** — Heavy libraries (React Flow, xterm.js, recharts) load on initial bundle
2. **No virtualization** — Large tables (e.g., equipements) load all rows
3. **SWR cache never invalidated** — Manual `mutate()` required after CRUD operations

### Code Smell

1. **react-hook-form unused** — Installed but not used, manual form state everywhere
2. **Zod unused** — No validation schemas
3. **Repeated error handling** — Axios error extraction duplicated across pages
4. **Hard-coded API error parsing** — No centralized error normalization
5. **Console logs** — 10 occurrences should be cleaned up

---

## Frontend Readiness for Features

### ✅ Production-Ready

- **Authentication flow** — Login, logout, route protection
- **CRUD pages** — Entreprises, sites, equipements, audits, frameworks
- **Dashboard** — Stats, charts, recent audits
- **Assessment interface** — Control evaluation, attachments, scoring
- **Tools suite** — 8 tools (scanner, config parser, AD audit, etc.)
- **Dark mode** — Fully functional
- **Responsive design** — Sidebar collapses, tables scroll

### ⚠️ Needs Polish

- **Form validation** — Add Zod schemas + react-hook-form
- **Error handling** — Centralize error normalization
- **Token refresh** — Implement silent refresh
- **Empty states** — Add illustrations and CTAs
- **Loading states** — Improve failed fetch handling
- **Performance** — Lazy load heavy libraries

### 🚧 Not Implemented

- **User management** — No admin pages for user CRUD
- **Role-based UI** — No conditional rendering based on user role
- **Audit/campaign workflow** — No campaign creation wizard
- **Bulk operations** — No multi-select for equipements/audits
- **Export features** — No CSV/PDF export buttons
- **Internationalization** — Hardcoded French strings (no i18n)

### Blockers

None. Frontend is functional and deployable.

### Quick Wins

1. **Add Zod validation** — 30 min per form
2. **Implement token refresh** — 1 hour
3. **Fix 401 redirect** — 5 min
4. **Remove console logs** — 10 min
5. **Add error normalization utility** — 20 min
6. **Enable SWR revalidation** — 5 min
7. **Lazy load React Flow** — 15 min
8. **Add empty state illustrations** — 2 hours (design + implementation)

---

## Summary

**Overall Grade:** ✨ **A-** (Excellent foundation, needs polish)

### Strengths

- ✅ Excellent TypeScript coverage (strict mode, only 5 `any` uses)
- ✅ Clean architecture (App Router, proper separation of concerns)
- ✅ Consistent shadcn/ui integration + dark mode
- ✅ Comprehensive API types (23KB of interfaces)
- ✅ SWR for data caching
- ✅ Proper auth flow and route protection
- ✅ Modern tech stack (Next.js 16, React 19, Tailwind v4)

### Weaknesses

- ⚠️ Form validation not implemented (Zod + react-hook-form unused)
- ⚠️ No token refresh (users logged out after 15 min)
- ⚠️ Performance: heavy libraries not lazy loaded
- ⚠️ UX: minimal empty/error states
- ⚠️ Error handling: repetitive Axios error parsing

### Verdict

Frontend is **production-ready** for core features but needs **polish** for enterprise-grade UX. The codebase is clean, well-typed, and maintainable. Priority improvements: token refresh, form validation, and lazy loading.

---

**Next Steps:**
1. Implement token refresh mechanism
2. Add Zod validation to forms
3. Lazy load React Flow and xterm.js
4. Improve empty/error states
5. Centralize error handling
