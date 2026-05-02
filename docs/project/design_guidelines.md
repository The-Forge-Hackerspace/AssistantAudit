# Design Guidelines — AssistantAudit (Frontend)

<!-- SCOPE: Design system frontend Next.js + shadcn/ui : routes, composants, tokens, WCAG 2.1. -->
<!-- DOC_KIND: explanation -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu touches au frontend, ajoutes un composant ou une route. -->
<!-- SKIP_WHEN: Tu cherches l'API REST ou les exigences fonctionnelles. -->
<!-- PRIMARY_SOURCES: frontend/src/app/, frontend/src/components/, frontend/components.json, frontend/eslint.config.mjs -->

## Quick Navigation

- [Stack frontend](#stack-frontend)
- [Architecture frontend](#architecture-frontend)
- [Routes Next.js App Router](#routes-next-js-app-router)
- [Primitives UI (`components/ui/`)](#primitives-ui-components-ui)
- [Composants métier (`components/`)](#composants-m-tier-components)
- [Tokens et thème (`globals.css`)](#tokens-et-th-me-globals-css)
- [Spacing et typographie](#spacing-et-typographie)
- [Configuration shadcn (`components.json`)](#configuration-shadcn-components-json)
- [Formulaires](#formulaires)
- [Data fetching](#data-fetching)
- [WCAG 2.1 — niveau AA cible](#wcag-2-1-niveau-aa-cible)
- [Conventions code TypeScript](#conventions-code-typescript)
- [Lint et build](#lint-et-build)
- [Maintenance](#maintenance)

**SCOPE :** Système de design et lignes directrices UI du frontend Next.js d'AssistantAudit. Couvre la stack, l'architecture App Router, l'inventaire des routes, les primitives shadcn/ui, les composants métier, les tokens de thème (`globals.css`), les patterns formulaires/data-fetching, la conformité **WCAG 2.1 niveau AA** et les conventions TypeScript/lint. Cible auditeurs UI, contributeurs frontend et reviewers `ln-401` / `ln-402`.

## Agent Entry

Quand lire ce document : Tu touches au frontend, ajoutes un composant ou une route.

Quand l'ignorer : Tu cherches l'API REST ou les exigences fonctionnelles.

Sources primaires (auto-discovery) : `frontend/src/app/, frontend/src/components/, frontend/components.json, frontend/eslint.config.mjs`

## Stack frontend

| Couche | Technologie | Version |
|---|---|---|
| Framework | Next.js (App Router) | 16.2.3 |
| Runtime UI | React + react-dom | 19.2.3 |
| Langage | TypeScript | 5 |
| Styling | Tailwind CSS | 4 |
| Composants | shadcn/ui (CLI shadcn) | 3.8.4 |
| Primitives | radix-ui | 1.4.3 |
| Animations | tw-animate-css | 1.4 |
| Icônes | lucide-react | 0.563 |
| Thème | next-themes | 0.4.6 |
| Formulaires | react-hook-form + @hookform/resolvers + zod | 7.72 / 5.2 / 4.3 |
| Data | axios + swr | 1.15 / 2.4 |
| Graphes | @xyflow/react + @dagrejs/dagre | 12.9 / 1.1 |
| Terminal | @xterm/xterm + addon-fit | 6.0 / 0.11 |
| Charts | recharts | 2.15 |
| Notifications | sonner | 2.0 |
| Export image | html-to-image | 1.11.11 |
| Lint | eslint + eslint-config-next | 9 / 16.1.6 |
| E2E | @playwright/test | 1.58.2 |

## Architecture frontend

Le frontend est organisé sous `frontend/src/` selon le pattern Next.js App Router (server + client components). `app/` héberge routes, layouts et `globals.css`. `components/` regroupe primitives `ui/` (shadcn) et composants métier (`checklists/`, `evaluation/`, `network-map/`, `tags/`). Les couches transverses sont : `contexts/auth-context` (état d'auth global), `hooks/{use-api,use-mobile,useNetworkMap}` (logique réutilisable), `lib/{api-client,constants,utils}` (axios + helpers), `services/api` (façade backend), `types/{api,index}` (types TypeScript). La rewrite `next.config.ts` proxie `/api/*` vers `BACKEND_INTERNAL_URL` au build, ce qui permet aux URLs relatives `/api/v1/*` de fonctionner sans CORS. Le `RootLayout` (`app/layout.tsx`) charge les polices Geist via `next/font/google` et délègue à `Providers` (auth, thème, SWR).

## Routes Next.js App Router

| Route | Page (`frontend/src/app/...`) | Description |
|---|---|---|
| `/` | `page.tsx` | Page d'accueil (redirection ou dashboard). |
| `/login` | `login/page.tsx` | Authentification (form react-hook-form + zod). |
| `/agents` | `agents/page.tsx` | Inventaire et statut des agents collecte mTLS. |
| `/audits` | `audits/page.tsx` | Liste des audits (campagnes, audits, rapports en onglets). |
| `/audits/evaluation` | `audits/evaluation/page.tsx` | Vue d'évaluation transverse (assessments + findings). |
| `/audits/[id]/checklists` | `audits/[id]/checklists/page.tsx` | Saisie des checklists ANSSI/CIS d'un audit. |
| `/audits/[id]/synthese` | `audits/[id]/synthese/page.tsx` | Synthèse d'audit (recommandations, plan). |
| `/entreprises` | `entreprises/page.tsx` | CRUD entreprises (multi-tenant). |
| `/sites` | `sites/page.tsx` | CRUD sites rattachés aux entreprises. |
| `/equipements` | `equipements/page.tsx` | Inventaire équipements (formulaire + détail). |
| `/frameworks` | `frameworks/page.tsx` | Référentiels YAML synchronisés (CIS, ANSSI, ...). |
| `/utilisateurs` | `utilisateurs/page.tsx` | Gestion utilisateurs (RBAC). |
| `/profile` | `profile/page.tsx` | Profil utilisateur courant. |
| `/outils` | `outils/page.tsx` | Tableau de bord des outils d'audit. |
| `/outils/ad-auditor` | `outils/ad-auditor/page.tsx` | Audit Active Directory (formulaire + résultats). |
| `/outils/collecte` | `outils/collecte/page.tsx` | Pipelines de collecte (form + détail + résultats). |
| `/outils/config-parser` | `outils/config-parser/page.tsx` | Analyse de configurations (Fortinet/OPNsense). |
| `/outils/monkey365` | `outils/monkey365/page.tsx` | Lancement Monkey365 + sortie xterm temps réel. |
| `/outils/network-map` | `outils/network-map/page.tsx` | Carte réseau interactive (xyflow + dagre). |
| `/outils/oradad` | `outils/oradad/page.tsx` | Collecte ORADAD + rapport ANSSI. |
| `/outils/scanner` | `outils/scanner/page.tsx` | Lancement de scans Nmap (dialog + détail tâche). |
| `/outils/ssl-checker` | `outils/ssl-checker/page.tsx` | Audit certificats TLS / chaînes. |

## Primitives UI (`components/ui/`)

| Primitive | Rôle |
|---|---|
| `accordion` | Sections pliantes (radix Accordion). |
| `alert` | Bandeau d'information / avertissement non bloquant. |
| `alert-dialog` | Dialogue de confirmation bloquant (radix AlertDialog). |
| `avatar` | Avatar utilisateur (image + fallback initiales). |
| `badge` | Étiquette de statut / catégorie. |
| `button` | Bouton standard avec variantes (default, destructive, outline, ghost, link). |
| `card` | Conteneur structuré (header/content/footer). |
| `chart` | Wrapper recharts (couleurs alignées sur tokens). |
| `checkbox` | Case à cocher accessible (radix Checkbox). |
| `dialog` | Modale (radix Dialog). |
| `dropdown-menu` | Menu déroulant (radix DropdownMenu). |
| `form` | Intégration react-hook-form + Field/Label/Description/Message. |
| `input` | Champ texte mono-ligne. |
| `label` | Libellé associé via `htmlFor` (radix Label). |
| `progress` | Barre de progression (déterminée ou indéterminée via keyframe). |
| `select` | Sélecteur (radix Select). |
| `separator` | Séparateur visuel (radix Separator). |
| `sheet` | Panneau latéral (drawer). |
| `sidebar` | Barre latérale de navigation (tokens `--sidebar-*`). |
| `skeleton` | Squelette de chargement. |
| `sonner` | Provider toasts sonner. |
| `switch` | Bascule on/off (radix Switch). |
| `table` | Composants de table sémantique. |
| `tabs` | Onglets (radix Tabs). |
| `textarea` | Champ texte multi-ligne. |
| `tooltip` | Info-bulle au survol/focus (radix Tooltip). |

## Composants métier (`components/`)

| Composant | Rôle |
|---|---|
| `app-layout` | Layout applicatif (sidebar + header). |
| `auth-guard` | Garde de route, redirige vers `/login` si non authentifié. |
| `skeletons` | Squelettes de chargement spécifiques (pages/listes). |
| `theme-toggle` | Bouton de bascule clair/sombre (next-themes). |
| `checklists/checklist-filler` | Saisie d'une checklist (questions + réponses). |
| `checklists/checklist-item-row` | Ligne d'item de checklist (statut + commentaire + pièces jointes). |
| `checklists/checklist-progress` | Indicateur d'avancement de checklist. |
| `evaluation/attachment-section` | Gestion des pièces jointes pour une évaluation. |
| `network-map/ConnectionForm` | Formulaire de création/édition de connexion. |
| `network-map/EquipmentDetailDialog` | Détail d'un équipement de la carte. |
| `network-map/InlinePortEditor` | Édition inline d'un port. |
| `network-map/PortsEditor` | Liste éditable des ports d'un équipement. |
| `network-map/SiteConnectionDialog` | Dialogue de connexion inter-sites. |
| `network-map/TabsArea` | Onglets latéraux de la carte (équipements, VLAN, ...). |
| `network-map/Toolbar` | Barre d'outils (zoom, layout, export image). |
| `network-map/TopologyView` | Canevas xyflow + layout dagre. |
| `network-map/VlanEditor` | Édition des VLAN. |
| `tags/tag-badge` | Badge de tag coloré. |
| `tags/tag-filter` | Filtre multi-sélection de tags. |
| `tags/tag-selector` | Sélecteur de tags (création + recherche). |

## Tokens et thème (`globals.css`)

Le thème utilise des variables CSS au format **OKLCH** (espace perceptuellement uniforme), résolues par Tailwind v4 via le bloc `@theme inline`. Deux modes : `:root` (clair) et `.dark` (sombre, géré par next-themes).

| Token | Rôle | Clair (`:root`) | Sombre (`.dark`) |
|---|---|---|---|
| `--background` | Fond global | `oklch(1 0 0)` | `oklch(0.145 0 0)` |
| `--foreground` | Texte principal | `oklch(0.145 0 0)` | `oklch(0.985 0 0)` |
| `--card` / `--card-foreground` | Cartes | `oklch(1 0 0)` / `oklch(0.145 0 0)` | `oklch(0.205 0 0)` / `oklch(0.985 0 0)` |
| `--popover` / `--popover-foreground` | Popovers | identique card | identique card |
| `--primary` / `--primary-foreground` | Couleur primaire | `oklch(0.205 0 0)` / `oklch(0.985 0 0)` | `oklch(0.922 0 0)` / `oklch(0.205 0 0)` |
| `--secondary` / `--secondary-foreground` | Secondaire | `oklch(0.97 0 0)` / `oklch(0.205 0 0)` | `oklch(0.269 0 0)` / `oklch(0.985 0 0)` |
| `--muted` / `--muted-foreground` | Texte atténué | `oklch(0.97 0 0)` / `oklch(0.556 0 0)` | `oklch(0.269 0 0)` / `oklch(0.708 0 0)` |
| `--accent` / `--accent-foreground` | Accent (hover) | `oklch(0.97 0 0)` / `oklch(0.205 0 0)` | `oklch(0.269 0 0)` / `oklch(0.985 0 0)` |
| `--destructive` | Erreur / suppression | `oklch(0.577 0.245 27.325)` | `oklch(0.704 0.191 22.216)` |
| `--border` | Bordures | `oklch(0.922 0 0)` | `oklch(1 0 0 / 10%)` |
| `--input` | Champs | `oklch(0.922 0 0)` | `oklch(1 0 0 / 15%)` |
| `--ring` | Anneau de focus | `oklch(0.708 0 0)` | `oklch(0.556 0 0)` |
| `--chart-1` à `--chart-5` | Palette charts recharts | série pastel/vive | série désaturée |
| `--sidebar*` | Tokens dédiés sidebar | déclinaison clair | déclinaison sombre |
| `--radius` | Rayon de base | `0.625rem` | identique |
| `--font-sans` | Police sans-serif | `var(--font-geist-sans)` | identique |
| `--font-mono` | Police mono | `var(--font-geist-mono)` | identique |

Le rayon `--radius` produit l'échelle `--radius-sm` à `--radius-4xl` via `calc()`. Les surcharges `react-flow` et `chart-container` mappent les tokens du thème vers les variables internes de @xyflow/react et recharts.

## Spacing et typographie

| Domaine | Règle |
|---|---|
| Spacing | Échelle Tailwind par défaut (rem) ; pas de surcharge dans `@theme`. |
| Typographie | `font-sans` = Geist Sans (chargée via `next/font/google` dans `app/layout.tsx`). |
| Mono | `font-mono` = Geist Mono (mêmes conditions). |
| Antialiasing | `antialiased` appliqué globalement sur `<body>`. |
| Curseur | `--cursor-button: pointer` + règles CSS sur `button`, `[role=button]`, `a`, `[type=button|submit|reset]`, `select`, `summary`. |
| Lang HTML | `<html lang="fr" suppressHydrationWarning>` (UI francophone). |
| Dark mode | Variant Tailwind `@custom-variant dark (&:is(.dark *))` ; classe `.dark` posée par next-themes. |

## Configuration shadcn (`components.json`)

| Clé | Valeur |
|---|---|
| `style` | `new-york` |
| `rsc` | `true` (React Server Components actifs) |
| `tsx` | `true` |
| `tailwind.css` | `src/app/globals.css` |
| `tailwind.baseColor` | `neutral` |
| `tailwind.cssVariables` | `true` |
| `iconLibrary` | `lucide` |
| `aliases.components` | `@/components` |
| `aliases.utils` | `@/lib/utils` |
| `aliases.ui` | `@/components/ui` |
| `aliases.lib` | `@/lib` |
| `aliases.hooks` | `@/hooks` |

## Formulaires

| Brique | Rôle |
|---|---|
| `react-hook-form` | Source de vérité de l'état du formulaire (uncontrolled refs). |
| `@hookform/resolvers/zod` | Adaptateur de schéma de validation. |
| `zod` | Schémas typés (miroir client des Pydantic backend). |
| `components/ui/form` | Wrappers `Form`, `FormField`, `FormItem`, `FormLabel`, `FormControl`, `FormDescription`, `FormMessage`. |
| `components/ui/{input,textarea,select,checkbox,switch}` | Champs accessibles (radix). |
| Erreurs | Affichées via `FormMessage` lié par `aria-describedby`. |
| Soumission | Mutation via `services/api` (axios) ; toast `sonner` pour succès/erreur. |

## Data fetching

| Cas | Mécanisme |
|---|---|
| Lecture (GET) | SWR via `hooks/use-api` ; clés stables, revalidation au focus. |
| Mutation (POST/PUT/PATCH/DELETE) | axios direct via `lib/api-client` ; revalidation manuelle SWR (`mutate`). |
| Authentification | Cookies httpOnly + intercepteur axios ; `auth-context` propage l'utilisateur. |
| WebSocket | Connexion native `WebSocket` (logs agents, Monkey365, scans). |
| Cache | Mémoire SWR ; pas de persistance localStorage par défaut. |
| URLs | Toujours relatives (`/api/v1/...`) ; rewrite Next.js gère le routage en conteneur. |

## WCAG 2.1 — niveau AA cible

| Critère | Niveau | Application dans AssistantAudit |
|---|---|---|
| 1.1.1 Contenu non textuel | A | Icônes lucide-react décoratives marquées `aria-hidden`; icônes interactives accompagnées d'un `aria-label`. |
| 1.3.1 Information et relations | A | Tables sémantiques `components/ui/table` ; libellés associés via `<Label htmlFor>` (radix Label). |
| 1.4.3 Contraste (minimum) | AA | Tokens OKLCH calibrés clair/sombre ; contrastes vérifiés sur `--foreground`/`--background`, `--primary`/`--primary-foreground`, `--destructive`/`--background`. |
| 1.4.11 Contraste non textuel | AA | Bordures `--border` et anneau `--ring` distincts du fond ; états focus visibles. |
| 2.1.1 Clavier | A | Radix UI assure la navigation clavier sur Dialog, Popover, DropdownMenu, Tabs, Select, Accordion, Tooltip. |
| 2.4.3 Ordre du focus | A | DOM linéaire respecté ; pas de `tabIndex` positifs. |
| 2.4.7 Visibilité du focus | AA | `outline-ring/50` appliqué globalement (`@layer base` dans `globals.css`). |
| 3.2.2 À la saisie | A | Pas de soumission automatique ; formulaires explicites (bouton submit). |
| 3.3.1 Identification d'erreur | A | `FormMessage` annonce les erreurs ; toasts sonner pour erreurs serveur. |
| 3.3.2 Étiquettes et instructions | A | Tous les champs portent un `<Label>` ; placeholders ne remplacent pas le label. |
| 4.1.2 Nom, rôle, valeur | A | Primitives radix exposent rôles ARIA conformes (button, dialog, tablist, ...). |
| 4.1.3 Messages d'état | AA | Toasts sonner avec `role=status`/`role=alert` ; `Alert` pour bandeaux non bloquants. |

Points d'attention spécifiques : `<html lang="fr">` (3.1.1), `suppressHydrationWarning` ne masque que les divergences SSR/CSR (next-themes) et n'affecte pas l'accessibilité.

## Conventions code TypeScript

- TypeScript strict (cf `tsconfig.json` du projet) ; pas de `as any`, pas de `@ts-ignore`, pas de `@ts-expect-error` non motivé.
- Noms de fichiers en `kebab-case.tsx` (composants UI) ou `PascalCase.tsx` (composants metier complexes — pattern observé dans `network-map/`).
- Identifiers en anglais ; chaînes UI, commentaires et docstrings en français.
- ESLint étend `eslint-config-next/core-web-vitals` + `eslint-config-next/typescript` ; règle `react/no-unescaped-entities` rétrogradée en `warn` pour les apostrophes françaises.
- Imports absolus via alias `@/*` (composants, lib, hooks).
- Les composants client doivent porter `"use client"` ; par défaut, App Router rend en server component.
- Pas d'accès direct au DOM via `document.*` hors `useEffect` ; respecter SSR.

## Lint et build

| Commande (depuis `frontend/`) | Description |
|---|---|
| `npm install` | Installe les dépendances (lockfile `package-lock.json`). |
| `npm run dev` | Démarre Next.js en mode développement (Turbopack). |
| `npm run build` | Build de production (rewrite `/api/*` figée si `BACKEND_INTERNAL_URL` est posé). |
| `npm start` | Lance le serveur Next.js sur le build de production. |
| `npm run lint` | Exécute ESLint (config `eslint.config.mjs`). |

CI (`.github/workflows/ci.yml`) exécute lint + build frontend ; `playwright.yml` exécute les tests E2E (`tests/e2e/`).

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

- **Owner :** `ln-114-frontend-docs-creator` (création) ; mises à jour manuelles ou via re-run de la pipeline `documentation-pipeline`.
- **Sources de vérité :**
  - Stack : `frontend/package.json`.
  - Tokens et thème : `frontend/src/app/globals.css`.
  - Configuration shadcn : `frontend/components.json`.
  - Routes : `frontend/src/app/**/page.tsx`.
  - Primitives UI : `frontend/src/components/ui/`.
  - Composants métier : `frontend/src/components/{checklists,evaluation,network-map,tags}/`.
  - Layout racine : `frontend/src/app/layout.tsx`.
  - Build : `frontend/next.config.ts`.
  - Lint : `frontend/eslint.config.mjs`.
- **Mettre à jour quand :** ajout/suppression d'une route, ajout d'une primitive `ui/`, modification des tokens OKLCH, montée de version majeure (Next.js, React, Tailwind, shadcn, radix-ui), changement des polices ou du dark-mode.
- **Consommateurs aval :** `ln-401` (Frontend Guard) et `ln-402` (Frontend Review Checks) lisent ce document pour valider la conformité du runtime au design système.
- **Vérification rapide :** `npm run lint && npm run build` dans `frontend/` ; vérifier visuellement clair/sombre via `theme-toggle`.
