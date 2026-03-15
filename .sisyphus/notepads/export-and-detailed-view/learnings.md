## [2026-03-15] Task 3: Export functions

### Implementation Details

Successfully added two export utility functions to `frontend/src/app/outils/network-map/page.tsx`:

1. **exportDiagramPng** (line 330)
   - Exports network diagram as PNG with 1024x768 resolution
   - Uses React Flow's official pattern: getNodesBounds() → getViewportForBounds() → toPng()
   - Adds 50px padding on all sides
   - Downloads with filename format: `network-diagram-YYYY-MM-DD.png`
   - Includes error handling with toast notifications

2. **exportDiagramSvg** (line 372)
   - Exports network diagram as SVG with identical resolution and pattern
   - Uses toSvg() instead of toPng()
   - Filename format: `network-diagram-YYYY-MM-DD.svg`
   - Error handling consistent with PNG export

### Imports Added

- New import: `import { toPng, toSvg } from "html-to-image";` (line 43)
- Extended @xyflow/react import with: `getNodesBounds, getViewportForBounds`

### React Flow Pattern Notes

- Viewport calculation uses padding value of 50/100 = 0.5 in getViewportForBounds()
- The transform style includes translate and scale operations
- Both functions target `.react-flow__viewport` element selector
- Proper null-checking for HTMLElement type safety

### TypeScript Verification

- Command: `cd frontend && npx tsc --noEmit`
- Result: No new errors introduced
- Baseline maintained (7 pre-existing errors in other files unchanged)

### Key Learnings for Future Tasks

- html-to-image library correctly handles capturing React Flow viewport elements
- The official React Flow export pattern is production-ready
- Downloads trigger via dynamically created anchor elements with click()
- Error handling should use both console.error and toast notifications for user feedback
- Filename consistency with ISO date format (YYYY-MM-DD) supports easy file organization

## [2026-03-15] Task 2: PortDefinition type

### Implementation Details

Successfully added PortDefinition interface and fixed three type mismatches in `frontend/src/types/api.ts`:

1. **PortDefinition Interface** (line 144)
   - Added before Equipement interface definition
   - 6 fields as specified: id (string), name (string), type (union of 5 port types), speed (string), row (number), index (number)
   - Includes documentation comments for each field with examples
   - Type union for port type: "ethernet" | "sfp" | "sfp+" | "console" | "mgmt"

2. **Type Fixes in Equipement Interface**
   - Line 156: `vlan_config` changed from `string | null` to `Record<string, unknown> | null`
   - Line 157: `ports_status` changed from `string | null` to `PortDefinition[] | null`
   - Line 163: `cpu_ram_info` changed from `string | null` to `Record<string, unknown> | null`

### Backend Alignment

These changes align with backend definitions:
- `backend/app/models/equipement.py`: Both vlan_config and ports_status defined as JSON columns (Mapped[dict | None])
- `backend/app/schemas/equipement.py`: Backend schemas return Optional[dict] for these fields
- Frontend types were incorrectly typed as strings, causing type mismatches when backend returns dict objects

### TypeScript Verification

- Command: `cd frontend && npx tsc --noEmit`
- Result: Exit code 0, no TypeScript errors
- No new errors introduced (baseline maintained)

### Key Design Decisions

1. PortDefinition uses array type (PortDefinition[] | null) to support multiple ports per equipment
2. Record<string, unknown> for vlan_config and cpu_ram_info provides flexibility for varying JSON structures from backend
3. Port type union defined as literal types for strict type checking in port configuration UI
4. Numerical fields (row, index) use number type to ensure type-safe calculations in UI positioning

## [2026-03-15] Task 4: Site export buttons

### Implementation Details

Successfully added two export buttons to site topology toolbar in `frontend/src/app/outils/network-map/page.tsx`:

1. **Import Addition** (line 3)
   - Added `useRef` to React imports: `import { useCallback, useEffect, useMemo, useRef, useState }`
   - Added `Download` icon to lucide-react imports (line 31 in alphabetical order)

2. **Ref Creation** (line 465)
   - Created `const siteFlowRef = useRef<HTMLDivElement>(null);` in NetworkMapPage component body
   - Properly typed as HTMLDivElement to match DOM element

