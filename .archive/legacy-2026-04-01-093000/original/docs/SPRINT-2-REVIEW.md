# SPRINT-2-REVIEW — Review complète Sprint 2

**Date** : 2026-03-31
**Reviewer** : Claude Code (planificateur)
**Steps couverts** : 30 → 36 (7 steps)
**Verdict** : ⚠️ **GO Sprint 3 avec 1 bug bloquant à corriger en priorité**

---

## Résumé exécutif

Le Sprint 2 livre les rapports PDF v1 (modèle + templates + API + génération), les 3 seeds checklists manquantes, les composants frontend checklists et tags, et les champs d'intervention sur le modèle Audit. Le code est solide : 663/664 tests unitaires passent, le build TypeScript est propre, et toutes les contraintes §1.5 sont respectées.

**1 bug bloquant** : le Dockerfile ne contient pas les dépendances système WeasyPrint (libgobject, libcairo, libpango). Le backend ne démarre pas dans Docker. À corriger avant de livrer en production ou de tester l'API via Docker.

---

## Phase 1 — Review de code

### Step 30 — Rapport : modèle + dépendances ✅

| Critère | Statut | Note |
|---------|--------|------|
| WeasyPrint, python-docx, Jinja2 dans requirements.txt | ✅ | Versions fixées |
| Modèle `AuditReport` avec 25 sections | ✅ | `REPORT_SECTIONS` = 25 items, ordre correct |
| Modèle `ReportSection` avec unicité section_key/rapport | ✅ | Contrainte `uq_report_section_key` |
| Schemas Pydantic (Create/Read/Detail/Update/GenerateRequest) | ✅ | 5 schemas conformes |
| Migration Alembic `a11a330219bb` | ✅ | Tables `audit_reports`, `report_sections` |
| Tests TDD : 8 tests passent | ✅ | `pytest tests/test_report_models.py` : 8/8 |
| Conformité §1.5 : sync only, 404 pas 403 | ✅ | Pas de `async def` dans le modèle |

**Note** : La migration a été réécrite manuellement pour exclure le drift (FK non liée) — bonne pratique.

---

### Step 31 — Template Jinja2 + ReportService (render_html) ✅

