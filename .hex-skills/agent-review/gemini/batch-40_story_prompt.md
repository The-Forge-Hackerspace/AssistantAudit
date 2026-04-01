# Task: Review 40 User Stories Against Codebase

You are reviewing 40 validated User Stories for the AssistantAudit project — an IT security auditing platform (FastAPI backend, Next.js 16 frontend, SQLAlchemy 2 ORM).

## CRITICAL CONSTRAINTS
- DO NOT modify, create, or delete any PROJECT files
- This is a READ-ONLY analysis task
- DO NOT ask clarifying questions — proceed autonomously
- Target completing within 10 minutes. Prioritize depth over breadth.

## Project Context

AssistantAudit is an IT security auditing platform with:
- **Backend**: Python 3.13, FastAPI 0.135.1, SQLAlchemy 2.0.48, Alembic 1.18.4
- **Frontend**: Next.js 16.2.0, React 19.2.3, Tailwind CSS v4, shadcn/ui
- **Architecture**: Router -> Service -> Model (sync only, no async on routes/services except WebSocket)
- **Security**: AES-256-GCM encryption, JWT auth, bcrypt, mTLS for agents
- **Tools**: Nmap, SSH/WinRM collectors, AD auditor, Monkey365, ORADAD
- **Database**: SQLite (dev), PostgreSQL 16 (prod), 36+ tables, 31 Alembic migrations

## Stories to Review (Linear Issues TOS-5 through TOS-44)

### Epic 1: Infrastructure & DevOps
- TOS-5: US001 — Pipeline CI/CD complete (P0, 13pts)
- TOS-6: US002 — Durcissement Docker production (P0, 8pts)
- TOS-7: US003 — Logging structure & monitoring (P1, 13pts)
- TOS-8: US004 — Gestion centralisee des secrets (P0, 8pts)
- TOS-9: US005 — Migration SQLite vers PostgreSQL (P2, 13pts)
- TOS-10: US006 — Gestion certificats mTLS agents (P3, 13pts)
- TOS-11: US007 — Hardening securite & rate limiting (P0, 8pts)

### Epic 2: Collecte automatisee & Agents
- TOS-12: US008 — Fiabilisation WebSocket agents (P1, 13pts)
- TOS-13: US009 — Pipeline de collecte multi-etapes (P1, 13pts)
- TOS-14: US010 — Retry et scheduling des taches agents (P2, 8pts)
- TOS-15: US011 — Auto-prefill evaluation depuis Nmap (P1, 8pts)
- TOS-16: US012 — Securisation WinRM et validation certificats (P1, 8pts)
- TOS-17: US013 — Administration agents depuis l'interface (P2, 13pts)
- TOS-18: US014 — Integration Monkey365 bout-en-bout (P2, 8pts)

### Epic 3: Referentiels & Evaluation
- TOS-19: US015 — Moteur d'evaluation automatique (P1, 13pts)
- TOS-20: US016 — Editeur de referentiels web avance (P2, 13pts)
- TOS-21: US017 — Scoring de conformite multi-niveaux (P1, 8pts)
- TOS-22: US018 — Coherence YAML-DB bidirectionnelle (P2, 8pts)
- TOS-23: US019 — Import/export de campagnes d'evaluation (P2, 8pts)
- TOS-24: US020 — Checklists personnalisees depuis l'interface (P2, 8pts)

### Epic 4: Rapports & Livrables
- TOS-25: US021 — Generation PDF sections 5-8 (P0, 13pts)
- TOS-26: US022 — Matrice de conformite visuelle (P1, 8pts)
- TOS-27: US023 — Export multi-format des donnees d'audit (P2, 8pts)
- TOS-28: US024 — Personnalisation des rapports PDF (P3, 8pts)
- TOS-29: US025 — Synthese executive automatique (P0, 8pts)

### Epic 5: Interface web & Visualisation
- TOS-30: US026 — Dashboard interactif & drill-down (P1, 13pts)
- TOS-31: US027 — Centre de notifications temps reel (P2, 13pts)
- TOS-32: US028 — Recherche globale & filtres avances (P1, 8pts)
- TOS-33: US029 — Accessibilite RGAA & UX mobile (P1, 8pts)
- TOS-34: US030 — Export visualisations & rapports interactifs (P2, 8pts)

### Epic 6: Remediation & Suivi
- TOS-35: US031 — Modele Finding & cycle de vie (P0, 13pts)
- TOS-36: US032 — Plans de remediation & actions correctives (P1, 13pts)
- TOS-37: US033 — Registre des risques & matrice (P1, 8pts)
- TOS-38: US034 — Suivi de conformite & tendances (P1, 8pts)
- TOS-39: US035 — Re-audit & comparaison inter-iterations (P2, 13pts)

### Epic 7: IA & Automatisation avancee
- TOS-40: US036 — Integration LLM & service IA central (P1, 13pts)
- TOS-41: US037 — Mapping semantique des controles (P1, 13pts)
- TOS-42: US038 — Generation narrative automatique des rapports (P1, 8pts)
- TOS-43: US039 — Guidance de remediation intelligente (P2, 8pts)
- TOS-44: US040 — Agregation multi-sources & priorisation des findings (P2, 13pts)

## Review Goal

Validate that the 40 stories are **technically feasible** given the current codebase, that they **reference correct files/modules/patterns**, and identify any **missing considerations** (security, performance, edge cases, dependencies).

Focus on:
1. **Codebase alignment**: Do stories reference files/modules that actually exist? Are the patterns described accurate?
2. **Technical feasibility**: Can the proposed implementations work with the current architecture?
3. **Library versions**: Are the library versions mentioned current and compatible?
4. **Missing risks**: Any production edge cases, breaking changes, or failure modes not covered?
5. **Cross-story conflicts**: Any overlapping scope or conflicting approaches between stories?

## Instructions

1. Examine the codebase structure: `backend/app/` (models, services, api, tools, core), `frontend/src/` (app, components)
2. Check key files: `backend/requirements.txt`, `frontend/package.json`, `Dockerfile`, `docker-compose.yml`
3. Cross-reference story claims against actual code
4. Search the web for current best practices (2025-2026) for key technical decisions
5. Report findings with specific file paths and line references

## Output Format

Write a structured review report in markdown, ending with a JSON block.

### Report Structure

```
# Review Report

## Goal
What specific question this review answers.

## Analysis Process
What files examined, what patterns checked, what research conducted.

## Findings

### 1. {Finding title}
- **Story:** TOS-{N}
- **Area:** security | performance | architecture | feasibility | best_practices | risk_analysis
- **Issue:** What is wrong or could be improved
- **Evidence:** Standards, code patterns supporting this finding
- **Suggestion:** Specific change to Story or Tasks
- **Confidence:** {N}% | **Impact:** {N}%

## Verdict
STORY_ACCEPTABLE | SUGGESTIONS

## Structured Data
{JSON block with verdict and suggestions array}
```

Focus on HIGH-IMPACT findings only. Skip cosmetic or low-value issues.
