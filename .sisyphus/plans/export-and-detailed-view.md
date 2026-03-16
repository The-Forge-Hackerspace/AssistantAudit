# Diagram Export & Detailed Equipment View with Port-Level Mapping

## TL;DR

> **Quick Summary**: Add PNG/SVG export to both network diagram tabs, and create a new "Vue détaillée" tab showing equipment with per-port visual rendering and port-to-port connections.
> 
> **Deliverables**:
> - Export PNG/SVG buttons on site topology and multi-site overview toolbars
> - Port configuration editor in equipment create/edit flow (manual definition with presets)
> - New "Vue détaillée" tab with `DetailedEquipmentNode` custom nodes showing physical port grids
> - Port-to-port edge connections using React Flow handle IDs
> - Updated link dialog with optional port picker
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES — 4 waves
> **Critical Path**: T1 (install dep) → T3 (export util) → T4/T5 (export buttons) | T6 (TS types) → T8 (port editor) → T10 (detailed node) → T11 (detailed tab) → T13 (port picker in link dialog)

---

## Context

### Original Request
User wants two new features for the network cartography tool:
1. Export diagrams as PNG and SVG for client deliverables
2. A detailed view showing equipment with physical port layouts (e.g., 24× GigE + 4× SFP+), with port-to-port connections visible

### Interview Summary
**Key Discussions**:
- **Export formats**: PNG + SVG only (no PDF) — user confirmed
- **Export library**: `html-to-image@1.11.11` (version-locked; later versions broken per React Flow team)
- **Detailed view location**: New 3rd tab "Vue détaillée" alongside "Topologie site" and "Vue multi-site"
- **Port data source**: Manual only — ports defined via port editor UI, not auto-populated from parser
- **Port linking**: Optional — user CAN pick ports but links also work without port assignments (backward compatible)
- **Detailed view scope**: All equipment for the selected site at once (not select-to-detail)
- **Port presets**: Quick-add buttons for common configs (e.g., "24× GigE + 4× SFP+")

**Research Findings**:
- `ports_status` JSON field exists on `EquipementReseau` (backend model line 126), currently unused — will repurpose for port config
- Frontend type mismatch: `ports_status` typed as `string | null` (line 157) but backend returns `dict`
- Backend Pydantic schemas already accept `ports_status: Optional[dict]` in create/update
- `_TYPE_FIELDS` mapping (backend `equipements.py:35-44`) already includes `ports_status` for network types (reseau, switch, router, access_point)
- `NetworkLink` model has `source_interface` and `target_interface` string fields (line 31-32) — will store port IDs
- React Flow supports multiple handles per node with unique `id` prop; edges target `sourceHandle`/`targetHandle`
- `useUpdateNodeInternals()` needed if handle count changes dynamically
- Two separate ReactFlow instances exist (site topology line 848, overview line 882) — both need export
- Page is currently 1274 lines; `DeviceNode` at line 233, `ParallelEdge` at line 255
- No `html-to-image` library currently installed

### Metis Review
**Identified Gaps** (addressed):
- **Port data source ambiguity** → Resolved: manual only (user decision)
- **Port linking enforcement** → Resolved: optional (user decision)
- **Detailed view scope** → Resolved: all site equipment (user decision)
- **STI subtypes without ports_status** → Only `EquipementReseau` (and its subtypes: switch, router, access_point) have `ports_status` column. Other types (serveur, firewall, etc.) do NOT — plan must handle this gracefully in the port editor (disable for non-network types)

---

## Work Objectives

### Core Objective
Enable network diagram export as PNG/SVG images, and add a port-level detailed equipment view that renders physical port grids with port-to-port connections.

### Concrete Deliverables
- `html-to-image@1.11.11` installed as dependency
- "Export PNG" / "Export SVG" buttons in site topology toolbar (lines 825-844)
- "Export PNG" / "Export SVG" buttons in multi-site overview toolbar (lines 871-878)
- `PortDefinition` TypeScript type and `ports_status` type fix (`string | null` → `PortDefinition[] | null`)
- Port configuration editor component (with presets) integrated in equipment forms
- `DetailedEquipmentNode` custom React Flow node component with per-port `<Handle>` elements
- "Vue détaillée" as 3rd tab with its own ReactFlow instance
- Link dialog updated with optional port picker dropdowns
- All existing features continue working (backward compatible)

### Definition of Done
- [ ] `tsc --noEmit` returns 0 errors
- [ ] Export PNG produces a downloadable `.png` file of the site diagram
- [ ] Export SVG produces a downloadable `.svg` file
- [ ] Equipment ports can be created/edited via port editor
- [ ] Detailed view tab renders equipment with port grids
- [ ] Links between ports render correctly in detailed view
- [ ] Existing links without ports still display normally

### Must Have
- Version-locked `html-to-image@1.11.11` (NOT latest)
- Export captures FULL diagram (not just viewport) using `getNodesBounds()` + `getViewportForBounds()`
- Port editor has quick-add presets (e.g., "24× GigE + 4× SFP+", "48× GigE + 4× SFP+")
- Detailed view shows ALL equipment for the selected site
- Port selection is OPTIONAL when creating/editing links
- Labels in French (matching existing UI language)

### Must NOT Have (Guardrails)
- NO PDF export (explicitly excluded by user)
- NO auto-population of ports from config parser (user chose manual only)
- NO mandatory port selection on link creation (backward compatible)
- NO port templates / shared port definitions (per-instance only)
- NO changes to existing link behavior in site topology or overview tabs
- NO `html-to-image` version other than `1.11.11`
- NO excessive comments, over-abstraction, or AI-slop patterns
- NO touching equipment types that don't have `ports_status` column (only reseau, switch, router, access_point subtypes support ports)

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO (no test framework in project)
- **Automated tests**: NO
- **Framework**: None
- **Agent QA**: Playwright for UI verification, `tsc --noEmit` for type safety, `py_compile` for backend

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Frontend/UI**: Use Playwright — navigate, interact, assert DOM, screenshot
- **Backend**: Use `py_compile` — verify syntax
- **Type Safety**: Use `tsc --noEmit` — verify zero errors
- **Export**: Use Playwright — trigger export, verify download

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — dependency + types + foundation):
├── Task 1: Install html-to-image@1.11.11 [quick]
├── Task 2: Fix ports_status TS type + add PortDefinition type [quick]
└── Task 3: Create export utility functions [quick]

Wave 2 (After Wave 1 — export buttons + port editor + detailed node):
├── Task 4: Add export buttons to site topology toolbar [quick]
├── Task 5: Add export buttons to multi-site overview toolbar [quick]
├── Task 6: Port configuration editor component [visual-engineering]
├── Task 7: DetailedEquipmentNode custom React Flow node [visual-engineering]
└── Task 8: Port presets (quick-add buttons) [quick]

Wave 3 (After Wave 2 — detailed view tab + link dialog update):
├── Task 9: Add "Vue détaillée" tab with ReactFlow instance [unspecified-high]
├── Task 10: Update link dialog with optional port picker [unspecified-high]
└── Task 11: Data loading for detailed view (ports + edges) [unspecified-high]

Wave 4 (After Wave 3 — integration + type-check):
├── Task 12: Integration: port-to-port edges in detailed view [deep]
└── Task 13: Final tsc --noEmit + visual QA [unspecified-high]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality review [unspecified-high]
├── Task F3: Real manual QA with Playwright [unspecified-high]
└── Task F4: Scope fidelity check [deep]

