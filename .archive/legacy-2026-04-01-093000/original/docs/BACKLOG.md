# Backlog AssistantAudit

**Date** : 2026-03-30
**Source** : `AUDIT-ETAT-DES-LIEUX.md` + `backlog/tech-debt.md` + `PROJECT-BRIEF-v7-final.md`

---

## Légende

| Priorité | Signification |
|----------|---------------|
| **P0** | Bloquant production / sécurité critique |
| **P1** | Fondation — nécessaire avant d'autres tâches |
| **P2** | Fonctionnalité clé du produit (différenciateur) |
| **P3** | Amélioration, non bloquant |

| Taille | Estimation |
|--------|-----------|
| **S** | < 1 jour (1 step) |
| **M** | 1-3 jours (1-2 steps) |
| **L** | 3-5 jours (2-3 steps) |
| **XL** | 5+ jours (3+ steps) |

---

## Module : Dette technique & Sécurité

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| TD-001 | Migrer 121 occurrences `if not X: raise 404` vers `get_or_404()` | P3 | M | server | - | - | tech-debt |
| TD-002 | Implémenter `rotate_kek.py` (rotation KEK complète) | P1 | M | server | - | §4 sécurité | security |
| TD-003 | Centraliser ownership check FK chain (dupliqué 3x) | P3 | S | server | - | - | tech-debt |
| TD-004 | Créer helper `atomic_write()` pour 15 opérations fichier sans try/except | P2 | S | server | - | - | tech-debt, security |
| TD-005 | Typer ~20 schemas avec `Literal`/`Enum` au lieu de `str` | P3 | M | server | - | - | tech-debt |
| TD-006 | Tests manquants : scan_service, collect_service, ad_audit_service, config_analysis_service | P2 | M | server | - | - | tech-debt |
| TD-007 | Refactoriser `network-map/page.tsx` (~2900 lignes) en composants | P2 | L | server | - | §7.3 | tech-debt, frontend |
| TD-008 | `uploaded_by` sur Attachment : `String(200)` → FK vers `users.id` | P3 | S | server | - | - | tech-debt |
| TD-009 | Backfill `owner_id` nullable sur audits/scans/ad_audit_results | P1 | S | server | - | §1.5 | security |
| TD-010 | CRUD copié-collé 25+ endpoints quasi-identiques → générique | P3 | L | server | - | - | tech-debt |
| TD-011 | Services retournent mix de types → standardiser | P3 | M | server | - | - | tech-debt |
| TD-012 | Messages d'erreur mix FR/EN dans tools/* | P3 | S | server | - | - | tech-debt |
| TD-013 | Rate limiting WebSocket absent | P2 | S | server | - | §4 sécurité | security |
| TD-014 | Buffers WS non nettoyés pour users inactifs | P2 | S | server | - | - | tech-debt |
| TD-015 | Tests frontend (jest/vitest/playwright) — actuellement 0 | P2 | XL | server | - | §12 DoD | tech-debt, frontend |
| TD-016 | `max_length` manquant sur ~100 champs str schemas output | P3 | M | server | - | - | tech-debt |
| TD-017 | Consolider 2 routes création user (`/auth/register` + `/users/`) | P2 | S | server | - | - | tech-debt |
| TD-018 | Contacts entreprise sans validation email/téléphone schema | P3 | S | server | - | - | tech-debt |
| TD-019 | Credentials en clair passés au task_runner (migration Celery) | P2 | M | server | - | §1.5 | security |
| TD-020 | Frontend ne tente pas refresh token avant redirect 401 | P1 | S | server | - | - | security, frontend |
| TD-021 | CSP `connect-src 'self'` bloque WS en dev | P3 | S | server | - | - | tech-debt |
| TD-022 | `ScanReseau.owner_id` nullable — scans orphelins | P1 | S | server | - | §1.5 | security |
| TD-023 | Endpoint `/metrics` non authentifié | P1 | S | server | - | - | security |
| TD-024 | DPAPI non installé agent — JWT stocké en base64 | P2 | S | agent | - | - | security |
| TD-025 | Dockerfile + docker-compose.yml | P2 | M | server | - | §9 | tech-debt |
| TD-026 | CI/CD GitHub Actions (lint, tests, build) | P2 | M | server | TD-025 | §12 DoD | tech-debt |

