# Exigences fonctionnelles — AssistantAudit

<!-- SCOPE: Catalogue des exigences fonctionnelles (FR) de la plateforme AssistantAudit. Norme cible : ISO/IEC/IEEE 29148:2018 (Functional Requirements). Hors scope : exigences non fonctionnelles (politique projet : NFR exclues). -->
<!-- DOC_KIND: explanation -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu cherches le perimetre fonctionnel ou tu ecris une nouvelle story. -->
<!-- SKIP_WHEN: Tu cherches une decision technique ou une procedure ops. -->
<!-- PRIMARY_SOURCES: docs/project/architecture.md, frameworks/*.yaml -->
DOC_KIND: project-requirements
DOC_ROLE: catalogue-fonctionnel
READ_WHEN: redaction d'une story, qualification d'une demande, evaluation de couverture fonctionnelle.
SKIP_WHEN: recherche d'une decision d'architecture (voir `architecture.md`), d'une version de dependance (voir `tech_stack.md`) ou d'un schema d'API (voir `../reference/` / Swagger).
PRIMARY_SOURCES: `backend/app/api/v1/`, `backend/app/services/`, `backend/app/models/`, `backend/app/data/glossary.yaml`, `frameworks/*.yaml`, `frontend/src/app/`, `docker-compose.yml`.

## Quick Navigation

| Section | Sujet |
|---------|-------|
| [Vision produit](#vision-produit) | Mission, utilisateurs cibles, valeur metier |
| [Personas](#personas) | Profils utilisateurs et besoins |
| [Capacites fonctionnelles](#capacites-fonctionnelles) | Catalogue FR-XX |
| [Contraintes](#contraintes) | Regles transverses obligatoires |
| [Glossaire metier](#glossaire-metier) | Definitions des termes du domaine |
| [Maintenance](#maintenance) | Regles de mise a jour de ce document |

## Agent Entry

| Si la demande concerne... | Alors consulter |
|---------------------------|-----------------|
| Une nouvelle capacite fonctionnelle | Tableau [Capacites fonctionnelles](#capacites-fonctionnelles) |
| Un terme metier ambigu | [Glossaire metier](#glossaire-metier) + `backend/app/data/glossary.yaml` |
| Une regle transverse (chiffrement, RBAC, langue, rate-limit) | [Contraintes](#contraintes) |
| Un referentiel d'audit | `frameworks/*.yaml` (auto-syncs vers la table `framework`) |

## Vision produit

AssistantAudit est une plateforme web qui industrialise le cycle d'audit de securite IT pour des equipes Red Team, des auditeurs de conformite et des consultants en cybersecurite. Elle centralise les referentiels (CIS M365, ANSSI, ISO 27001, NIS2, frameworks personnalises), automatise la collecte de preuves (M365, Active Directory, configurations reseau, scans SSL/Nmap) et produit des rapports homogenes (PDF + DOCX) pretes a livrer au client.

- **Pour qui** : Red Team interne, auditeurs externes, consultants cybersecurite, administrateurs plateforme.
- **Pour quoi** : reduire le temps de production d'un audit, garantir la tracabilite des preuves, harmoniser le rendu client.
- **Valeur** : une seule interface couvre la collecte, l'evaluation, le findings management, le plan de remediation et la livraison documentaire.

## Personas

| Persona | Objectifs principaux | Capacites cles utilisees |
|---------|----------------------|--------------------------|
| Red Team | Cartographier le SI cible, identifier les vulnerabilites, capitaliser les preuves | Network map, scans SSL, AD audit, Monkey365, configuration parsers |
| Auditeur de conformite | Evaluer la conformite contre un referentiel, justifier chaque controle, livrer un rapport | Frameworks YAML, assessments, checklists ANSSI, findings, rapports PDF/DOCX |
| Consultant cybersecurite | Construire un plan de remediation, prioriser les actions, suivre l'avancement | Recommandations, plan de remediation, glossaire metier, executive summary |
| Admin plateforme | Gerer les entreprises clientes, isoler les donnees, controler les acces, deployer les agents | RBAC, multi-tenant `owner_id`, agents Windows mTLS, certificats |

## Capacites fonctionnelles

| ID | Capacite | Description | Acceptation |
|----|----------|-------------|-------------|
| FR-01 | Multi-tenant entreprises | La plateforme isole les donnees par entreprise cliente avec sites et equipements rattaches. | Toute entite metier porte `owner_id`; un utilisateur ne voit que les entreprises auxquelles il est rattache. |
| FR-02 | Sites et equipements | Modeliser le SI client : sites (geographiques) et equipements (firewall, switch, serveur Linux/Windows, AP WiFi, peripherique, etc.). | Un equipement est rattache a un site, lui-meme rattache a une entreprise. |
| FR-03 | Audits + assessments | Demarrer un audit pour un client, declencher des assessments (evaluations) attaches a un audit. | Un audit a un statut, des dates d'intervention, des assessments associes, un rapport final. |
| FR-04 | Frameworks YAML auto-sync | Les referentiels d'audit YAML places dans `frameworks/` sont charges en base au demarrage de l'application. | Au boot de l'API, la table `framework` reflete les fichiers YAML presents (insertion, mise a jour). |
| FR-05 | Catalogue de referentiels | La plateforme livre les referentiels : CIS M365 v5, ANSSI, M365, Active Directory, server Linux, server Windows, firewall, OPNsense, switch, VPN, WiFi, sauvegarde, peripheriques, DNS/DHCP, messagerie. | `frameworks/*.yaml` contient les fichiers correspondants charges en base. |
| FR-06 | Checklists ANSSI | Disposer de checklists ANSSI predefinies (depart utilisateur, documentation, LAN, salle serveur). | Les seeds `seed_checklist_*.py` peuplent la table `checklist` avec les checklists ANSSI. |
| FR-07 | Findings | Saisir et gerer des findings : titre, severite, statut, description, recommandation associee. | Endpoints `/api/v1/findings`; severites alignees sur ANSSI / CVSS-like. |
| FR-08 | Recommandations | Generer des recommandations a partir des findings. | Service `recommendations_service`; rendu dans la section recommandations du rapport. |
| FR-09 | Plan de remediation | Construire un plan de remediation priorise (effort, gain, criticite). | Service `remediation_plan_service`; rendu dans la section plan de remediation du rapport. |
| FR-10 | Agents Windows mTLS | Deployer des agents Windows pour la collecte M365/AD/PowerShell, authentification mTLS via certificat client. | Cycle de vie agents (`agent`, `agent_task`, `task_artifact`); CA propre (`core/cert_manager.py`); WS `/ws/agent`. |
| FR-11 | Pipelines de collecte | Orchestrer la collecte multi-sources (SSH, WinRM, AD, M365) via des pipelines. | Endpoints `/api/v1/pipelines`; modele `collect_pipeline` + `collect_result`. |
| FR-12 | AD audit | Auditer un Active Directory (LDAP, comptes, GPO, delegations). | Outil `tools/ad_auditor`; endpoint `/api/v1/tools/ad_audit`. |
| FR-13 | Monkey365 | Lancer Monkey365 pour evaluer un tenant M365, capturer la sortie PowerShell en streaming. | Outil `tools/monkey365_runner`; service `monkey365_streaming_executor`; modele `monkey365_scan_result`. |
| FR-14 | ORADAD | Importer et evaluer des resultats ORADAD pour un audit AD ANSSI. | Service `oradad_analysis_service`; endpoints `/api/v1/oradad`. |
| FR-15 | SSL checker | Verifier les chaines TLS / certificats d'un endpoint. | Outil `tools/ssl_checker`; endpoint `/api/v1/tools/ssl_checker`. |
| FR-16 | Config parsers | Parser et evaluer des configurations Fortinet et OPNsense. | Outils `tools/config_parsers/{fortinet,opnsense}.py`. |
| FR-17 | Network map | Editer une cartographie reseau (sites, equipements, VLAN, liens) avec rendu graphe. | Modele `network_map`; UI `/outils/network-map` (xyflow + dagre); endpoints `/api/v1/network-map`. |
| FR-18 | Rapports PDF | Generer un rapport PDF complet (cover, executive summary, scope, objectifs, findings, recommandations, plan de remediation, glossaire, annexes, TOC). | WeasyPrint + Jinja2 + `app/templates/reports/`; endpoint `/api/v1/reports`. |
| FR-19 | Rapports DOCX | Generer une variante DOCX du rapport. | python-docx + service `report_service`. |
| FR-20 | Tags | Categoriser les entites (audits, equipements, findings) via un systeme de tags. | Endpoints `/api/v1/tags`; modele `tag`. |
| FR-21 | Pieces jointes | Attacher des fichiers (preuves, exports) a une entite, avec chiffrement KEK+DEK enveloppe. | Endpoints `/api/v1/attachments` + `/api/v1/files`; service `file_service`. |
| FR-22 | RBAC + isolation | Controler les acces par role et garantir l'isolation par `owner_id` entre tenants. | `core/deps.py` injecte l'utilisateur courant; chaque service filtre par `owner_id`. |
| FR-23 | Glossaire metier | Maintenir un glossaire dynamique injecte dans les rapports. | `backend/app/data/glossary.yaml` charge par `glossary_service`; rendu section glossaire. |
| FR-24 | Executive summary | Produire une synthese executive synthetisant l'audit. | Service `executive_summary_service`. |
| FR-25 | Streaming PowerShell | Diffuser en temps reel la sortie de Monkey365 / scripts PowerShell vers l'UI. | WebSocket; UI xterm.js sur `/outils/monkey365`. |
| FR-26 | Authentification + refresh | Login JWT, refresh token, logout, validation password. | Endpoints `/api/v1/auth` (login/refresh/logout); service `auth_service`. |
| FR-27 | Health check | Exposer un endpoint de sante interroge par Docker / reverse proxy. | `GET /api/v1/health`; healthcheck Dockerfile / docker-compose. |

## Contraintes

| Type | Contrainte |
|------|------------|
| Langue | UI, libelles utilisateur, commentaires, docstrings : francais. Identifiants code : anglais. |
| Backend | Strictement synchrone (`async def` interdit hors handlers WebSocket). |
| Architecture | `api/v1/` ne fait pas d'acces DB direct ; transactions appartiennent aux services ; pas d'`HTTPException` dans les services (utiliser `AppError` / `NotFoundError` de `core/errors.py`). |
| Chiffrement | Colonnes sensibles chiffrees AES-256-GCM via TypeDecorator `EncryptedJSON`; fichiers chiffres en enveloppe KEK + DEK (cf. ADR-001). |
| Authentification agents | mTLS obligatoire pour les agents Windows (CA propre via `core/cert_manager.py`). |
| Rate-limit | Defauts par IP par minute : auth = 5, api = 30, public = 100 (`RATE_LIMIT_AUTH_MAX`, `RATE_LIMIT_API_MAX`, `RATE_LIMIT_PUBLIC_MAX`). |
| DB | Ne jamais renommer une colonne existante : ajouter une nouvelle colonne et migrer via Alembic. |
| Frontend | Stack figee : Next.js 16, React 19, Tailwind v4, shadcn/ui v4. Pas de `as any` ni `@ts-ignore`. |
| Multi-tenant | Toute entite metier porte `owner_id`; les services filtrent systematiquement par tenant. |
| Frameworks | Auto-sync au demarrage : la verite est dans `frameworks/*.yaml`, la base est un cache. |

## Glossaire metier

| Terme | Definition |
|-------|------------|
| Audit | Mission contractuelle d'evaluation de la securite IT d'un client, regroupant un ou plusieurs assessments. |
| Assessment | Evaluation concrete realisee dans le cadre d'un audit (ex. : evaluation contre un framework). |
| Checklist ANSSI | Liste predefinie de controles ANSSI (depart utilisateur, documentation, LAN, salle serveur) instanciable dans un audit. |
| Finding | Constat issu d'un controle non conforme, porteur d'une severite et d'une description. |
| Recommandation | Mesure proposee pour corriger un finding. |
| Remediation | Action concrete inscrite au plan de remediation, avec effort et priorite. |
| Framework | Referentiel YAML decrivant des controles attendus (CIS, ANSSI, M365, AD, etc.) charge en base au demarrage. |
| Agent | Service Windows distant authentifie en mTLS qui execute des collectes M365 / AD / PowerShell pour le compte de la plateforme. |
| Pipeline de collecte | Sequence d'etapes de collecte (SSH, WinRM, AD, M365) orchestree pour un equipement ou une entreprise. |
| Network map | Cartographie graphe (sites, equipements, VLAN, liens) editable depuis l'UI. |
| Monkey365 | Outil tiers integre, evaluant la posture de securite d'un tenant Microsoft 365. |
| ORADAD | Outil ANSSI d'audit d'un Active Directory; ses sorties sont importees et evaluees par la plateforme. |
| OPNsense | Distribution open source de pare-feu / routeur dont la configuration est parsee par le module dedie. |

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

| Regle | Detail |
|-------|--------|
| Source | Toute nouvelle FR-XX nait d'une story Linear ou d'une issue produit. |
| Identifiants | Numerotation continue FR-01..FR-NN ; ne jamais reattribuer un identifiant retire. |
| Synchronisation | Verifier que chaque ligne du tableau capacites correspond a un endpoint `api/v1/`, un service ou un modele present dans le code. |
| Glossaire | Refleter `backend/app/data/glossary.yaml` (verite operationnelle pour les rapports). |
| Audit | Ce document est revu par `ln-612-semantic-content-auditor` et `ln-614-docs-fact-checker`. |
| Liens | Tous les liens internes restent relatifs. |