Critical Path: T1 → T3 → T4 | T2 → T7 → T9 → T12 → T13 → FINAL
Parallel Speedup: ~55% faster than sequential
Max Concurrent: 5 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| T1 | — | T3, T4, T5 | 1 |
| T2 | — | T6, T7, T8, T10 | 1 |
| T3 | T1 | T4, T5 | 1 |
| T4 | T3 | T13 | 2 |
| T5 | T3 | T13 | 2 |
| T6 | T2 | T9, T11 | 2 |
| T7 | T2 | T9, T12 | 2 |
| T8 | T2 | T6 | 2 |
| T9 | T6, T7 | T11, T12 | 3 |
| T10 | T2 | T12 | 3 |
| T11 | T6, T9 | T12 | 3 |
| T12 | T7, T9, T10, T11 | T13 | 4 |
| T13 | T4, T5, T12 | FINAL | 4 |
| F1-F4 | T13 | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 → `quick`, T2 → `quick`, T3 → `quick`
- **Wave 2**: 5 tasks — T4 → `quick`, T5 → `quick`, T6 → `visual-engineering`, T7 → `visual-engineering`, T8 → `quick`
- **Wave 3**: 3 tasks — T9 → `unspecified-high`, T10 → `unspecified-high`, T11 → `unspecified-high`
- **Wave 4**: 2 tasks — T12 → `deep`, T13 → `unspecified-high`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Install html-to-image@1.11.11

  **What to do**:
  - Run `npm install html-to-image@1.11.11` in the `frontend/` directory
  - Verify the exact version `1.11.11` is locked in `package.json` (NOT `^1.11.11` — must be exact)
  - If npm adds a caret (`^`), edit `package.json` to remove it

  **Must NOT do**:
  - Do NOT install any version other than `1.11.11` (later versions have bugs per React Flow team)
  - Do NOT add `@types/html-to-image` (not needed, library includes types)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single npm install command + version verification
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 3, 4, 5
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `frontend/package.json` (full file, 47 lines) — Current dependencies list. Add `html-to-image` in the `dependencies` section alongside existing libraries.

  **External References**:
  - React Flow export guide: https://reactflow.dev/examples/misc/download-image — Official recommendation to use `html-to-image@1.11.11`
  - npm package: https://www.npmjs.com/package/html-to-image/v/1.11.11

  **WHY Each Reference Matters**:
  - `package.json` — Must verify the version is exactly `1.11.11`, not `^1.11.11` or `~1.11.11`

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Verify html-to-image installed at exact version
    Tool: Bash
    Preconditions: frontend/ directory exists with package.json
    Steps:
      1. Run: cd frontend && cat package.json | grep html-to-image
      2. Assert output contains "html-to-image": "1.11.11" (exact, no ^ or ~)
      3. Run: ls frontend/node_modules/html-to-image/package.json
      4. Assert file exists
    Expected Result: html-to-image@1.11.11 in package.json with exact version
    Failure Indicators: Version has ^ prefix, or different version number, or package not found
    Evidence: .sisyphus/evidence/task-1-html-to-image-version.txt
  ```

  **Commit**: YES (group 1)
  - Message: `chore(deps): add html-to-image@1.11.11 for diagram export`
  - Files: `frontend/package.json`, `frontend/package-lock.json`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

- [x] 2. Fix ports_status TS type + add PortDefinition type

  **What to do**:
  - In `frontend/src/types/api.ts`, add a new `PortDefinition` interface:
    ```typescript
    export interface PortDefinition {
      id: string;          // unique within equipment, e.g. "ge-0/0/1"
      name: string;        // display name, e.g. "GigE 1"
      type: "ethernet" | "sfp" | "sfp+" | "console" | "mgmt";
      speed: string;       // e.g. "1 Gbps", "10 Gbps"
      row: number;         // visual row (0 = top, 1 = bottom)
      index: number;       // position within row (left to right)
    }
    ```
  - Fix `Equipement` interface (line 157): change `ports_status: string | null` to `ports_status: PortDefinition[] | null`
  - Fix `cpu_ram_info` (line 163): change `string | null` to `Record<string, unknown> | null` (while we're fixing type mismatches)
  - Fix `vlan_config` (line 156): change `string | null` to `Record<string, unknown> | null`

  **Must NOT do**:
  - Do NOT change the backend model or schemas (they already accept `dict`)
  - Do NOT add any fields not in the backend response

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small type definition changes in a single file
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Tasks 6, 7, 8, 10
  - **Blocked By**: None (can start immediately)

  **References**:

  **API/Type References**:
  - `frontend/src/types/api.ts:145-170` — Current `Equipement` interface with `ports_status: string | null` on line 157, `vlan_config: string | null` on line 156, `cpu_ram_info: string | null` on line 163
  - `backend/app/schemas/equipement.py:80-81` — Backend returns `ports_status: Optional[dict]` (line 81), confirming it's a dict not string
  - `backend/app/models/equipement.py:125-126` — SQLAlchemy model: `vlan_config: Mapped[dict | None]`, `ports_status: Mapped[dict | None]` — both are JSON columns

  **WHY Each Reference Matters**:
  - `api.ts:145-170` — The exact lines to modify, showing current (incorrect) types
  - Backend schemas/models — Prove the correct types should be `dict`/`object`, not `string`

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: PortDefinition type exists and is correctly defined
    Tool: Bash (grep)
    Preconditions: frontend/src/types/api.ts exists
    Steps:
      1. Run: grep -A 8 "export interface PortDefinition" frontend/src/types/api.ts
      2. Assert output contains: id: string, name: string, type: "ethernet" | "sfp" | "sfp+", speed: string, row: number, index: number
      3. Run: grep "ports_status" frontend/src/types/api.ts
      4. Assert output contains: ports_status: PortDefinition[] | null (NOT string | null)
    Expected Result: PortDefinition interface defined, ports_status correctly typed
    Failure Indicators: ports_status still typed as string, PortDefinition missing fields
    Evidence: .sisyphus/evidence/task-2-port-definition-type.txt

  Scenario: tsc compiles without errors after type changes
    Tool: Bash
    Preconditions: All type references updated
    Steps:
      1. Run: cd frontend && npx tsc --noEmit
      2. Assert exit code 0 and no error output
    Expected Result: Zero TypeScript errors
    Failure Indicators: Type errors from existing code referencing ports_status as string
    Evidence: .sisyphus/evidence/task-2-tsc-check.txt
  ```

  **Commit**: YES (group 2)
  - Message: `feat(types): add PortDefinition type and fix ports_status typing`
  - Files: `frontend/src/types/api.ts`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

