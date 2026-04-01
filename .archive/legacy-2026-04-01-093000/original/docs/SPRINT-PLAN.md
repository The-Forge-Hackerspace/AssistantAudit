# Plan de sprints AssistantAudit

**Date** : 2026-03-30
**Source** : `BACKLOG.md` + `AUDIT-ETAT-DES-LIEUX.md`

---

## Principes de planification

1. **Sprint 1 = sécurité + fondations** — pas de nouvelles features tant que les bases ne sont pas solides
2. **Chaque sprint livre quelque chose de testable** end-to-end
3. **Un step = une tâche ciblée** (3-4 fichiers max, cf. leçon apprise #1)
4. **Dépendances inter-repos** explicites : si l'agent doit faire X avant que le serveur puisse Y
5. **Ordre : backend → frontend** — les routes API existent avant l'UI

---

## Sprint 1 — Fondations & sécurité (2 semaines)

**Focus** : Corriger les failles restantes, poser les briques réutilisées partout (tags, checklists modèles), Docker

### Tâches

| ID | Titre | Repo | Taille | Step |
|---|---|---|---|---|
| TD-022 | Fix `ScanReseau.owner_id` nullable | server | S | steps-21-server.md |
| TD-023 | Authentifier endpoint `/metrics` | server | S | steps-21-server.md |
| TD-009 | Backfill `owner_id` nullable | server | S | steps-21-server.md |
| TD-020 | Frontend refresh token avant 401 redirect | server | S | steps-22-server.md |
| TD-002 | Implémenter `rotate_kek.py` | server | M | steps-23-server.md |
| TAG-001 | Modèle Tag + table liaison polymorphe | server | M | steps-24-server.md |
| TAG-002 | Service tags (CRUD, association, filtrage) | server | S | steps-24-server.md |
| TAG-003 | Routes API tags | server | S | steps-25-server.md |
| TAG-004 | Seed tags prédéfinis | server | S | steps-25-server.md |
| CK-001 | Modèles checklist (template, item, response) | server | M | steps-26-server.md |
| CK-002 | Service checklist | server | M | steps-27-server.md |
| CK-003 | Routes API checklists | server | M | steps-28-server.md |
| CK-004 | Seed checklist LAN | server | S | steps-28-server.md |
| TD-025 | Dockerfile + docker-compose.yml | server | M | steps-29-server.md |

### Critère de succès
- [ ] Aucune faille sécurité ouverte P0/P1
- [ ] API tags fonctionnelle : CRUD + association + filtrage
- [ ] API checklists fonctionnelle : templates + réponses + preuves
- [ ] Checklist LAN prédéfinie chargée
- [ ] `docker-compose up` lance le serveur complet
- [ ] Tous les tests passent

### Dépendances inter-repos
Aucune — sprint 100% serveur.

---

## Sprint 2 — Rapports v1 & checklists frontend (2 semaines)

**Focus** : La fonctionnalité la plus critique : générer un rapport PDF. + UI checklists.

### Tâches

| ID | Titre | Repo | Taille | Step |
|---|---|---|---|---|
| RPT-001 | Dépendances rapport (WeasyPrint, python-docx, Jinja2) | server | S | steps-30-server.md |
| RPT-002 | Modèle de données rapport (25 sections, metadata) | server | M | steps-30-server.md |
| RPT-003 | Template PDF rapport complet (brandable) | server | L | steps-31-server.md |
| RPT-004 | Générateur PDF sections 1-4 (page de garde → périmètre) | server | M | steps-32-server.md |
| RPT-012 | Routes API génération rapport | server | S | steps-32-server.md |
| CK-005 | Seed checklist salle serveur | server | S | steps-33-server.md |
| CK-006 | Seed checklist documentation | server | S | steps-33-server.md |
| CK-007 | Seed checklist protocole départ | server | S | steps-33-server.md |
| CK-008 | Frontend composant checklist (mode tablette) | server | L | steps-34-server.md |
| TAG-005 | Frontend badge tag + filtre multi-tag | server | M | steps-35-server.md |
| CK-009 | Enrichir modèle Audit : champs intervention | server | S | steps-36-server.md |

### Critère de succès
- [ ] Rapport PDF généré avec sections 1-4 (page de garde, intro, objectifs, périmètre)
- [ ] Logo consultant/client dans le rapport
- [ ] Checklists remplissables dans le frontend (tablette-friendly)
- [ ] Tags affichés et filtrables dans les listes
- [ ] 3 checklists supplémentaires prédéfinies

### Dépendances inter-repos
Aucune — sprint 100% serveur.

---

## Sprint 3 — Rapports sections 5-16 & AD complet (2 semaines)

**Focus** : Enrichir le rapport avec les sections techniques. Script AD complet côté agent.

### Tâches

| ID | Titre | Repo | Taille | Step |
|---|---|---|---|---|
| RPT-005 | Générateur PDF sections 5-9 (lieux, synoptique, locaux, onduleurs, internet) | server | L | steps-37-server.md + steps-38-server.md |
| RPT-006 | Générateur PDF sections 10-16 (IP, switches, Wi-Fi, FW, serveurs, NAS, AD) | server | L | steps-39-server.md + steps-40-server.md |
| AD-001 | Script PowerShell AD complet | agent | L | steps-06-agent.md |
| AD-004 | Parsing structuré résultats AD côté serveur | server | M | steps-41-server.md |
| AD-002 | Script PowerShell DCDIAG + GPO + DNS + DHCP | agent | L | steps-07-agent.md |

### Critère de succès
- [ ] Rapport PDF sections 1-16 générées
- [ ] Script AD agent collecte : OU, comptes, groupes admin, MDP policies
- [ ] Résultats AD parsés et stockés de manière structurée côté serveur
- [ ] Tests agent AD passent

### Dépendances inter-repos
- `AD-001` (agent) doit être terminé AVANT `AD-004` (serveur)
- Le format de sortie JSON du script AD doit être défini dans le step agent

---

## Sprint 4 — Rapports sections 17-25 & export Word (2 semaines)

**Focus** : Terminer le générateur de rapport complet. Export Word.

### Tâches

| ID | Titre | Repo | Taille | Step |
|---|---|---|---|---|
| RPT-007 | Générateur PDF sections 17-22 (sauvegardes, docs, AV, M365, parc, shadow IT) | server | L | steps-42-server.md + steps-43-server.md |
| RPT-008 | Générateur PDF sections 23-25 (points forts, quick wins, synthèse/matrice) | server | M | steps-44-server.md |
| RPT-009 | Générateur Word (python-docx) | server | L | steps-45-server.md |
| RPT-011 | Auto-insertion preuves dans rapport | server | M | steps-46-server.md |
| RPT-013 | Frontend page génération rapport | server | M | steps-47-server.md |

### Critère de succès
- [ ] Rapport PDF complet 25 sections généré
- [ ] Export Word fonctionnel
- [ ] Preuves (Attachments) auto-insérées
- [ ] Frontend : choisir template, prévisualiser, télécharger PDF/Word
- [ ] Matrice de recommandations classée par catégorie + risque + tags

### Dépendances inter-repos
Aucune — sprint 100% serveur.

---

## Sprint 5 — Vue rack, M365 évaluation, firewall (2 semaines)

**Focus** : Fonctionnalités produit différenciantes.

### Tâches

| ID | Titre | Repo | Taille | Step |
|---|---|---|---|---|
| RACK-001 | Modèle Rack/Bay | server | M | steps-48-server.md |
| RACK-002 | API CRUD racks | server | S | steps-48-server.md |
| RACK-003 | Frontend composant rack drag & drop | server | L | steps-49-server.md |
| M365-001 | Évaluation auto Monkey365 → CIS M365 v5 | server | L | steps-50-server.md |
| M365-002 | Import structuré résultats Monkey365 dans assessments | server | M | steps-51-server.md |
| FW-001 | Analyse automatique règles firewall | server | M | steps-52-server.md |
| FW-003 | Findings automatiques firewall | server | M | steps-52-server.md |

### Critère de succès
- [ ] Vue rack configurable avec drag & drop
- [ ] Résultats Monkey365 évalués automatiquement contre CIS M365 v5
- [ ] Règles firewall analysées automatiquement (0 hit, any→any, IPS)
- [ ] Findings firewall générés avec tags

### Dépendances inter-repos
Aucune — sprint 100% serveur.

---

## Sprint 6 — Remédiation, synoptiques avancés, IA (2 semaines)

**Focus** : Workflow de suivi et intelligence.

### Tâches

| ID | Titre | Repo | Taille | Step |
|---|---|---|---|---|
| REM-001 | Modèle Remediation | server | M | steps-53-server.md |
| REM-002 | API remédiation | server | M | steps-54-server.md |
| REM-003 | Frontend dashboard remédiation | server | L | steps-55-server.md |
| NET-001 | Vue simplifiée (client) vs détaillée (technicien) | server | M | steps-56-server.md |
| NET-003 | Export image/PDF synoptique | server | S | steps-56-server.md |
| AI-001 | Service IA abstrait (cloud/local, fallback) | server | M | steps-57-server.md |
| AI-005 | Configuration providers IA | server | M | steps-57-server.md |
| AI-002 | Résumé exécutif auto-généré | server | M | steps-58-server.md |

### Critère de succès
- [ ] Workflow remédiation fonctionnel (statuts, preuves, dashboard)
- [ ] Synoptique exportable en image/PDF
- [ ] Service IA avec au moins Claude API + Ollama
- [ ] Résumé exécutif auto-généré pour un audit

### Dépendances inter-repos
Aucune — sprint 100% serveur.

---

## Sprint 7 — Agent enrichi & outils manquants (2 semaines)

**Focus** : Outils agent manquants, collecteurs.

### Tâches

| ID | Titre | Repo | Taille | Step |
|---|---|---|---|---|
| AGT-001 | Outil iperf3 | agent | M | steps-08-agent.md |
| AGT-002 | Outil speedtest-cli | agent | M | steps-09-agent.md |
| AGT-003 | API + frontend résultats débit | server | M | steps-59-server.md |
| AD-003 | Script PowerShell Azure AD Connect / Entra ID | agent | M | steps-10-agent.md |
| AD-005 | Findings automatiques AD | server | M | steps-60-server.md |
| INV-006 | Auto-détection OS obsolètes → tag `legacy` | server | S | steps-60-server.md |
| COL-006 | Détection shadow IT (nmap vs DHCP/DNS) | server + agent | M | steps-61-server.md |

### Critère de succès
- [ ] Tests débit LAN (iperf3) et internet (speedtest) fonctionnels
- [ ] Résultats débit affichés avec comparaison contractuel vs mesuré
- [ ] Findings AD automatiques (PasswordNeverExpires, inactifs, GPO dangereuses)
- [ ] Shadow IT détecté automatiquement

### Dépendances inter-repos
- `AGT-001`, `AGT-002` (agent) avant `AGT-003` (serveur)
- `AD-003` (agent) indépendant

---

## Sprint 8 — RBAC Phase 2 & CI/CD (2 semaines)

**Focus** : Contrôle d'accès fin et industrialisation.

### Tâches

| ID | Titre | Repo | Taille | Step |
|---|---|---|---|---|
| RBAC-001 | Table ResourcePermission | server | M | steps-62-server.md |
| RBAC-002 | Héritage permissions | server | L | steps-63-server.md |
| RBAC-003 | Migration 30+ endpoints | server | XL | steps-64→66-server.md |
| RBAC-004 | Frontend partage d'audit | server | M | steps-67-server.md |
| TD-026 | CI/CD GitHub Actions | server | M | steps-68-server.md |
| AGT-004 | Mode air-gapped (export/import chiffré) | agent | L | steps-11-agent.md |

### Critère de succès
- [ ] RBAC par ressource fonctionnel (owner/write/read)
- [ ] Lecteurs peuvent voir uniquement les audits partagés
- [ ] CI/CD : lint + tests + build sur chaque PR
- [ ] Agent : export chiffré pour mode air-gapped

### Dépendances inter-repos
- RBAC (serveur) indépendant de l'agent
- Air-gapped (agent) indépendant du serveur

---

## Sprint 9 — Collecteurs avancés & pipeline (2 semaines)

**Focus** : Enrichir les collecteurs agent + pipeline commercial.

### Tâches

| ID | Titre | Repo | Taille | Step |
|---|---|---|---|---|
| INV-001 | Script PS collecte serveurs (hardware, RAID, iLO) | agent | L | steps-12-agent.md |
| INV-003 | Collecte SNMP switches | agent | L | steps-13-agent.md |
| INV-004 | API import résultats inventaire | server | M | steps-69-server.md |
| INV-005 | Modèle licences & garanties | server | M | steps-70-server.md |
| PIP-001 | Modèle pipeline | server | M | steps-71-server.md |
| PIP-002 | Chiffrage remédiation j/h | server | M | steps-72-server.md |

### Critère de succès
- [ ] Agent collecte hardware serveurs (RAID, iLO/iDRAC, garanties)
- [ ] Agent collecte SNMP switches (ports, MAC, LLDP)
- [ ] Résultats importés dans modèle Equipement
- [ ] Licences et garanties trackées
- [ ] Pipeline commercial basique fonctionnel

### Dépendances inter-repos
- `INV-001`, `INV-003` (agent) avant `INV-004` (serveur)

---

## Sprint 10 — Mode terrain, audits récurrents, polish (2 semaines)

**Focus** : UX terrain et fonctionnalités évolution.

### Tâches

| ID | Titre | Repo | Taille | Step |
|---|---|---|---|---|
| MOB-001 | Responsive tablette | server | L | steps-73-server.md |
| MOB-002 | Photos rattachées au contexte | server | M | steps-74-server.md |
| REC-001 | Comparaison audit N vs N-1 | server | L | steps-75-server.md |
| REC-003 | Alertes proactives (garanties, licences) | server | M | steps-76-server.md |
| TD-007 | Refactoriser network-map/page.tsx | server | L | steps-77-server.md |
| TD-015 | Tests frontend (base vitest + 10 tests clés) | server | L | steps-78-server.md |

### Critère de succès
- [ ] Interface utilisable sur tablette
- [ ] Photos prises depuis l'app rattachées au contexte
- [ ] Comparaison entre audits N et N-1
- [ ] Alertes sur garanties/licences expirant
- [ ] network-map/page.tsx < 500 lignes par composant
- [ ] Au moins 10 tests frontend

### Dépendances inter-repos
Aucune — sprint 100% serveur.

---

## Récapitulatif

| Sprint | Focus | Durée | Tâches | Livrable end-to-end |
|--------|-------|-------|--------|---------------------|
| 1 | Sécurité + tags + checklists + Docker | 2 sem | 14 | API tags + checklists fonctionnelles |
| 2 | Rapport v1 + checklists frontend | 2 sem | 11 | Rapport PDF sections 1-4 + UI checklists |
| 3 | Rapport sections 5-16 + AD agent | 2 sem | 5 | Rapport 16 sections + AD complet |
| 4 | Rapport complet + Word | 2 sem | 5 | Rapport 25 sections PDF + Word |
| 5 | Rack + M365 auto + firewall auto | 2 sem | 7 | Vue rack + évaluation automatique |
| 6 | Remédiation + synoptiques + IA | 2 sem | 8 | Workflow remédiation + IA résumé |
| 7 | Outils agent + findings auto | 2 sem | 7 | iperf3 + speedtest + shadow IT |
| 8 | RBAC Phase 2 + CI/CD | 2 sem | 6 | Permissions fines + CI/CD |
| 9 | Collecteurs avancés + pipeline | 2 sem | 6 | SNMP + hardware + pipeline |
| 10 | Mode terrain + récurrence | 2 sem | 6 | Tablette + comparaison audits |

**Total** : ~20 semaines (~5 mois), 75 tâches planifiées sur les 100 du backlog.

Les 25 tâches restantes (P3, principalement collecteurs spécialisés Wi-Fi/VPN/sauvegardes/AV/postes et templates rapport alternatifs) sont **post-MVP** et seront planifiées après le sprint 10 selon les retours terrain.