3. **DOM Wrapping** (lines 939-959)
   - Wrapped existing Card element (containing ReactFlow component) with `<div ref={siteFlowRef}>`
   - Preserved all internal structure and props of ReactFlow component
   - Card height and padding remain unchanged (h-[70vh] p-0)

4. **Button Implementation** (lines 934-950)
   - Added 2 buttons after the "Recharger" button in toolbar
   - Both use `variant="outline"` style consistent with other toolbar buttons
   - Each button includes Download icon with tailwind spacing: `<Download className="h-4 w-4 mr-2" />`
   - Button labels in French: "Export PNG" and "Export SVG"
   - Both buttons include null-check guard: `if (siteFlowRef.current) { exportFunction(...) }`
   - Click handlers pass ref.current (HTMLElement) and nodes array to export functions

### Ref Assignment Pattern

```tsx
const siteFlowRef = useRef<HTMLDivElement>(null);
// ... in JSX:
<div ref={siteFlowRef}>
  <Card>
    <ReactFlow ... />
  </Card>
</div>
```

This pattern allows exportDiagramPng/Svg functions to access the complete Card DOM element including ReactFlow viewport for screenshot capture.

### TypeScript Verification

- Command: `cd frontend && npx tsc --noEmit`
- Result: Exit code 0, no errors
- useRef properly imported and typed
- Ref usage consistent with React TypeScript patterns
- No regressions on baseline (7 pre-existing errors unchanged)

### Integration with Export Functions

The two export buttons wire directly to Task 3 functions:
- `exportDiagramPng(siteFlowRef.current, nodes)` - exports PNG with ISO date filename
- `exportDiagramSvg(siteFlowRef.current, nodes)` - exports SVG with ISO date filename
- Both functions handle error cases with toast notifications (French messages)

### Key Design Decisions

1. Ref wraps the entire Card (not just ReactFlow) to ensure html-to-image captures the full diagram with Card styling
2. Null-check guard (`if (siteFlowRef.current)`) prevents calling export functions with undefined
3. Both buttons use consistent styling with existing toolbar (variant="outline")
4. Download icon imported from lucide-react matches UI design system
5. Buttons positioned after "Recharger" for logical grouping of "reload + export" actions

## [2026-03-15] Task 5: Overview export buttons

### Implementation Details

Successfully added two export buttons to multi-site overview toolbar in `frontend/src/app/outils/network-map/page.tsx`:

1. **Ref Creation** (line 464)
   - Created `const overviewFlowRef = useRef<HTMLDivElement>(null);` right after `siteFlowRef`
   - Properly typed as HTMLDivElement to match Task 4 pattern
   - Declared in NetworkMapPage component body

2. **Button Implementation** (lines 989-1006)
   - Added 2 buttons after the "Recharger" button in overview toolbar (same location as site export buttons)
   - Both use `variant="outline"` style for consistency with existing buttons
   - Each button includes Download icon: `<Download className="h-4 w-4 mr-2" />`
   - Button labels in French: "Export PNG" and "Export SVG"
   - Both buttons include null-check guard: `if (overviewFlowRef.current) { ... }`
   - Click handlers pass ref.current (HTMLElement) and **overviewNodes** to export functions

3. **DOM Wrapping** (lines 1009-1032)
   - Wrapped existing Card element with `<div ref={overviewFlowRef}>`
   - Card contains ReactFlow component with all overview configuration
   - Structure preserved: Card → CardContent → ReactFlow → Background/Controls/MiniMap

### Critical Implementation Notes

**IMPORTANT**: Used `overviewNodes` (not `nodes`) as state parameter
- Site topology uses: `nodes` state (from useNodesState)
- Multi-site overview uses: `overviewNodes` state (from useNodesState)
- This distinction was necessary to match the correct data source for each view
- Both states defined around line 460-461

### Ref Assignment Pattern (Consistent with Task 4)

```tsx
const overviewFlowRef = useRef<HTMLDivElement>(null);
// ... in JSX:
<div ref={overviewFlowRef}>
  <Card>
    <ReactFlow nodes={overviewNodes} ... />
  </Card>
</div>
```