- [x] 3. Create export utility functions

  **What to do**:
  - In `frontend/src/app/outils/network-map/page.tsx`, add two export helper functions BEFORE the `NetworkMapPage` component (before line 327):
    - `exportDiagramPng(flowElement: HTMLElement, nodes: Node[])` — uses `toPng()` from `html-to-image` with `getNodesBounds()` + `getViewportForBounds()` from `@xyflow/react` to capture the full diagram
    - `exportDiagramSvg(flowElement: HTMLElement, nodes: Node[])` — uses `toSvg()` with same bounds logic
  - Both functions should:
    1. Get the `.react-flow__viewport` child element from the passed container
    2. Calculate bounds with padding (50px)
    3. Use `getViewportForBounds()` to compute the transform
    4. Call `toPng()`/`toSvg()` with width/height from bounds and style transform
    5. Create a download link and trigger click
    6. Use filename format: `network-diagram-{timestamp}.png` / `.svg`
  - Add imports at top of file: `import { toPng, toSvg } from "html-to-image";` and add `getNodesBounds, getViewportForBounds` to the existing `@xyflow/react` import (line 5-24)

  **Must NOT do**:
  - Do NOT create a separate file — keep in page.tsx (consistent with existing pattern of everything in one file)
  - Do NOT add PDF export
  - Do NOT use `html2canvas` or any other library

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Utility function following well-documented React Flow pattern
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T1 for html-to-image)
  - **Parallel Group**: Wave 1 (sequential after T1)
  - **Blocks**: Tasks 4, 5
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `frontend/src/app/outils/network-map/page.tsx:5-24` — Existing `@xyflow/react` imports. Add `getNodesBounds` and `getViewportForBounds` here.
  - `frontend/src/app/outils/network-map/page.tsx:233-251` — `DeviceNode` component shows the node rendering pattern. Export must capture these HTML-rendered nodes.
  - `frontend/src/app/outils/network-map/page.tsx:255-322` — `ParallelEdge` component with foreignObject labels. Export must handle mixed HTML+SVG.

  **External References**:
  - React Flow download image example: https://reactflow.dev/examples/misc/download-image — Official pattern using `toPng`/`toSvg` + `getNodesBounds` + `getViewportForBounds`
  - `html-to-image` API: `toPng(node, { width, height, style })`, `toSvg(node, { width, height, style })`

  **WHY Each Reference Matters**:
  - Lines 5-24 — Where to add new imports alongside existing ones
  - Lines 233-322 — Understanding what the export must capture (HTML nodes + SVG edges with foreignObject labels)
  - React Flow example — The exact algorithm for full-diagram export (not just viewport)

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Export functions exist and compile
    Tool: Bash (grep + tsc)
    Preconditions: html-to-image installed (Task 1 complete)
    Steps:
      1. Run: grep "async function exportDiagramPng" frontend/src/app/outils/network-map/page.tsx
      2. Assert function found
      3. Run: grep "async function exportDiagramSvg" frontend/src/app/outils/network-map/page.tsx
      4. Assert function found
      5. Run: grep "from \"html-to-image\"" frontend/src/app/outils/network-map/page.tsx
      6. Assert import found
      7. Run: cd frontend && npx tsc --noEmit
      8. Assert 0 errors
    Expected Result: Both export functions defined and TypeScript compiles clean
    Failure Indicators: Functions missing, import missing, or tsc errors
    Evidence: .sisyphus/evidence/task-3-export-functions.txt
  ```

  **Commit**: NO (groups with T4, T5 in commit 3)

- [x] 4. Add export buttons to site topology toolbar

  **What to do**:
  - In the site topology toolbar (lines 825-844), add two new buttons after "Recharger":
    - "Export PNG" button — calls `exportDiagramPng()` targeting the site topology ReactFlow container
    - "Export SVG" button — calls `exportDiagramSvg()` targeting the site topology ReactFlow container
  - To get the container DOM element, use a `useRef<HTMLDivElement>(null)` on the wrapping div around the site ReactFlow `<Card>` (lines 846-867). Pass the `.current` to the export function.
  - Add `Download` icon import from `lucide-react` for the export buttons
  - Pass current `nodes` state to the export function for bounds calculation

  **Must NOT do**:
  - Do NOT add PDF export button
  - Do NOT modify the ReactFlow component props

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Adding 2 buttons + 1 ref to existing toolbar
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7, 8)
  - **Blocks**: Task 13
  - **Blocked By**: Task 3

  **References**:

  **Pattern References**:
  - `frontend/src/app/outils/network-map/page.tsx:825-844` — Existing site toolbar with buttons (Auto-layout, direction toggle, Save layout, Add link, Reload). Add export buttons in the same `<Button variant="outline">` style.
  - `frontend/src/app/outils/network-map/page.tsx:846-867` — The `<Card>` containing the site ReactFlow. Needs a `ref` wrapper div for DOM access to `.react-flow__viewport`.
  - `frontend/src/app/outils/network-map/page.tsx:369` — `nodes` state variable used for bounds calculation

  **WHY Each Reference Matters**:
  - Lines 825-844 — Exact location to add buttons, following existing button pattern
  - Lines 846-867 — Container wrapping ReactFlow; need ref for export DOM target
  - Line 369 — The `nodes` state needed by `getNodesBounds()` for full-diagram export

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Export PNG button exists and triggers download on site topology
    Tool: Playwright
    Preconditions: App running at localhost:3000, user logged in, site with equipment selected
    Steps:
      1. Navigate to http://localhost:3000/outils/network-map
      2. Wait for site topology to render (selector: .react-flow)
      3. Click button with text "Export PNG"
      4. Assert a download is triggered with filename matching "network-diagram-*.png"
      5. Take screenshot
    Expected Result: PNG file downloaded
    Failure Indicators: No download triggered, button not found, error toast appears
    Evidence: .sisyphus/evidence/task-4-export-png-site.png

  Scenario: Export SVG button triggers SVG download
    Tool: Playwright
    Preconditions: Same as above
    Steps:
      1. Navigate to http://localhost:3000/outils/network-map
      2. Wait for site topology to render
      3. Click button with text "Export SVG"
      4. Assert a download is triggered with filename matching "network-diagram-*.svg"
    Expected Result: SVG file downloaded
    Failure Indicators: No download, button not found
    Evidence: .sisyphus/evidence/task-4-export-svg-site.png
  ```

  **Commit**: NO (groups with T3, T5 in commit 3)