### Critères d'acceptation (tous les TD)
- Tests existants passent (0 régressions)
- Nouveau code couvert par tests

---

## Module : Checklists terrain (brief §4)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| CK-001 | Modèles ChecklistTemplate, ChecklistItem, ChecklistResponse + migrations | P1 | M | server | - | §4.2 | from-brief |
| CK-002 | Service checklist (CRUD template, répondre, rattacher preuves) | P1 | M | server | CK-001 | §4.2 | from-brief |
| CK-003 | Routes API checklists (CRUD + réponses + preuves) | P1 | M | server | CK-002 | §4.2 | from-brief |
| CK-004 | Seed checklist LAN prédéfinie (brief §4.2 complet) | P1 | S | server | CK-001 | §4.2 | from-brief |
| CK-005 | Seed checklist salle serveur (brief §6.13) | P2 | S | server | CK-001 | §6.13 | from-brief |
| CK-006 | Seed checklist documentation & outils internes (brief §6.16) | P2 | S | server | CK-001 | §6.16 | from-brief |
| CK-007 | Seed checklist protocole de départ (brief §4.3) | P2 | S | server | CK-001 | §4.3 | from-brief |
| CK-008 | Frontend : composant checklist (statuts, notes, preuves, mode tablette) | P2 | L | server | CK-003 | §4.2, §7.2 | from-brief, frontend |
| CK-009 | Enrichir modèle Audit : champs fiche d'intervention manquants | P2 | S | server | - | §4.1 | from-brief |

### Critères d'acceptation
- [ ] Checklist LAN remplissable via API avec statuts OK/NOK/N-A/non vérifié
- [ ] Chaque point peut avoir une note libre et des preuves (Attachment)
- [ ] Templates prédéfinis chargés au seed
- [ ] Frontend responsive (tablette)

---

## Module : Système de tags (brief §5)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| TAG-001 | Modèle Tag + table liaison polymorphe + migration | P1 | M | server | - | §5 | from-brief |
| TAG-002 | Service tags (CRUD, association, filtrage) | P1 | S | server | TAG-001 | §5 | from-brief |
| TAG-003 | Routes API tags (CRUD + association + filtrage par tag) | P1 | S | server | TAG-002 | §5 | from-brief |
| TAG-004 | Seed tags prédéfinis (critical, legacy, quick-win, shadow-it, etc.) | P1 | S | server | TAG-001 | §5 | from-brief, quick-win |
| TAG-005 | Frontend : composant badge tag + filtre multi-tag sur listes | P2 | M | server | TAG-003 | §5 | from-brief, frontend |

### Critères d'acceptation
- [ ] Tags rattachables à : équipement, finding, recommandation, checklist item
- [ ] 8 tags prédéfinis avec couleurs
- [ ] Tags custom créables par audit ou globalement
- [ ] Filtrage par tag dans les endpoints de liste

---

## Module : Inventaire infrastructure agent (brief §6.1)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| INV-001 | Script PowerShell collecte serveurs (hardware, RAID, iLO, hyperviseur) | P2 | L | agent | - | §6.1 | from-brief, agent |
| INV-002 | Script PowerShell collecte VMs (état, ressources, event log) | P2 | M | agent | - | §6.1 | from-brief, agent |
| INV-003 | Collecte SNMP switches (ports, MAC, LLDP/CDP, firmware) | P2 | L | agent | - | §6.1 | from-brief, agent |
| INV-004 | API import résultats inventaire → modèle Equipement | P2 | M | server | INV-001 | §6.1 | from-brief |
| INV-005 | Modèle licences & garanties (numéro série, constructeur, dates) | P2 | M | server | - | §6.1 | from-brief |
| INV-006 | Auto-détection OS obsolètes → tag `legacy` | P2 | S | server | TAG-001, INV-004 | §6.1 | from-brief |