This identical pattern to Task 4 ensures consistent export functionality across both views.

### TypeScript Verification

- Command: `cd frontend && npx tsc --noEmit`
- Result: Exit code 0, no errors
- Baseline maintained (7 pre-existing errors in collecte/page.tsx unchanged)
- No new TypeScript issues introduced

### Integration with Export Functions

The two export buttons wire directly to Task 3 functions:
- `exportDiagramPng(overviewFlowRef.current, overviewNodes)` - exports PNG with ISO date filename
- `exportDiagramSvg(overviewFlowRef.current, overviewNodes)` - exports SVG with ISO date filename

### Key Design Decisions

1. Identical pattern to Task 4 for consistency - same ref wrapper structure, button styling, icon usage
2. Separate ref (overviewFlowRef) from site ref (siteFlowRef) allows independent export captures of both views
3. State variable alignment: always pass matching state (overviewNodes for overview tab)
4. Null-check guard prevents undefined ref errors
5. Download icon and French labels match Task 4 implementation exactly
6. Buttons positioned after "Recharger" for logical grouping consistent with site topology view

### Learnings Applied

- Task 4 established the exact pattern for export buttons (ref + wrapper + null-check)
- Task 5 successfully applied identical pattern to second ReactFlow view
- State variable names matter: each view has its own nodes state to prevent data mismatches
- Dual-view export functionality now complete, ready for Task 13 QA

## [2026-03-15] Task 8: Port preset generator functions

### Implementation Details

Successfully added `generatePortPreset(presetType: string): PortDefinition[]` function to `frontend/src/app/outils/network-map/page.tsx` (line 343).

### Function Placement
- Location: Lines 332-490 in page.tsx
- Positioned BEFORE NetworkMapPage component (before line 540)
- Placed after nodeTypes/edgeTypes declarations, before exportDiagramPng function
- Follows TypeScript conventions for utility functions

### Preset Types Implemented

1. **"24×GigE+4×SFP+"** (28 ports)
   - 24× Ethernet 1Gbps: Port IDs `ge-0-0` through `ge-0-11` (row 0), `ge-1-0` through `ge-1-11` (row 1)
   - Names: "GigE 1" through "GigE 24"
   - 4× SFP+ 10Gbps: Port IDs `sfp-0-12`, `sfp-0-13`, `sfp-1-12`, `sfp-1-13`
   - Names: "SFP+ 25" through "SFP+ 28"

2. **"48×GigE+4×SFP+"** (52 ports)
   - 48× Ethernet 1Gbps: Port IDs `ge-0-0` through `ge-0-23` (row 0), `ge-1-0` through `ge-1-23` (row 1)
   - Names: "GigE 1" through "GigE 48"
   - 4× SFP+ 10Gbps: Port IDs `sfp-0-24`, `sfp-0-25`, `sfp-1-24`, `sfp-1-25`
   - Names: "SFP+ 49" through "SFP+ 52"

3. **"8×SFP+10G"** (8 ports)
   - 8× SFP+ 10Gbps: Port IDs `sfp-0-0` through `sfp-0-3` (row 0), `sfp-1-0` through `sfp-1-3` (row 1)
   - Names: "SFP+ 1" through "SFP+ 8"

4. **"4×SFP28-25G"** (4 ports)
   - 4× SFP+ 25Gbps: Port IDs `sfp-0-0` through `sfp-0-3` (all on row 0)
   - Names: "SFP+ 1" through "SFP+ 4"

### Port ID Auto-Generation Pattern
Format: `{type_short}-{row}-{index}`
- Type short codes: "ge" (ethernet), "sfp" (both sfp and sfp+)
- Row: 0 (top) or 1 (bottom)
- Index: 0-based position within row

### Port Name Auto-Generation Pattern
Format: `{TypeLabel} {global_index+1}`
- Type labels: "GigE" (ethernet), "SFP+" (sfp/sfp+)
- Global index: Sequential counter across all ports (1-indexed for display)
- Each preset maintains continuous numbering from start to end

### Type Safety
- Added `PortDefinition` to imports from `@/types` (line 89)
- Function signature: `function generatePortPreset(presetType: string): PortDefinition[]`
- All 6 required fields provided for each port: id, name, type, speed, row, index
- Type literals used: "ethernet" | "sfp+" for port types