- [x] 5. Add export buttons to multi-site overview toolbar

  **What to do**:
  - In the multi-site overview toolbar (lines 871-878), add two new buttons after "Recharger":
    - "Export PNG" — calls `exportDiagramPng()` targeting the overview ReactFlow container
    - "Export SVG" — calls `exportDiagramSvg()` targeting the overview ReactFlow container
  - Use a `useRef<HTMLDivElement>(null)` on a wrapper around the overview `<Card>` (lines 880-902) for DOM access
  - Pass `overviewNodes` state to the export function for bounds calculation

  **Must NOT do**:
  - Do NOT modify the overview ReactFlow component props
  - Do NOT add PDF export

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Same pattern as Task 4, just different container
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 6, 7, 8)
  - **Blocks**: Task 13
  - **Blocked By**: Task 3

  **References**:

  **Pattern References**:
  - `frontend/src/app/outils/network-map/page.tsx:871-878` — Overview toolbar with "Ajouter une connexion" and "Recharger" buttons. Add export buttons after.
  - `frontend/src/app/outils/network-map/page.tsx:880-902` — Overview ReactFlow `<Card>` container. Needs ref wrapper.
  - `frontend/src/app/outils/network-map/page.tsx:372` — `overviewNodes` state for bounds calculation

  **WHY Each Reference Matters**:
  - Lines 871-878 — Exact insertion point for export buttons
  - Lines 880-902 — Container needing ref for DOM access
  - Line 372 — `overviewNodes` state for `getNodesBounds()`

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Export buttons visible and functional on overview tab
    Tool: Playwright
    Preconditions: App running, user logged in, entreprise with 2+ sites and connections
    Steps:
      1. Navigate to http://localhost:3000/outils/network-map
      2. Click tab "Vue multi-site"
      3. Wait for overview ReactFlow to render
      4. Assert button "Export PNG" is visible
      5. Assert button "Export SVG" is visible
      6. Click "Export PNG"
      7. Assert download triggered with filename matching "overview-*.png"
    Expected Result: Both export buttons visible and functional on overview tab
    Failure Indicators: Buttons missing, download not triggered
    Evidence: .sisyphus/evidence/task-5-export-overview.png
  ```

  **Commit**: NO (groups with T3, T4 in commit 3)

- [x] 6. Port configuration editor component

  **What to do**:
  - Create a port editor UI section within the equipment detail dialog (currently lines 1116-1270), inserted after existing equipment details and before the close button (line 1264)
  - The editor should:
    1. Display current ports in a compact table/list: Name | Type | Speed | Row | Actions (delete button)
    2. "Ajouter un port" button that expands an inline form with: name input, type dropdown (ethernet/sfp/sfp+/console/mgmt), speed dropdown (100 Mbps to 100 Gbps), row (0 or 1), index (auto-assigned)
    3. Quick-add presets section (from Task 8) with preset buttons
    4. "Sauvegarder les ports" button that calls `equipementsApi.update(equipmentId, { ports_status: portDefinitions })` to persist
  - Only show port editor when `detailEquipement.type_equipement` is one of: `reseau`, `switch`, `router`, `access_point`
  - Add state: `const [editingPorts, setEditingPorts] = useState<PortDefinition[]>([])` — initialized from `detailEquipement.ports_status` when dialog opens
  - Auto-generate port ID: slugify name → lowercase, spaces to hyphens, e.g. "GigE 1" → "gige-1"
  - Auto-increment index within row when adding ports

  **Must NOT do**:
  - Do NOT show port editor for non-network types (serveur, firewall, camera, etc.)
  - Do NOT auto-populate from config parser
  - Do NOT create port templates or shared definitions
  - Do NOT create a separate file — keep in page.tsx

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI component with table, forms, dropdowns — needs clean layout
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Port editor needs clean table layout with inline editing

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 7, 8)
  - **Blocks**: Tasks 9, 11
  - **Blocked By**: Task 2 (needs PortDefinition type), Task 8 (provides presets)

  **References**:

  **Pattern References**:
  - `frontend/src/app/outils/network-map/page.tsx:1116-1270` — Equipment detail dialog. Port editor inserted after equipment details (line ~1260), before close button (line 1264).
  - `frontend/src/app/outils/network-map/page.tsx:912-1023` — Link dialog structure: `Dialog > DialogContent > DialogHeader > div.space-y-3 > DialogFooter`. Follow same form patterns.
  - `frontend/src/app/outils/network-map/page.tsx:951-958` — Input field pattern: `<Label>...</Label> <Input value={...} onChange={...} placeholder="..." />`

  **API/Type References**:
  - `frontend/src/types/api.ts` — `PortDefinition` interface (from Task 2): `{ id, name, type, speed, row, index }`
  - `frontend/src/types/api.ts:145-170` — `Equipement` interface with `ports_status: PortDefinition[] | null` and `type_equipement`
  - `backend/app/api/v1/equipements.py:35-44` — `_TYPE_FIELDS` confirms: reseau, switch, router, access_point support `ports_status`

  **WHY Each Reference Matters**:
  - Lines 1116-1270 — The dialog where port editor goes; understand layout to insert correctly
  - Lines 912-1023 — Dialog form patterns (labels, inputs, selects) to follow for consistency
  - `_TYPE_FIELDS` — Definitive list of which types support ports (must guard UI with this)

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Port editor visible for switch equipment
    Tool: Playwright
    Preconditions: App running, site with a switch equipment on the diagram
    Steps:
      1. Navigate to http://localhost:3000/outils/network-map
      2. Double-click on a switch node in the site topology diagram
      3. Wait for equipment detail dialog to open
      4. Scroll down in the dialog
      5. Assert a section with "Configuration des ports" heading is visible
      6. Assert "Ajouter un port" button exists
      7. Take screenshot
    Expected Result: Port editor section visible in switch detail dialog
    Failure Indicators: Section not visible, button missing, dialog doesn't scroll
    Evidence: .sisyphus/evidence/task-6-port-editor-visible.png

  Scenario: Port editor hidden for serveur equipment
    Tool: Playwright
    Preconditions: App running, site with a serveur equipment
    Steps:
      1. Double-click on a serveur node
      2. Wait for detail dialog
      3. Assert NO "Configuration des ports" text exists in the dialog
    Expected Result: Port editor not shown for non-network equipment
    Failure Indicators: Port editor visible for serveur type
    Evidence: .sisyphus/evidence/task-6-port-editor-hidden.png

  Scenario: Add a single port manually and save
    Tool: Playwright
    Preconditions: Switch detail dialog open, no ports configured
    Steps:
      1. Click "Ajouter un port"
      2. Fill name: "GigE 1"
      3. Select type: "ethernet"
      4. Select speed: "1 Gbps"
      5. Assert row defaults to 0, index auto-assigned
      6. Click confirm/add
      7. Assert port appears in the ports list table
      8. Click "Sauvegarder les ports"
      9. Assert success toast appears
      10. Close and reopen dialog — assert port persists
    Expected Result: Port added, saved to backend, persists on reload
    Failure Indicators: Port not in list, save fails, port gone after reopen
    Evidence: .sisyphus/evidence/task-6-add-port-save.png
  ```

  **Commit**: NO (groups with T7, T8 in commit 4)