---

## Module : Active Directory (brief §6.2)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| AD-001 | Script PowerShell AD complet (OU, comptes détaillés, MDP policies, groupes admin) | P1 | L | agent | - | §6.2 | from-brief, agent |
| AD-002 | Script PowerShell DCDIAG + GPO analyse + DNS zones + DHCP | P2 | L | agent | AD-001 | §6.2 | from-brief, agent |
| AD-003 | Script PowerShell Azure AD Connect / Entra ID statut sync | P2 | M | agent | AD-001 | §6.2 | from-brief, agent |
| AD-004 | Parsing structuré résultats AD côté serveur | P1 | M | server | AD-001 | §6.2 | from-brief |
| AD-005 | Findings automatiques AD (PasswordNeverExpires, inactifs, GPO dangereuses) | P2 | M | server | AD-004, TAG-001 | §6.2 | from-brief |

---

## Module : Outils agent manquants (brief §8)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| AGT-001 | Outil iperf3 (test débit LAN) | P3 | M | agent | - | §6.6, §8 | from-brief, agent |
| AGT-002 | Outil speedtest-cli (test débit internet) | P3 | M | agent | - | §6.6, §8 | from-brief, agent |
| AGT-003 | API + frontend résultats débit (comparaison contractuel vs mesuré) | P3 | M | server | AGT-001, AGT-002 | §6.6 | from-brief |
| AGT-004 | Mode air-gapped : export fichier chiffré + import | P2 | L | agent + server | - | §8 | from-brief, agent |
| AGT-005 | Windows Service (`install-service` fonctionnel) | P3 | M | agent | - | - | agent |

---

## Module : Firewall & config (brief §6.5)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| FW-001 | Analyse automatique règles (0 hit, any→any, IPS non activé) | P2 | M | server | - | §6.5 | from-brief |
| FW-002 | Modèle licence/garantie firewall + extraction depuis config | P2 | S | server | INV-005 | §6.5 | from-brief |
| FW-003 | Findings automatiques firewall (admin exposé, services obsolètes) | P2 | M | server | FW-001, TAG-001 | §6.5 | from-brief |
| FW-004 | Référentiel CIS FortiGate YAML | P3 | M | server | - | §7.5 | from-brief |

---

## Module : Microsoft 365 (brief §6.7)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| M365-001 | Évaluation automatique Monkey365 → contrôles CIS M365 v5 | P2 | L | server | - | §6.7 | from-brief |
| M365-002 | Import structuré résultats Monkey365 dans assessments | P2 | M | server | M365-001 | §6.7 | from-brief |
| M365-003 | Rapport détaillé M365 par catégorie (Entra ID, Exchange, SharePoint, Teams) | P2 | M | server | M365-001 | §6.7 | from-brief |

---

## Module : Rapports & livrables (brief §7.7)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| RPT-001 | Dépendances : WeasyPrint/ReportLab (PDF) + python-docx (Word) + Jinja2 (templates) | P1 | S | server | - | §7.7 | from-brief |
| RPT-002 | Modèle de données rapport (structure 25 sections, metadata) | P1 | M | server | RPT-001 | §7.7 | from-brief |
| RPT-003 | Template PDF rapport complet (brandable : logo, couleurs) | P1 | L | server | RPT-002 | §7.7 | from-brief |
| RPT-004 | Générateur PDF : sections 1-4 (page de garde, intro, objectifs, périmètre) | P1 | M | server | RPT-003 | §7.7 | from-brief |
| RPT-005 | Générateur PDF : sections 5-9 (lieux, synoptique, locaux, onduleurs, internet) | P2 | L | server | RPT-004 | §7.7 | from-brief |
| RPT-006 | Générateur PDF : sections 10-16 (IP, switches, Wi-Fi, FW, serveurs, NAS, AD) | P2 | L | server | RPT-005 | §7.7 | from-brief |
| RPT-007 | Générateur PDF : sections 17-22 (sauvegardes, docs, AV, M365, parc, shadow IT) | P2 | L | server | RPT-006 | §7.7 | from-brief |
| RPT-008 | Générateur PDF : sections 23-25 (points forts, quick wins, synthèse/matrice) | P2 | M | server | RPT-007, TAG-001 | §7.7 | from-brief |
| RPT-009 | Générateur Word (python-docx) — même structure | P2 | L | server | RPT-003 | §7.7 | from-brief |
| RPT-010 | Templates alternatifs (allégé, conformité) | P3 | M | server | RPT-003 | §7.7 | from-brief |
| RPT-011 | Auto-insertion des preuves (Attachments) dans le rapport | P2 | M | server | RPT-003 | §7.7 | from-brief |
| RPT-012 | Routes API génération rapport (POST + download) | P1 | S | server | RPT-004 | §7.7 | from-brief |
| RPT-013 | Frontend : page génération rapport (choix template, preview, download) | P2 | M | server | RPT-012 | §7.7 | from-brief, frontend |

