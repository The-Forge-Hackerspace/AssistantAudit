# Draft: Diagram Export + Detailed Equipment View

## Requirements (confirmed)
- User wants diagram export (image/PDF) for client deliverables
- User wants a detailed equipment view showing physical port layout
- Port-level linking: when creating a link, choose specific ports instead of just equipment

## Technical Decisions
- (pending research results)

## Research Findings
- (3 agents launched: equipment model, ReactFlow export, librarian for export+hardware rendering)

## Open Questions

### Feature 1: Diagram Export
- Which formats? PNG, SVG, PDF?
- Export just the site view, overview, or both?
- Should export include a title/legend?

### Feature 2: Detailed Equipment View
- How to define port templates per equipment type/model?
- Where does the detailed view appear? New tab? Click on equipment?
- Should ports be defined globally per model or per individual equipment?
- What equipment types need port rendering? (switch, router, firewall, all?)

## Scope Boundaries
- INCLUDE: (TBD)
- EXCLUDE: (TBD)