### Row Distribution
- Row 0 = top row (visual layout)
- Row 1 = bottom row (visual layout)
- "24×GigE+4×SFP+": 14 ports per row (12 GigE + 2 SFP+)
- "48×GigE+4×SFP+": 26 ports per row (24 GigE + 2 SFP+)
- "8×SFP+10G": 4 ports per row (4 SFP+)
- "4×SFP28-25G": All 4 ports on row 0 only

### Speed Strings Used
- "1 Gbps" for Ethernet ports
- "10 Gbps" for SFP+ 10G ports
- "25 Gbps" for SFP+ 25G ports (SFP28)

### TypeScript Verification
- Command: `cd frontend && npx tsc --noEmit`
- Result: Exit code 0, no errors
- PortDefinition type correctly imported
- All return types match function signature

### Docstring Implementation
- Added comprehensive JSDoc docstring (lines 332-342)
- Documents purpose, port ID/name generation patterns, all 4 preset types with port counts
- Necessary as public API function used by Task 6 UI buttons

### Key Design Decisions

1. **Global index counter** - Tracks sequential port names across entire preset
2. **Row-based distribution** - Ports explicitly split between row 0 and row 1 for visual layout
3. **Sequential indices within row** - Indices are 0-based positions within their row (not global positions)
4. **Type-specific naming** - "GigE" vs "SFP+" labels distinguish port speeds
5. **Default case** - Invalid preset types trigger console.warn and return empty array (graceful degradation)
6. **Speed string consistency** - Uses exact speed strings defined in requirements ("1 Gbps", "10 Gbps", "25 Gbps")

### Task 6 Readiness
Function is now ready for Task 6 quick-add buttons. UI will call generatePortPreset with preset name and receive ready-to-use PortDefinition[] array for bulk port configuration.
- [Sun Mar 15 19:43:26 CET 2026] Added port configuration editor to equipment detail dialog for network map (only visible for reseau, switch, router, access_point). Includes preset functionality overriding current state after confirmation dialog, inline port additions with auto-computed index and slugified ID, and integration with equipementsApi.update. Reused shadcn UI table and select components to match project styling.

- 2026-03-15T19:43:34+01:00: Task 7 - DetailedEquipmentNode needs React Flow Handles placed smartly and invisible with zero size (`!w-1 !h-1 opacity-0`) over CSS grid elements to support multiple port connections per node, keeping the layout purely controlled by CSS instead of messy absolute handle positioning.

## [2026-03-15T19:56:00Z] Task: T6, T7, T8 - Atlas Verification

### Verification Completed
Atlas orchestrator performed Phase 1-4 verification on T6, T7, T8 completed by Sisyphus-Junior subagents.

**Phase 1: Automated**
- TypeScript: `tsc --noEmit` exits 0 ✅
- Anti-patterns: No TODO/FIXME/@ts-ignore/as-any ✅

**Phase 2: Manual Code Review**
- Read ALL 515 lines of changes across port editor, DetailedEquipmentNode, and generatePortPreset
- Verified logic correctness against requirements
- All implementations follow established patterns

**Phase 3: Cross-Check**
- T6: Port editor with CRUD, presets, confirmation dialog ✅
- T7: Custom React Flow node with port grid, dual Handles, connected highlighting ✅
- T8: Preset generator with 4 presets, auto ID/name generation ✅

**Phase 4: Boulder State**
- Plan checkboxes updated: T6, T7, T8 marked complete
- Progress: 8/17 tasks (47%)
- Ready for Wave 2 commits

### Wave 2 Summary (100% Complete)
- T3: Export utility functions (exportDiagramPng, exportDiagramSvg)
- T4: Site topology export buttons
- T5: Multi-site overview export buttons
- T6: Port configuration editor (state, handlers, UI)
- T7: DetailedEquipmentNode custom React Flow node
- T8: generatePortPreset function (4 presets)

**Commits Planned**:
1. Commit 3: T3+T4+T5 - "feat(network-map): add export buttons to both diagram views"
2. Commit 4: T6+T7+T8 - "feat(network-map): add port editor and detailed equipment node"