- [x] 7. DetailedEquipmentNode custom React Flow node

  **What to do**:
  - Create a new React Flow custom node component `DetailedEquipmentNode` in `page.tsx` near `DeviceNode` (line 233):
    1. Renders equipment type icon + model name (hostname) + IP address at the top
    2. Renders a visual port grid below using CSS grid:
       - Top row: ports with `row === 0` sorted by `index`
       - Bottom row: ports with `row === 1` sorted by `index`
       - `grid-template-columns: repeat(N, 1fr)` where N = max ports in a row
    3. Each port = small rectangle (≈28×22px) with:
       - Background color by port type: ethernet=#6b7280, sfp=#3b82f6, sfp+=#8b5cf6, console=#f97316, mgmt=#22c55e
       - Port name as `title` attribute (tooltip on hover)
       - A React Flow `<Handle>` with `id={`port-${port.id}`}` and `type="source"` and `position={Position.Bottom}` (positioned at the port's location)
       - For target connections, also add `<Handle type="target" id={`port-${port.id}-in`}` at top of port
    4. Connected ports: brighter border (ring-2 ring-primary) — determined by `connectedPortIds` in node data
    5. Equipment border color from `nodeColorByType` (lines 124-139)
  - Define types: `type DetailedNodeData = FlowNodeData & { ports: PortDefinition[]; connectedPortIds: string[] }`
  - Register: add `detailed: React.memo(DetailedEquipmentNode)` to `nodeTypes` (line 324)
  - Memoize the component with `React.memo()` for performance
  - Update `nodeTypes` to be defined OUTSIDE the component (it already is at line 324) — just add the new type

  **Must NOT do**:
  - Do NOT use SVG for port rendering — use HTML divs with CSS grid
  - Do NOT add drag-and-drop port reordering
  - Do NOT make ports editable inline in the detailed view
  - Do NOT modify the existing `DeviceNode` component

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Visual component with CSS grid port layout, color coding, tooltips
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Port grid visual rendering needs good design

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6, 8)
  - **Blocks**: Tasks 9, 12
  - **Blocked By**: Task 2 (needs PortDefinition type)

  **References**:

  **Pattern References**:
  - `frontend/src/app/outils/network-map/page.tsx:233-251` — `DeviceNode` component. Follow same HTML div pattern (rounded-md border bg-card) but extend with port grid.
  - `frontend/src/app/outils/network-map/page.tsx:242-248` — Handle placement: `<Handle type="target" position={Position.Top}>` and `<Handle type="source" position={Position.Bottom}>`. For detailed node, each port gets its own Handle with unique `id`.
  - `frontend/src/app/outils/network-map/page.tsx:324-325` — `nodeTypes` and `edgeTypes` const definitions. Add `detailed: React.memo(DetailedEquipmentNode)` here.
  - `frontend/src/app/outils/network-map/page.tsx:124-139` — `nodeColorByType` map for equipment type border colors.
  - `frontend/src/app/outils/network-map/page.tsx:95-110` — `iconByType` map for equipment type icons.

  **API/Type References**:
  - `frontend/src/types/api.ts` — `PortDefinition`: `{ id, name, type, speed, row, index }`

  **External References**:
  - React Flow custom nodes: https://reactflow.dev/learn/customization/custom-nodes
  - React Flow multiple handles: https://reactflow.dev/api-reference/components/handle — `id` prop for unique identification

  **WHY Each Reference Matters**:
  - `DeviceNode` (233-251) — Base pattern to extend; same styling approach
  - Handle pattern (242-248) — Each port needs its own `<Handle id={...}>` for port-to-port connections
  - `nodeTypes` (324) — Registration point for the new node type
  - `nodeColorByType` + `iconByType` — Consistent visual language

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: DetailedEquipmentNode renders with port grid
    Tool: Playwright
    Preconditions: Detailed view tab active, switch with 28 ports (24 GigE + 4 SFP+)
    Steps:
      1. Navigate to detailed view tab
      2. Find the switch equipment node
      3. Assert node shows hostname and IP at top
      4. Assert port grid is visible below with small colored rectangles
      5. Count visible port elements — assert >= 28
      6. Hover over first port — assert tooltip shows "GigE 1"
      7. Take screenshot
    Expected Result: Equipment rendered with header and 28 visible ports in grid layout
    Failure Indicators: No ports visible, missing hostname/IP, no tooltips
    Evidence: .sisyphus/evidence/task-7-detailed-node-render.png

  Scenario: Different port types have different colors
    Tool: Playwright
    Preconditions: Equipment with mixed ethernet + sfp+ ports in detailed view
    Steps:
      1. Inspect ethernet port element — assert background color is gray (#6b7280)
      2. Inspect sfp+ port element — assert background color is purple (#8b5cf6)
    Expected Result: Ports color-coded by type
    Failure Indicators: All ports same color, wrong colors
    Evidence: .sisyphus/evidence/task-7-port-colors.png
  ```

  **Commit**: NO (groups with T6, T8 in commit 4)

- [x] 8. Port presets (quick-add buttons)

  **What to do**:
  - In the port editor (Task 6), add a "Préréglages" section with buttons that auto-populate the ports list:
    - "24× GigE + 4× SFP+" → 28 ports: 24 ethernet 1Gbps (row 0: indices 0-11, row 1: indices 0-11) + 4 sfp+ 10Gbps (row 0: indices 12-13, row 1: indices 12-13)
    - "48× GigE + 4× SFP+" → 52 ports: 48 ethernet 1Gbps + 4 sfp+ 10Gbps
    - "8× SFP+ 10G" → 8 sfp+ 10Gbps ports (single row)
    - "4× SFP28 25G" → 4 sfp+ 25Gbps ports (single row)
  - Define a `generatePortPreset(config: PresetConfig): PortDefinition[]` function that generates port arrays
  - Presets REPLACE existing ports — show confirmation if ports already exist: "Remplacer les X ports existants ?"
  - Auto-generate port IDs: `{type_short}-{row}-{index}` (e.g., "ge-0-1", "sfp-0-12")
  - Auto-generate port names: `{TypeLabel} {global_index+1}` (e.g., "GigE 1", "SFP+ 25")

  **Must NOT do**:
  - Do NOT create user-defined/saveable preset templates
  - Do NOT save presets to backend — only generate PortDefinition arrays client-side

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Array generation logic + buttons, straightforward
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6, 7)
  - **Blocks**: Task 6 (provides preset buttons for the port editor UI)
  - **Blocked By**: Task 2 (needs PortDefinition type)

  **References**:

  **API/Type References**:
  - `frontend/src/types/api.ts` — `PortDefinition`: `{ id, name, type, speed, row, index }`

  **Pattern References**:
  - `frontend/src/app/outils/network-map/page.tsx:141-148` — `bandwidthShort` map shows how speeds are labeled in this codebase

  **WHY Each Reference Matters**:
  - `PortDefinition` — Shape each generated port must match
  - `bandwidthShort` — Speed naming conventions in this project

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Apply "24× GigE + 4× SFP+" preset
    Tool: Playwright
    Preconditions: Port editor open for a switch, no existing ports
    Steps:
      1. Click preset button "24× GigE + 4× SFP+"
      2. Assert 28 ports appear in the ports list
      3. Assert first 24 have type "ethernet" and speed "1 Gbps"
      4. Assert last 4 have type "sfp+" and speed "10 Gbps"
      5. Assert names: "GigE 1" through "GigE 24", "SFP+ 25" through "SFP+ 28"
    Expected Result: 28 correctly typed/named ports generated
    Failure Indicators: Wrong count, wrong types/speeds, naming issues
    Evidence: .sisyphus/evidence/task-8-preset-24gige.png

  Scenario: Preset shows confirmation when replacing existing ports
    Tool: Playwright
    Preconditions: Port editor with some ports already saved
    Steps:
      1. Click any preset button
      2. Assert confirmation text appears ("Remplacer les X ports existants ?")
      3. Click confirm/OK
      4. Assert old ports replaced with preset ports
    Expected Result: Confirmation shown, then ports replaced
    Failure Indicators: No confirmation, old ports persist alongside new ones
    Evidence: .sisyphus/evidence/task-8-preset-replace-confirm.png
  ```

  **Commit**: NO (groups with T6, T7 in commit 4)

- [x] 9. Add "Vue détaillée" tab with ReactFlow instance

  **What to do**:
  - Add a 3rd tab "Vue détaillée" to the existing `<Tabs>` component (line 818):
    - Update `activeTab` type: `"site" | "overview"` → `"site" | "overview" | "detailed"`
    - Add `<TabsTrigger value="detailed">Vue détaillée</TabsTrigger>` after the overview trigger (line 821)
    - Add `<TabsContent value="detailed">` section with its own ReactFlow instance
  - Add new state for the detailed view:
    - `const [detailedNodes, setDetailedNodes, onDetailedNodesChange] = useNodesState<Node<DetailedNodeData>>([]);`
    - `const [detailedEdges, setDetailedEdges, onDetailedEdgesChange] = useEdgesState<Edge>([]);`
  - Create a `loadDetailedView` function that:
    1. Fetches site map data (reuse `networkMapApi.getSiteMap()`)
    2. For each equipment node, fetches full equipment data (reuse `equipementsApi.get()`) to get `ports_status`
    3. Creates `DetailedEquipmentNode` type nodes with port data in `node.data.ports`
    4. Computes `connectedPortIds` from link `source_interface`/`target_interface` values
    5. Creates edges with `sourceHandle` and `targetHandle` pointing to port handles (if available)
    6. Applies auto-layout with larger node dimensions (accounting for port grid size)
  - Add a toolbar above the detailed ReactFlow: "Auto-layout", "Sauvegarder layout", "Recharger"
  - Add export buttons to this tab's toolbar too (following T4/T5 pattern)
  - The detailed view's ReactFlow uses `nodeTypes` that includes `{ detailed: DetailedEquipmentNode, device: DeviceNode }` — equipment without ports falls back to `device` type

  **Must NOT do**:
  - Do NOT modify the existing site or overview tabs
  - Do NOT add link creation in the detailed view (use existing link dialog from site tab)
  - Do NOT remove any existing functionality

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: New tab with ReactFlow instance, data loading, state management — complex integration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (with Tasks 10, 11)
  - **Blocks**: Tasks 11, 12
  - **Blocked By**: Tasks 6, 7 (needs port editor + DetailedEquipmentNode)

  **References**:

  **Pattern References**:
  - `frontend/src/app/outils/network-map/page.tsx:818-910` — Full tab structure: `<Tabs>` with `<TabsList>` containing triggers, and `<TabsContent>` for each tab. Add 3rd tab following exact same pattern.
  - `frontend/src/app/outils/network-map/page.tsx:824-868` — Site tab: toolbar + Card + ReactFlow + Background + Controls + MiniMap. Replicate this structure for detailed view.
  - `frontend/src/app/outils/network-map/page.tsx:369-373` — State declarations for nodes/edges using `useNodesState`/`useEdgesState`. Add matching state for detailed view.
  - `frontend/src/app/outils/network-map/page.tsx:398-409` — `loadSiteMap` function pattern: fetch data, transform to nodes/edges, apply layout, set state.
  - `frontend/src/app/outils/network-map/page.tsx:337` — `activeTab` state. Extend type union.
  - `frontend/src/app/outils/network-map/page.tsx:210-231` — `autoLayout` function. Reuse with adjusted node dimensions for detailed nodes (wider + taller).

  **API/Type References**:
  - `frontend/src/services/api.ts:447-451` — `networkMapApi.getSiteMap(siteId)` returns `NetworkMap`
  - `frontend/src/types/api.ts:475-485` — `NetworkMapNode` includes `metadata` and `position`

  **WHY Each Reference Matters**:
  - Lines 818-910 — Tab structure to extend with 3rd tab
  - Lines 824-868 — Complete tab content pattern to replicate
  - Lines 369-373 — State pattern for new ReactFlow instance
  - Lines 398-409 — Data loading pattern to follow/extend
  - `autoLayout` — Reuse layout algorithm with larger node dimensions

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: "Vue détaillée" tab appears and renders
    Tool: Playwright
    Preconditions: App running, user logged in, site with equipment selected
    Steps:
      1. Navigate to http://localhost:3000/outils/network-map
      2. Assert 3 tabs visible: "Topologie site", "Vue multi-site", "Vue détaillée"
      3. Click "Vue détaillée" tab
      4. Wait for ReactFlow to render (selector: .react-flow inside the detailed tab content)
      5. Assert equipment nodes are visible
      6. Take screenshot
    Expected Result: 3rd tab renders with ReactFlow showing equipment
    Failure Indicators: Tab missing, ReactFlow empty, no nodes
    Evidence: .sisyphus/evidence/task-9-detailed-tab.png

  Scenario: Equipment without ports renders as fallback DeviceNode
    Tool: Playwright
    Preconditions: Site has equipment with ports AND equipment without ports
    Steps:
      1. Open "Vue détaillée" tab
      2. Find equipment without ports — assert it renders as simple DeviceNode (small node, no port grid)
      3. Find equipment with ports — assert it renders with port grid
    Expected Result: Mixed rendering based on port configuration
    Failure Indicators: All nodes same type, crash when ports missing
    Evidence: .sisyphus/evidence/task-9-mixed-nodes.png
  ```

  **Commit**: YES (commit 5)
  - Message: `feat(network-map): add detailed view tab with port-level equipment nodes`
  - Files: `frontend/src/app/outils/network-map/page.tsx`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

- [x] 10. Update link dialog with optional port picker

  **What to do**:
  - In the existing link dialog (lines 912-1023), add OPTIONAL port picker dropdowns:
    - After "Interface source" input (line 953-955), add a "Port source" `<Select>` dropdown
    - After "Interface cible" input (line 957-958), add a "Port cible" `<Select>` dropdown
  - Port picker behavior:
    - Populate from source/target equipment's `ports_status` array
    - When source equipment is selected, fetch its `ports_status` via `equipementsApi.get()` (or cache from loaded data)
    - Show port names in dropdown: "GigE 1 (ethernet, 1 Gbps)", "SFP+ 25 (sfp+, 10 Gbps)"
    - Selection is OPTIONAL — "Aucun" option as default (empty value)
    - When a port is selected, auto-fill the "Interface source/cible" text input with the port name
    - Store selected port ID in `source_interface` / `target_interface` on save
  - Add state: `const [sourceEquipPorts, setSourceEquipPorts] = useState<PortDefinition[]>([])` and same for target
  - Add effect: when `sourceEquipementId` changes, fetch equipment and set ports. Same for target.
  - If equipment has no ports configured, hide the port picker dropdown (show only the text input as currently)

  **Must NOT do**:
  - Do NOT make port selection mandatory
  - Do NOT change the backend NetworkLink model (source_interface/target_interface already exist as strings)
  - Do NOT break existing link creation/editing flow
  - Do NOT modify backend API endpoints

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Modifying existing dialog with conditional UI + data fetching
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 11)
  - **Blocks**: Task 12
  - **Blocked By**: Task 2 (needs PortDefinition type)

  **References**:

  **Pattern References**:
  - `frontend/src/app/outils/network-map/page.tsx:912-1023` — Full link dialog. Port pickers go after interface inputs.
  - `frontend/src/app/outils/network-map/page.tsx:951-958` — Interface source/target inputs. Port picker `<Select>` goes above or alongside these.
  - `frontend/src/app/outils/network-map/page.tsx:921-949` — Source/target equipment selects. When selected, fetch equipment's ports.
  - `frontend/src/app/outils/network-map/page.tsx:604-625` — `onNodeDoubleClick` shows pattern for fetching equipment details via `equipementsApi.get(eqId)`.

  **API/Type References**:
  - `frontend/src/types/api.ts:145-170` — `Equipement` with `ports_status: PortDefinition[] | null`
  - `frontend/src/types/api.ts:446-460` — `NetworkLink` with `source_interface: string | null`, `target_interface: string | null`
  - `backend/app/models/network_map.py:31-32` — Backend stores `source_interface`/`target_interface` as String(100) — port IDs fit

  **WHY Each Reference Matters**:
  - Lines 912-1023 — The dialog to modify; understand form layout
  - Lines 951-958 — Where to insert port pickers (above/alongside interface inputs)
  - Lines 921-949 — Equipment selection triggers port data fetch
  - Line 604-625 — Pattern for `equipementsApi.get()` call

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Port picker appears when equipment has ports
    Tool: Playwright
    Preconditions: Link dialog open, source equipment (switch) has ports configured
    Steps:
      1. Open link dialog (click "Ajouter un lien")
      2. Select source equipment (a switch with ports)
      3. Assert "Port source" dropdown appears with port options
      4. Assert "Aucun" is selected by default
      5. Select a port (e.g., "GigE 1")
      6. Assert "Interface source" input auto-filled with "GigE 1"
      7. Take screenshot
    Expected Result: Port picker shows equipment ports, selection auto-fills interface
    Failure Indicators: Dropdown missing, no ports listed, interface not auto-filled
    Evidence: .sisyphus/evidence/task-10-port-picker.png

  Scenario: Port picker hidden when equipment has no ports
    Tool: Playwright
    Preconditions: Link dialog open, equipment without ports configured
    Steps:
      1. Select source equipment (a serveur with no ports_status)
      2. Assert NO "Port source" dropdown appears
      3. Assert "Interface source" text input still works for manual entry
    Expected Result: No port picker for equipment without ports; manual input works
    Failure Indicators: Port picker shown for portless equipment, input broken
    Evidence: .sisyphus/evidence/task-10-no-port-picker.png

  Scenario: Link saved without port selection (backward compatible)
    Tool: Playwright
    Preconditions: Link dialog open with equipment that has ports
    Steps:
      1. Select source and target equipment
      2. Leave port pickers on "Aucun"
      3. Select link type, bandwidth
      4. Click "Créer le lien"
      5. Assert success toast
      6. Assert link created (visible in diagram)
    Expected Result: Link created successfully without port selection
    Failure Indicators: Save fails, validation error requiring port
    Evidence: .sisyphus/evidence/task-10-link-without-port.png
  ```

  **Commit**: NO (groups with T11, T12 in commit 6)

- [x] 11. Data loading for detailed view (ports + edges)

  **What to do**:
  - Implement the `loadDetailedView` callback (registered in Task 9) with full data loading logic:
    1. Call `networkMapApi.getSiteMap(siteId)` to get the site map with all nodes and edges
    2. For each node in the map, call `equipementsApi.get(node.equipement_id)` to get full equipment data including `ports_status`
    3. Transform each equipment into a detailed node:
       - If `ports_status` is an array with items → type `"detailed"`, data includes `ports` and `connectedPortIds`
       - If `ports_status` is null/empty → type `"device"` (fallback to simple node)
    4. Compute `connectedPortIds` per equipment: look at all edges where equipment is source or target, collect `source_interface`/`target_interface` values
    5. Create edges:
       - If edge has `source_interface` AND `target_interface` matching port IDs → use `sourceHandle: "port-{source_interface}"`, `targetHandle: "port-{target_interface}-in"`
       - If edge has NO matching ports → create edge between node centers (no handles) — backward compatible
    6. Apply auto-layout with larger node dimensions:
       - Estimate width: `max(200, numPortsInRow * 32 + 40)` px
       - Estimate height: `80 + numRows * 30` px
  - Add loading state for the detailed view
  - Trigger reload when site changes or when switching to the detailed tab
  - Use `Promise.all` for parallel equipment fetches (batch)

  **Must NOT do**:
  - Do NOT make N+1 sequential API calls — batch with Promise.all
  - Do NOT cache stale data across site changes
  - Do NOT modify backend endpoints

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Complex data transformation with multiple API calls and node type decisions
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 10)
  - **Blocks**: Task 12
  - **Blocked By**: Tasks 6 (port editor saves ports to use), 9 (tab + state exist)

  **References**:

  **Pattern References**:
  - `frontend/src/app/outils/network-map/page.tsx:398-409` — `loadSiteMap` function: fetches data, transforms nodes/edges, applies layout. Follow same pattern but extend.
  - `frontend/src/app/outils/network-map/page.tsx:162-208` — `toFlowNodes` and `toFlowEdges` functions. Adapt for detailed view with port-aware transformation.
  - `frontend/src/app/outils/network-map/page.tsx:210-231` — `autoLayout` function. Reuse with dynamic node dimensions.
  - `frontend/src/app/outils/network-map/page.tsx:411-447` — `loadOverview` function. Shows how to transform API data into ReactFlow nodes/edges.

  **API/Type References**:
  - `frontend/src/services/api.ts:447-451` — `networkMapApi.getSiteMap(siteId)` returns `NetworkMap` with nodes + edges
  - `frontend/src/types/api.ts:475-485` — `NetworkMapNode`: `{ id, equipement_id, site_id, type_equipement, ip_address, hostname, label, metadata }`
  - `frontend/src/types/api.ts:487-500` — `NetworkMapEdge`: `{ id, link_id, source, target, metadata }` — metadata contains source_interface/target_interface
  - `frontend/src/types/api.ts:446-460` — `NetworkLink` with `source_interface`/`target_interface`

  **WHY Each Reference Matters**:
  - `loadSiteMap` (398-409) — Same pattern to follow, extended with equipment fetch
  - `toFlowNodes`/`toFlowEdges` (162-208) — Data transformation pattern to adapt
  - `autoLayout` (210-231) — Must pass dynamic dimensions for detailed nodes
  - API types — Understanding the data shapes for transformation

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Detailed view loads all equipment with ports
    Tool: Playwright
    Preconditions: Site with 3+ equipment, at least 2 with ports configured
    Steps:
      1. Click "Vue détaillée" tab
      2. Wait for loading to complete (no spinner visible)
      3. Count equipment nodes — assert matches site equipment count
      4. Assert equipment with ports shows port grids
      5. Assert equipment without ports shows simple DeviceNode
    Expected Result: All equipment loaded with correct node types
    Failure Indicators: Missing nodes, loading stuck, wrong node types
    Evidence: .sisyphus/evidence/task-11-load-detailed.png

  Scenario: Edges connect between equipment nodes
    Tool: Playwright
    Preconditions: Site with linked equipment, at least one link between equipment with ports
    Steps:
      1. Open detailed view
      2. Assert edge lines visible between connected equipment
      3. For a link with port data — assert edge connects to specific port handle (not node center)
      4. For a link without port data — assert edge connects to node center
    Expected Result: Edges render correctly, port-specific when data exists
    Failure Indicators: No edges, all edges at center, edges pointing to wrong ports
    Evidence: .sisyphus/evidence/task-11-edges-detailed.png
  ```

  **Commit**: NO (groups with T10, T12 in commit 6)

- [x] 12. Integration: port-to-port edges in detailed view

  **What to do**:
  - Verify and polish the full integration of port-to-port edges in the detailed view:
    1. Ensure `ParallelEdge` component works with `sourceHandle`/`targetHandle` props — edges between specific ports should render curved paths from port to port
    2. If `ParallelEdge` doesn't handle per-handle positioning well, create a simple straight/curved edge variant for port connections
    3. Edge labels should still show link info (link type, bandwidth, interface names) using the existing `toFlowEdges` pattern
    4. Test with multiple edges between the same pair of equipment (LAGG/MLAGG scenario) — parallel edges should offset correctly between different ports
    5. Connected ports should be highlighted: add `ring-2 ring-primary` CSS class to port elements whose ID is in `connectedPortIds`
  - Ensure the detailed view's `edgeTypes` includes `parallel: ParallelEdge`
  - Test edge cases:
    - Equipment with ports connected to equipment without ports
    - Multiple edges between same equipment pair going to different ports
    - Edge with only source port but no target port

  **Must NOT do**:
  - Do NOT modify the `ParallelEdge` component behavior for site/overview tabs
  - Do NOT break existing edge rendering

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Integration task requiring careful edge handling with parallel edges + port handles
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (sequential — depends on T7, T9, T10, T11)
  - **Blocks**: Task 13
  - **Blocked By**: Tasks 7, 9, 10, 11

  **References**:

  **Pattern References**:
  - `frontend/src/app/outils/network-map/page.tsx:255-322` — `ParallelEdge` component. Uses `useReactFlow().getEdges()` for sibling detection and offset. Must work with `sourceHandle`/`targetHandle` when present.
  - `frontend/src/app/outils/network-map/page.tsx:178-208` — `toFlowEdges` function: edge label construction pattern with link type, bandwidth, interface names.
  - `frontend/src/app/outils/network-map/page.tsx:253` — `PARALLEL_EDGE_SPACING = 35` constant.

  **External References**:
  - React Flow edge with handles: https://reactflow.dev/api-reference/types/edge — `sourceHandle` and `targetHandle` props on Edge objects

  **WHY Each Reference Matters**:
  - `ParallelEdge` (255-322) — The edge component that must handle port-specific source/target positions
  - `toFlowEdges` (178-208) — Label formatting pattern to maintain in detailed view
  - `PARALLEL_EDGE_SPACING` — Same spacing constant for parallel edges between ports

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Port-to-port edge renders between specific ports
    Tool: Playwright
    Preconditions: Two switches with ports, link with source_interface and target_interface matching port IDs
    Steps:
      1. Open detailed view tab
      2. Find the edge between the two switches
      3. Assert edge path originates from source port handle area (not node center)
      4. Assert edge path terminates at target port handle area
      5. Assert connected ports have highlight styling (ring/border)
      6. Take screenshot showing the connection
    Expected Result: Edge visually connects specific ports, ports highlighted
    Failure Indicators: Edge at node center, no port highlighting, edge path incorrect
    Evidence: .sisyphus/evidence/task-12-port-to-port-edge.png

  Scenario: Parallel edges between same equipment with different ports
    Tool: Playwright
    Preconditions: Two switches with 2+ links between them, each on different ports
    Steps:
      1. Open detailed view
      2. Find both edges between the same equipment pair
      3. Assert edges are visually separated (not overlapping)
      4. Assert each edge connects to its respective ports
    Expected Result: Multiple edges between same pair are distinguishable
    Failure Indicators: Edges overlap completely, wrong port connections
    Evidence: .sisyphus/evidence/task-12-parallel-port-edges.png

  Scenario: Edge without port data falls back to node center
    Tool: Playwright
    Preconditions: Link between equipment where source_interface/target_interface don't match port IDs
    Steps:
      1. Open detailed view
      2. Find the edge for the portless link
      3. Assert edge connects to node center (no sourceHandle/targetHandle)
    Expected Result: Graceful fallback for links without port data
    Failure Indicators: Edge missing, error in console, crash
    Evidence: .sisyphus/evidence/task-12-edge-fallback.png
  ```

  **Commit**: NO (groups with T10, T11 in commit 6)

- [ ] 13. Final tsc --noEmit + visual QA

  **What to do**:
  - Run `cd frontend && npx tsc --noEmit` — fix ANY errors
  - Run the dev server and visually verify all 3 tabs:
    1. Site topology: existing features work, export PNG/SVG buttons functional
    2. Multi-site overview: existing features work, export buttons functional
    3. Detailed view: equipment with ports renders port grids, edges connect, port editor works
  - Verify backward compatibility:
    - Double-click node opens equipment detail dialog (still works)
    - Double-click edge opens link edit dialog (still works)
    - Create new link without port selection (still works)
    - Site connection CRUD in overview tab (still works)
    - Auto-layout + save layout + direction toggle (still works)
  - Fix any visual issues: overlapping elements, misaligned text, broken responsive layout
  - Check dark mode compatibility (the app uses `next-themes`)

  **Must NOT do**:
  - Do NOT add new features — only fix issues
  - Do NOT refactor working code

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Comprehensive verification across all features + dark mode
  - **Skills**: [`playwright`]
    - `playwright`: Browser-based visual verification of all tabs

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (after T12)
  - **Blocks**: Final verification wave
  - **Blocked By**: Tasks 4, 5, 12

  **References**:

  **Pattern References**:
  - `frontend/src/app/outils/network-map/page.tsx` (entire file) — All changes are in this file. Full review needed.
  - `frontend/src/types/api.ts` — PortDefinition type and Equipement interface changes.

  **WHY Each Reference Matters**:
  - `page.tsx` — Single file containing ALL changes; must verify end-to-end
  - `api.ts` — Type changes that affect compilation

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: tsc --noEmit passes
    Tool: Bash
    Preconditions: All implementation tasks complete
    Steps:
      1. Run: cd frontend && npx tsc --noEmit
      2. Assert exit code 0
      3. Assert no error output
    Expected Result: Zero TypeScript compilation errors
    Failure Indicators: Any error output
    Evidence: .sisyphus/evidence/task-13-tsc-clean.txt

  Scenario: All 3 tabs render correctly
    Tool: Playwright
    Preconditions: App running, user logged in, site with equipment and links
    Steps:
      1. Navigate to http://localhost:3000/outils/network-map
      2. Assert "Topologie site" tab is active, diagram renders
      3. Click "Vue multi-site" — assert overview renders with site nodes and connection edges
      4. Click "Vue détaillée" — assert detailed view renders with equipment nodes
      5. Take screenshots of all 3 tabs
    Expected Result: All tabs render correctly without errors
    Failure Indicators: Any tab crashes, empty content, console errors
    Evidence: .sisyphus/evidence/task-13-all-tabs.png

  Scenario: Backward compatibility — existing features work
    Tool: Playwright
    Preconditions: App running with existing data
    Steps:
      1. On site topology: double-click node → assert detail dialog opens
      2. On site topology: double-click edge → assert link edit dialog opens
      3. On overview: double-click edge → assert connection edit dialog opens
      4. Auto-layout button → assert nodes rearrange
      5. Direction toggle → assert layout switches TB/LR
    Expected Result: All existing features continue working
    Failure Indicators: Any feature broken
    Evidence: .sisyphus/evidence/task-13-backward-compat.png

  Scenario: Dark mode compatibility
    Tool: Playwright
    Preconditions: App running
    Steps:
      1. Toggle dark mode (via theme switcher)
      2. Navigate through all 3 tabs
      3. Assert no invisible text, no contrast issues, port colors visible
      4. Take dark mode screenshot
    Expected Result: All features visible and usable in dark mode
    Failure Indicators: Text invisible on dark background, ports not visible
    Evidence: .sisyphus/evidence/task-13-dark-mode.png
  ```

  **Commit**: YES (commit 7 — if any fixes were needed)
  - Message: `fix(network-map): resolve TypeScript errors and visual issues`
  - Files: `frontend/src/app/outils/network-map/page.tsx`
  - Pre-commit: `cd frontend && npx tsc --noEmit`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `tsc --noEmit` + linter. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp).
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill)
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together, not isolation). Test edge cases: empty state, invalid input, rapid actions. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (`git log`/`diff`). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| Commit | Tasks | Message | Files | Pre-commit |
|--------|-------|---------|-------|------------|
| 1 | T1 | `chore(deps): add html-to-image@1.11.11 for diagram export` | `frontend/package.json`, `frontend/package-lock.json` | `tsc --noEmit` |
| 2 | T2 | `feat(types): add PortDefinition type and fix ports_status typing` | `frontend/src/types/api.ts` | `tsc --noEmit` |
| 3 | T3-T5 | `feat(network-map): add PNG/SVG export for site and overview diagrams` | `frontend/src/app/outils/network-map/page.tsx` | `tsc --noEmit` |
| 4 | T6-T8 | `feat(network-map): add port configuration editor with presets` | `frontend/src/app/outils/network-map/page.tsx` | `tsc --noEmit` |
| 5 | T7, T9 | `feat(network-map): add detailed view tab with port-level equipment nodes` | `frontend/src/app/outils/network-map/page.tsx` | `tsc --noEmit` |
| 6 | T10-T12 | `feat(network-map): port picker in link dialog and port-to-port edges` | `frontend/src/app/outils/network-map/page.tsx` | `tsc --noEmit` |

---

## Success Criteria

### Verification Commands
```bash
cd frontend && npx tsc --noEmit  # Expected: 0 errors
python -m py_compile backend/app/models/equipement.py  # Expected: no output (success)
python -m py_compile backend/app/api/v1/equipements.py  # Expected: no output (success)
```

### Final Checklist
- [ ] `html-to-image@1.11.11` installed (exact version)
- [ ] Export PNG works on site topology tab
- [ ] Export SVG works on site topology tab
- [ ] Export PNG works on multi-site overview tab
- [ ] Export SVG works on multi-site overview tab
- [ ] `PortDefinition` type exists and `ports_status` typed correctly
- [ ] Port editor renders for network equipment types (reseau, switch, router, access_point)
- [ ] Port editor disabled/hidden for non-network types
- [ ] Port presets work (24×GigE+4×SFP+, etc.)
- [ ] "Vue détaillée" tab renders as 3rd tab
- [ ] Detailed view shows all site equipment with port grids
- [ ] Port-to-port edges render between equipment in detailed view
- [ ] Link dialog has optional port picker
- [ ] Existing links without ports still work in all views
- [ ] `tsc --noEmit` returns 0 errors
- [ ] All labels in French
