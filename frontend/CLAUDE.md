# Frontend — Conventions & Architecture

**Path:** `E:\AssistantAudit\frontend\`
**Stack:** Next.js 16, React 19, TypeScript, Tailwind v4, shadcn/ui, SWR, Axios, Zod, react-hook-form

## STRUCTURE

```
frontend/src/
├── app/                 Next.js App Router — pages and layouts
│   ├── layout.tsx       Root layout: AuthProvider + ThemeProvider + AppLayout
│   ├── providers.tsx    Client providers wrapper
│   ├── login/           Unauthenticated entry point
│   ├── outils/          Tool pages (monkey365, pingcastle, collecte, scanner, ...)
│   ├── audits/          Audit + campaign management
│   ├── entreprises/     Company management
│   ├── sites/           Physical site inventory
│   ├── equipements/     Equipment list
│   └── frameworks/      Compliance framework viewer
├── components/
│   ├── ui/              shadcn/ui primitives — DO NOT EDIT directly
│   ├── app-layout.tsx   Sidebar navigation + header
│   ├── auth-guard.tsx   Redirects unauthenticated users to /login
│   └── ...              Custom components
├── contexts/
│   └── auth-context.tsx AuthContext: user state, login(), logout(), refresh()
├── hooks/
│   ├── use-api.ts       Generic SWR-based data fetching hook
│   └── use-mobile.ts    Responsive breakpoint hook
├── lib/
│   ├── api-client.ts    Axios instance + JWT interceptors + cookie helpers
│   ├── constants.ts     App-wide constants
│   └── utils.ts         cn() utility (clsx + tailwind-merge)
├── services/
│   └── api.ts           All API call functions grouped by resource
└── types/
    ├── api.ts           TypeScript interfaces for all backend response types
    └── index.ts         Re-exports
```

## PAGE CONVENTIONS

All pages are in `app/{route}/page.tsx`. All pages are `"use client"` components (no RSC data fetching in use). Add `"use client"` at the top of every page and interactive component.

New page checklist:
1. Create `app/{route}/page.tsx` with `"use client"`
2. Add types to `types/api.ts` for any new backend response shapes
3. Add API functions to `services/api.ts`
4. Auth is enforced at layout level via `AuthGuard` — no need to add per-page

## DATA FETCHING PATTERNS

**Pattern 1 — SWR (preferred for read data):**
```typescript
import useSWR from "swr";
import api from "@/lib/api-client";

const { data, error, isLoading, mutate } = useSWR(
  `/entreprises/${id}`,
  (url) => api.get(url).then(r => r.data)
);
```

**Pattern 2 — Direct async (mutations and tool triggers):**
```typescript
const [loading, setLoading] = useState(false);
const handleAction = async () => {
  setLoading(true);
  try {
    await toolsApi.launchMonkey365Scan(payload);
    toast.success("Scan lancé");
  } catch (err) {
    toast.error("Erreur lors du lancement");
  } finally {
    setLoading(false);
  }
};
```

Use `sonner` (`import { toast } from "sonner"`) for all user-facing notifications.

## API CLIENT

`lib/api-client.ts` — Axios instance pre-configured with:
- `baseURL`: `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"`
- `timeout`: 30 seconds
- Request interceptor: attaches `Authorization: Bearer <token>` from cookies
- Response interceptor: on 401, clears tokens and redirects to `/login`

Tokens stored via `js-cookie` with `sameSite: strict`.

## ADDING API CALLS

1. Add TypeScript interfaces to `types/api.ts`
2. Add the function to the appropriate group in `services/api.ts`:

```typescript
export const myResourceApi = {
  async list(): Promise<MyResource[]> {
    const { data } = await api.get("/my-resource");
    return data;
  },
  async create(payload: MyResourceCreate): Promise<MyResource> {
    const { data } = await api.post("/my-resource", payload);
    return data;
  },
};
```

## AUTH FLOW

1. `AuthProvider` wraps the entire app
2. On mount, calls `authApi.me()` if a token cookie exists; populates `user` state
3. `AuthGuard` in layout checks `useAuth().user` and redirects to `/login` if null
4. `useAuth()` exposes `{ user, loading, login, logout, refresh }`
5. `logout()` clears cookies and redirects via `window.location.href`

## COMPONENT RULES

- `components/ui/` — shadcn/ui primitives. **Do NOT edit these files.** Regenerated via `npx shadcn add <component>`
- `components/` root — custom components
- Use `cn()` from `lib/utils.ts` for conditional class merging (clsx + tailwind-merge)
- Use path alias `@/` for all imports within `src/`

## STATE MANAGEMENT

- **Server state**: SWR (`useSWR`) — list data, detail data, paginated resources
- **Auth/global state**: React Context (`auth-context.tsx`)
- **Form state**: `react-hook-form` + `zod` validation
- **Local UI state**: `useState` within the component
- Do NOT add Redux, Zustand, or new context providers without discussion

## POLLING PATTERN (long-running jobs)

```typescript
// Poll until status changes — clean up on unmount or status change
useEffect(() => {
  if (!selectedScan || selectedScan.status !== "running") return;
  const interval = setInterval(async () => {
    const updated = await toolsApi.getScanDetail(selectedScan.id);
    setSelectedScan(updated);
    if (updated.status !== "running") {
      clearInterval(interval);
    }
  }, 2000);
  return () => clearInterval(interval);
}, [selectedScan?.id, selectedScan?.status]);  // depend on id + status, NOT the full object
```

## TYPE CONVENTIONS

- All API response shapes are in `types/api.ts` (use `interface` for objects, not `type`)
- Do NOT use `any` — use `unknown`, `Record<string, unknown>`, or specific types
- Do NOT use `@ts-ignore` — fix the underlying type issue
- `null` = backend's empty value; `undefined` = TypeScript optional

## LANGUAGE

- **UI text, labels, button text, error messages, toasts:** French
- **Code, variables, function names, comments:** English

## RUNNING

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
npm run build    # production build (fails on TypeScript errors)
npm run lint     # ESLint with eslint-config-next
```

## KNOWN ISSUES

- No test suite (jest/vitest/playwright not configured)
- `network-map/page.tsx` is ~2,900 lines — needs extraction into sub-components
- Some `catch` blocks only call `console.error` without user-visible feedback
- 7 npm high-severity audit vulnerabilities reported (unresolved as of Sprint 0)