### Critères d'acceptation
- [ ] Rapport PDF 20-80+ pages généré automatiquement
- [ ] Logo consultant et client personnalisables
- [ ] Preuves auto-insérées aux bons endroits
- [ ] Export Word éditable
- [ ] Matrice de recommandations classée par catégorie + risque + tags

---

## Module : Synoptiques réseau (brief §7.3)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| NET-001 | Vue simplifiée (client) vs vue détaillée (technicien) | P2 | M | server | TD-007 | §7.3 | from-brief, frontend |
| NET-002 | Auto-génération depuis SNMP/LLDP/CDP (import résultats agent) | P2 | L | server | INV-003 | §7.3 | from-brief |
| NET-003 | Export image/PDF du synoptique | P2 | S | server | - | §7.3 | from-brief, frontend |

---

## Module : Vue rack (brief §7.4)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| RACK-001 | Modèle Rack/Bay (localisation, type, taille, contenu ordonné) | P2 | M | server | - | §7.4 | from-brief |
| RACK-002 | API CRUD racks + contenu | P2 | S | server | RACK-001 | §7.4 | from-brief |
| RACK-003 | Frontend : composant rack drag & drop (faces avant/arrière, photos) | P2 | L | server | RACK-002 | §7.4 | from-brief, frontend |
| RACK-004 | Export image/PDF du rack | P3 | S | server | RACK-003 | §7.4 | from-brief |
| RACK-005 | Auto-suggestion contenu depuis inventaire équipements | P3 | S | server | RACK-001, INV-004 | §7.4 | from-brief |

---

## Module : Pipeline commercial & chiffrage (brief §7.8)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| PIP-001 | Modèle pipeline (statut audit, historique client, scoring évolution) | P3 | M | server | - | §7.8 | from-brief |
| PIP-002 | Chiffrage remédiation j/h par catégorie (barèmes configurables) | P3 | M | server | PIP-001 | §7.8 | from-brief |
| PIP-003 | Frontend : dashboard pipeline + historique client | P3 | L | server | PIP-002 | §7.8 | from-brief, frontend |

---

## Module : Audits récurrents & évolution (brief §7.9)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| REC-001 | Comparaison audit N vs N-1 (nouveaux/résolus/persistants findings) | P3 | L | server | - | §7.9 | from-brief |
| REC-002 | Timeline maturité (scoring par audit) | P3 | M | server | REC-001 | §7.9 | from-brief |
| REC-003 | Alertes proactives (garanties, certificats, licences expirant) | P3 | M | server | INV-005 | §7.9 | from-brief |
| REC-004 | Planification récurrente | P3 | S | server | - | §7.9 | from-brief |

---

## Module : Workflow de remédiation (brief §7.10)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| REM-001 | Modèle Remediation (statut, assignation, preuves avant/après) | P2 | M | server | - | §7.10 | from-brief |
| REM-002 | API remédiation (CRUD + transitions statut + preuves) | P2 | M | server | REM-001 | §7.10 | from-brief |
| REM-003 | Frontend : dashboard remédiation avec progression | P2 | L | server | REM-002 | §7.10 | from-brief, frontend |