| Critère | Statut | Note |
|---------|--------|------|
| `report_base.html` — itère 25 sections conditionnellement | ✅ | `{% if section.included %}` correct |
| `styles.css` — print A4, `@page`, en-têtes, pieds | ✅ | WeasyPrint-compatible |
| `macros.html` — macros réutilisables | ✅ | Tableau, checklist, placeholder |
| `sections/cover.html` — logos base64, metadata | ✅ | Logos inline, pas de dépendance externe |
| Sections 2-4 HTML présentes | ✅ | introduction, objectives, scope |
| `_placeholder.html` pour sections 5-25 | ✅ | `ignore missing` dans base template |
| `ReportService.create_report()` + `render_html()` | ✅ | Ownership check 404, sync only |
| Tests TDD : 5 tests passent | ✅ | `pytest tests/test_report_template.py` : 5/5 |
| Logo base64 inline (pas d'URL externe) | ✅ | `_load_logo_base64()` encode en base64 |

**Sécurité** : Le template utilise `| safe` sur `custom_content` et `audit.objectifs`. À surveiller si ces champs acceptent du HTML utilisateur — risque XSS si l'input n'est pas sanitisé côté backend. **Note pour Sprint 3** : ajouter sanitisation HTML avant d'injecter `| safe`.

---

### Step 32 — Générateur PDF + Routes API ✅

| Critère | Statut | Note |
|---------|--------|------|
| `generate_pdf()` via WeasyPrint | ✅ | Stocke dans `DATA_DIR/reports/`, status → ready |
| 7 routes API : POST, GET, PUT, POST/generate, GET/download, DELETE | ✅ | Toutes enregistrées dans router.py |
| `FileResponse` pour le téléchargement PDF | ✅ | `content-type: application/pdf` |
| Isolation : 404 pour un autre utilisateur | ✅ | `_check_audit_access()` sur audit parent |
| Tests TDD : 9 tests (8/9 passent localement) | ⚠️ | 1 erreur : sentry_sdk incompatible Python 3.14 (env) |
| `update_section()` — inclure/exclure section | ✅ | PATCH fields via `model_dump(exclude_unset=True)` |

**Bug Docker** : `generate_pdf()` appelle WeasyPrint qui nécessite `libgobject-2.0` manquant dans le Dockerfile → crash backend. Voir BUG-S2-001.

---

### Step 33 — Seeds checklists (salle serveur + documentation + départ) ✅

| Critère | Statut | Note |
|---------|--------|------|
| `seed_checklist_server_room.py` — 7 sections, 38 items | ✅ | Catégorie `server_room`, ref 1.1→7.5 |
| `seed_checklist_documentation.py` — 5 sections, 22 items | ✅ | Catégorie `documentation` |
| `seed_checklist_departure.py` — 5 sections, 18 items | ✅ | Catégorie `departure` |
| Scripts idempotents | ✅ | `seed(db)` accepte un db optionnel pour tests |
| Conformité brief §6.13, §6.16, §4.3 | ✅ | Contenu fidèle aux sections du brief |
| Tests TDD : 6 tests passent | ✅ | Structure, items, idempotence |

Avec le sprint 1 (LAN), les 4 checklists du brief sont maintenant en base :

| Template | Catégorie | Sections | Items |
|---------|-----------|----------|-------|
| Checklist LAN | `lan` | 9 | 45 |
| Salle serveur | `server_room` | 7 | 38 |
| Documentation | `documentation` | 5 | 22 |
| Protocole départ | `departure` | 5 | 18 |

---

### Step 34 — Frontend Checklist Filler (mode tablette) ✅

| Critère | Statut | Note |
|---------|--------|------|
| Page `/audits/[id]/checklists` | ✅ | Route `ƒ` (dynamic) dans le build |
| `ChecklistFiller` — Accordion sections | ✅ | shadcn Accordion |
| `ChecklistItemRow` — 4 boutons ≥48px (OK/NOK/NA/?) | ✅ | `min-h-[48px]` touch-friendly |
| `ChecklistProgress` — barre de progression | ✅ | Compteurs OK/NOK/NA |
| `checklistsApi` — 8 méthodes API | ✅ | Templates, instances, réponses, progression |
| Types TypeScript — 7 interfaces | ✅ | Template, Section, Item, Instance, Response, Progress, Detail |
| `npm run build` sans erreur | ✅ | 23 pages compilées |
| Notes sauvegardées via `onBlur` | ✅ | Appel `respondToItem()` au blur |

---

### Step 35 — Frontend Tags (badge + selector + filtre multi-tag) ✅

| Critère | Statut | Note |
|---------|--------|------|
| `TagBadge` — badge coloré hex, prop onRemove | ✅ | Couleur en fond + texte, tailles sm/md |
| `TagSelector` — chargement + association + dissociation | ✅ | Dropdown shadcn, icône × |
| `TagFilter` — badges cliquables, bouton "Effacer" | ✅ | Toggle actif/inactif, callback `onFilterChange` |
| `tagsApi` — 7 méthodes (list, create, update, remove, associate, dissociate, getEntityTags) | ✅ | Conforme aux routes backend |
| Intégration dans page équipements | ✅ | `tagFilter` state passé au TagFilter |
| `npm run build` sans erreur | ✅ | Build propre |

**Manque** : `TagSelector` n'est pas encore intégré dans les pages (équipements, findings). Seulement `TagFilter` sur équipements. Normal pour Sprint 2 (intégration complète Sprint 3+).

---

### Step 36 — Champs intervention Audit ✅

| Critère | Statut | Note |
|---------|--------|------|
| 11 colonnes ajoutées au modèle `Audit` | ✅ | `client_contact_name`, `client_contact_title`, `client_contact_email`, `client_contact_phone`, `access_level`, `access_missing_details`, `intervention_window`, `intervention_constraints`, `scope_covered`, `scope_excluded`, `audit_type` + `date_fin` |
| Migration Alembic `fee3cc8b8c35` | ✅ | Colonnes nullable, rétro-compatible |
| Schemas `AuditCreate`, `AuditUpdate`, `AuditRead` mis à jour | ✅ | Validation pattern sur `access_level`, `audit_type` |
| Template `scope.html` utilise les nouveaux champs | ✅ | Type d'audit, fenêtre d'intervention, périmètre couvert/exclu |
| Colonnes existantes préservées (`nom_projet`, etc.) | ✅ | Conforme §1.5 décision 2 |
| Tests TDD : 5/5 passent (hors erreur sentry env) | ✅ | `pytest tests/test_audit_intervention.py` |

**Note** : L'interface frontend pour la fiche d'intervention n'est pas encore créée (prévu Sprint 3).

---

## Phase 2 — Tests Docker

### Services

```
docker compose ps (2026-03-31)

SERVICE    STATUS
db         Up (healthy)     — PostgreSQL 16-alpine OK ✅
frontend   Up               — Next.js 3000 OK ✅
backend    Restarting (1)   — CRASH WeasyPrint ❌
```

**Migrations** : Les migrations Alembic ont été exécutées avec succès avant le crash WeasyPrint :
```
[OK] alembic upgrade head
```

### Raison du crash backend

```
OSError: cannot load library 'libgobject-2.0-0'
from weasyprint.text.ffi import ffi → dlopen('libgobject-2.0-0')
```

**Cause** : Dockerfile manque les libs système Cairo/Pango/GObject → BUG-S2-001.

### Test frontend HTTP

```
GET http://localhost:3000 → 200 OK ✅
HTML contient "AssistantAudit" ✅
Title: AssistantAudit ✅
```

---

## Phase 3 — Tests API

**Résultat** : Tests API non exécutables en Docker (backend down).

**Tests locaux (pytest avec SQLite)** :

```
pytest tests/test_report_api.py        : 8/9 passent (1 erreur sentry env)
pytest tests/test_audit_intervention.py : 5/5 passent
pytest tests/ (complet, hors websocket/health/sentry) : 663/664 passent
```

Le 1 error restant (`test_admin_sees_all_audits`) est le même problème Python 3.14 + sentry_sdk + eventlet, pré-existant à Sprint 2. **Pas un bug de code Sprint 2.**

---

## Phase 4 — Tests Playwright

### Infrastructure de test créée

Fichiers créés dans `tests/e2e/` :
- `test-checklists.spec.ts` — 4 tests checklists + tablette
- `test-tags.spec.ts` — 3 tests tags + responsive
- `test-reports.spec.ts` — 3 tests rapports (avec skip si backend down)
- `test-responsive.spec.ts` — 6 tests layout tablette multi-pages

### Résultats Playwright (Chromium)

```
Total : 16 tests
Passent : 11 ✅
Échouent : 4 ❌
Skippés : 1 ⏭
```

**Tests passants** :
- ✅ Frontend charge (titre "AssistantAudit")
- ✅ Redirect `/login` quand non authentifié
- ✅ Pas de scroll horizontal sur toutes les pages testées (desktop + tablette 768x1024)
- ✅ Pages `/`, `/login`, `/audits`, `/equipements`, `/audits/1/checklists` sans overflow
- ✅ API health check skip (backend down, test s'auto-skip correctement)

**Tests échouants** (cause unique : backend down) :
- ❌ `Page checklists est accessible après login` — formulaire login non rendu (backend down)
- ❌ `Page de génération rapport visible (frontend)` — même cause
- ❌ `Composant TagFilter présent dans équipements (après login)` — même cause
- ❌ `API health check backend` — `http://localhost:8000/health` → connection refused

**Cause commune** : BUG-S2-001 — Le backend crashe dans Docker → le frontend ne peut pas authentifier les utilisateurs.

### Screenshots capturés

Disponibles dans `playwright-results/` :
- `login-page.png` — page login (spinner, pas de formulaire → backend down)
- `tablet-login.png` / `tablet-home.png` — layouts tablette OK
- `equipements-page.png` — redirect vers login OK

---

## Bugs trouvés

### BUG-S2-001 — Dockerfile : dépendances système WeasyPrint manquantes ❌ BLOQUANT

- **Fichier** : `Dockerfile`
- **Sévérité** : Bloquante (backend ne démarre pas en Docker)
- **Fix** : Ajouter dans le bloc `apt-get install` :
  ```dockerfile
  libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info
  ```
- **Détail** : `bugs/open/BUG-S2-001-dockerfile-weasyprint-deps.md`

### NOTE-S2-001 — XSS potentiel dans templates rapport

- **Fichier** : `backend/app/templates/reports/` (sections objectives.html, scope.html, introduction.html)
- **Sévérité** : Faible (les champs concernés sont `audit.objectifs`, `audit.limites`, `report.consultant_contact` — saisis par l'auditeur authentifié, pas par un utilisateur anonyme)
- **Observation** : `{{ audit.objectifs | safe }}` injecte du HTML non sanitisé. Si un attaquant compromet un compte auditeur, il peut injecter du HTML dans le PDF.
- **Recommandation** : Ajouter bleach/markupsafe pour sanitiser le HTML avant rendu dans les templates rapport (Sprint 3+).

---

## Impact sur le Sprint 3

### À corriger avant Sprint 3

1. **BUG-S2-001** — Ajouter libs WeasyPrint dans Dockerfile (quick-win, ~5 min) — BLOCKER pour toute demo en Docker

### Nouvelles dettes techniques détectées

1. `| safe` sans sanitisation HTML dans templates rapport → ajouter à `backlog/tech-debt.md`
2. `TagSelector` pas encore intégré dans les pages de détail équipements/findings
3. Interface frontend pour la fiche d'intervention Audit (champs step 36) non créée

### Sprint 3 peut démarrer sur

- Sections rapport 5-25 (équipements, AD, sauvegardes, M365, synthèse...) — brief §7.7
- Frontend fiche intervention (form edit audit avec champs step 36)
- Intégration TagSelector dans les détails d'entités
- Fix Dockerfile (BUG-S2-001) — premier commit Sprint 3

---

## Conformité brief + architecture

| Règle §1.5 | Vérifié | Résultat |
|-----------|---------|----------|
| Sync only (pas async def routes/services) | ✅ | report_service.py, reports.py — sync |
| 404 pas 403 pour ownership | ✅ | `_check_audit_access()` → 404 si not owner |
| owner_id filtré dans chaque query service | ✅ | Via audit parent dans all report endpoints |
| Colonnes existantes préservées | ✅ | Audit : `nom_projet`, `objectifs`, etc. inchangés |
| Pas de migration avec drift non lié | ✅ | Migration report réécrite manuellement |

| Brief §7.7 (rapports) | Statut |
|----------------------|--------|
| 25 sections définies (`REPORT_SECTIONS`) | ✅ |
| Sections 1-4 avec données réelles | ✅ |
| Sections 5-25 placeholder | ✅ (`_placeholder.html`) |
| Génération PDF (WeasyPrint) | ✅ (fonctionne hors Docker) |
| Branding : logos consultant/client | ✅ (base64 inline) |

| Brief §4.2-4.3 (checklists) | Statut |
|-----------------------------|--------|
| 4 templates : LAN + salle serveur + documentation + départ | ✅ |
| Frontend remplissage terrain (mode tablette) | ✅ |
| Items OK/NOK/NA/UNCHECKED + note | ✅ |

| Brief §5 (tags) | Statut |
|-----------------|--------|
| 8 tags prédéfinis | ✅ (depuis Sprint 1) |
| Badges colorés | ✅ (TagBadge) |
| Filtrage multi-tag | ✅ (TagFilter, intégré équipements) |

---

## Verdict : **GO SPRINT 3** ⚠️ (1 bug bloquant à corriger en premier commit)

- Code Sprint 2 : conforme architecture + brief
- Tests backend : 663/664 (le 1 error est env Python 3.14, pré-existant)
- Frontend build : propre, 23 pages
- Docker : frontend OK, backend KO (BUG-S2-001 — quick-win)
- **Action immédiate** : Corriger Dockerfile (BUG-S2-001) avant tout test Docker Sprint 3