---

## Module : IA hybride (brief §7.12)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| AI-001 | Service IA abstrait (provider cloud/local, fallback sans IA) | P2 | M | server | - | §7.12 | from-brief |
| AI-002 | Résumé exécutif auto-généré | P2 | M | server | AI-001, RPT-002 | §7.12 | from-brief |
| AI-003 | Suggestions de remédiation contextualisées | P3 | M | server | AI-001 | §7.12 | from-brief |
| AI-004 | Quick wins automatiques depuis findings | P3 | S | server | AI-001, TAG-001 | §7.12 | from-brief |
| AI-005 | Configuration providers (Claude/OpenAI/Mistral + Ollama/llama.cpp/vLLM) | P2 | M | server | AI-001 | §7.12 | from-brief |

---

## Module : Mode terrain / tablette (brief §7.14)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| MOB-001 | Responsive tablette (layout adaptatif, touch-friendly) | P2 | L | server | - | §7.14 | from-brief, frontend |
| MOB-002 | Prise photos rattachées au contexte | P2 | M | server | CK-003 | §7.14 | from-brief, frontend |
| MOB-003 | Mode offline avec sync au retour | P3 | XL | server | - | §7.14 | from-brief, frontend |
| MOB-004 | Scan QR/code-barres (numéro série, asset tag) | P3 | M | server | - | §7.14 | from-brief, frontend |

---

## Module : RBAC Phase 2 (brief §1.5)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| RBAC-001 | Table ResourcePermission (user_id, resource_type, resource_id, level) | P2 | M | server | - | §1.5 | from-brief, security |
| RBAC-002 | Héritage permissions entreprise → audit → site → équipement | P2 | L | server | RBAC-001 | §1.5 | security |
| RBAC-003 | Migration 30+ endpoints pour vérifier ResourcePermission | P2 | XL | server | RBAC-002 | §1.5 | security |
| RBAC-004 | Frontend : interface partage d'audit (inviter lecteur/auditeur) | P2 | M | server | RBAC-003 | §1.5 | from-brief, frontend |

---

## Module : Collecteurs absents (brief §6.3-6.16)

| ID | Titre | Prio | Taille | Repo | Dépendances | Brief | Tags |
|---|---|---|---|---|---|---|---|
| COL-001 | Collecteur Wi-Fi (contrôleurs, bornes, SSID, clients, firmware) | P3 | L | agent | - | §6.3 | from-brief, agent |
| COL-002 | Collecteur VPN (type, utilisateurs, MFA, split/full tunnel) | P3 | M | agent | - | §6.4 | from-brief, agent |
| COL-003 | Collecteur sauvegardes (Veeam, WSB, Acronis, M365 backup) | P3 | L | agent | - | §6.8 | from-brief, agent |
| COL-004 | Collecteur antivirus/EDR (console, modules, endpoints, agents manquants) | P3 | L | agent | - | §6.9 | from-brief, agent |
| COL-005 | Collecteur postes (hostname, OS, AV, supervision, série) | P3 | M | agent | - | §6.10 | from-brief, agent |
| COL-006 | Détection shadow IT automatique (nmap vs DHCP/DNS) | P2 | M | server + agent | TAG-001 | §6.11 | from-brief |
| COL-007 | Performance réseau (SPOF, saturation ports, erreurs SNMP) | P3 | L | agent | INV-003 | §6.12 | from-brief, agent |
| COL-008 | API + frontend pour chaque collecteur côté serveur | P3 | XL | server | COL-001→007 | §6.3-6.12 | from-brief |

---

## Résumé par priorité

| Priorité | Nombre | Effort estimé |
|----------|--------|---------------|
| P0 | 0 | - |
| P1 | 17 | ~25 jours |
| P2 | 52 | ~115 jours |
| P3 | 31 | ~75 jours |
| **Total** | **100 tâches** | **~215 jours** |
