# Plan de développement - AssistantAudit

## 🎯 Vision

Un outil d'audit d'infrastructure inspiré de CISO Assistant, mais centré sur l'audit technique d'infrastructure, avec des référentiels d'audit par type d'équipement et des outils intégrés.

---

## 📐 Architecture Conceptuelle

```
┌─────────────────────────────────────────────────────┐
│                  AssistantAudit                      │
├─────────────────────────────────────────────────────┤
│  UI Layer (Frontend)                                │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐            │
│  │Dashboard	 │ │Campagnee	   │ │Rapports   │            │
│  │         	 │ │d'audit   │ │& Exports  │            │
│  └─────────┘ └──────────┘ └───────────┘            │
├─────────────────────────────────────────────────────┤
│  Core Engine                                        │
│  ┌──────────────┐ ┌─────────────┐ ┌──────────────┐ │
│  │Référentiels  │ │Moteur       │ │Scoring &     │ │
│  │d'audit       │ │d'évaluation │ │Conformité    │ │
│  │(Frameworks)  │ │             │ │              │ │
│  └──────────────┘ └─────────────┘ └──────────────┘ │
├─────────────────────────────────────────────────────┤
│  Outils Intégrés                                    │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────────┐ │
│  │Scanner │ │Config  │ │Collecte│ │Analyse      │ │
│  │Réseau  │ │Parser  │ │Auto    │ │Auto         │ │
│  └────────┘ └────────┘ └────────┘ └─────────────┘ │
├─────────────────────────────────────────────────────┤
│  Data Layer (SQLite/PostgreSQL)                     │
└─────────────────────────────────────────────────────┘
```

---

## 📋 Plan en 6 phases

### **Phase 1 — Fondations & Modèle de données** (Semaines 1-3)

**Objectif** : Poser l'architecture et le modèle de données central.

| Tâche | Détail |
|-------|--------|
| Stack technique | Python (backend), FastAPI ou Django, SQLite puis PostgreSQL |
| Modèle de données | Définir les entités clés (voir ci-dessous) |
| Structure projet | Monorepo avec séparation backend/frontend |
| Auth basique | Gestion des utilisateurs/rôles |

**Modèle de données clé :**

```
Référentiel (Framework)
  └── Catégorie (Category)
       └── Point de contrôle (Control)
            └── Critère d'évaluation (Requirement)

Campagne d'audit (Audit Campaign)
  └── Périmètre (Scope) → liste d'équipements
       └── Équipement (Asset)
            └── Évaluation (Assessment)
                 └── Résultat par contrôle (ControlResult)
                      - statut: conforme/non-conforme/partiel/N-A
                      - preuve (evidence)
                      - score
                      - recommandation
```

---

### **Phase 2 — Moteur de Référentiels** (Semaines 4-6)

**Objectif** : Vos mini-audits deviennent des référentiels structurés.

| Tâche | Détail |
|-------|--------|
| Format de référentiel | YAML/JSON pour définir chaque référentiel |
| Import/Export | Charger des référentiels depuis des fichiers |
| Référentiels initiaux | Convertir vos audits existants (Firewall, Switch, Serveur, AD, Wi-Fi...) |
| Versioning | Versionner les référentiels |

**Exemple de structure YAML pour un référentiel :**

````yaml
framework:
  name: "Audit Firewall"
  version: "1.0"
  description: "Référentiel d'audit pour les pare-feu"
  categories:
    - name: "Configuration Générale"
      controls:
        - id: FW-001
          title: "Firmware à jour"
          description: "Le firmware du pare-feu est à la dernière version stable"
          severity: high
          check_type: manual  # ou automatic
          evidence_required: true
          remediation: "Mettre à jour vers la dernière version stable"
        - id: FW-002
          title: "Accès administration sécurisé"
          description: "L'accès admin est limité à HTTPS/SSH uniquement"
          severity: high
          check_type: automatic
          auto_check: "check_admin_protocols"

    - name: "Règles de filtrage"
      controls:
        - id: FW-010
          title: "Règle deny-all par défaut"
          description: "Une règle deny all est présente en fin de politique"
          severity: critical
          check_type: semi-automatic
        - id: FW-011
          title: "Pas de règle any-any"
          description: "Aucune règle n'autorise tout le trafic"
          severity: critical
          check_type: automatic
          auto_check: "check_any_any_rules"

    - name: "Journalisation"
      controls:
        - id: FW-020
          title: "Logging activé"
          description: "Les logs sont activés et envoyés vers un SIEM/Syslog"
          severity: high
          check_type: semi-automatic
````

**Liste de référentiels à créer (vos mini-audits) :**

1. 🔥 Firewall (Fortinet, Palo Alto, pfSense...)
2. 🔀 Switch / Infrastructure réseau
3. 🖥️ Serveur Windows
4. 🐧 Serveur Linux
5. 📁 Active Directory
6. 📶 Wi-Fi
7. 💾 Sauvegarde
8. 🖨️ Imprimantes / Périphériques
9. ☁️ Services Cloud (M365, Azure AD)
10. 📧 Messagerie
11. 🔒 VPN
12. 🌐 DNS / DHCP

---

### **Phase 3 — Interface Utilisateur** (Semaines 7-10)

**Objectif** : Interface web pour gérer les audits.

| Tâche | Détail |
|-------|--------|
| Frontend | React, Vue.js, ou Svelte |
| Dashboard | Vue d'ensemble des campagnes, scores globaux |
| Gestion des campagnes | Créer, suivre, clôturer un audit |
| Évaluation interactive | Remplir point par point avec preuves |
| Visualisation | Graphiques radar par catégorie, jauges de conformité |

**Écrans principaux :**

```
📊 Dashboard
  ├── Campagnes en cours
  ├── Score global de conformité
  └── Alertes (non-conformités critiques)

📋 Campagne d'audit
  ├── Infos client / périmètre
  ├── Équipements à auditer
  ├── Référentiels appliqués
  └── Progression

✅ Évaluation
  ├── Liste des contrôles (par catégorie)
  ├── Statut par contrôle
  ├── Zone de preuve (screenshot, texte, fichier)
  └── Zone de recommandation

📈 Rapports
  ├── Synthèse exécutive
  ├── Détail par équipement
  ├── Plan de remédiation priorisé
  └── Export PDF/Word/Excel
```

---

### **Phase 4 — Outils Intégrés** (Semaines 11-15)

**Objectif** : Automatiser une partie de la collecte et de l'évaluation.

| Outil | Fonction | Technologie |
|-------|----------|-------------|
| **Scanner réseau** | Découverte d'assets, ports ouverts | Nmap (python-nmap) |
| **Config Parser** | Analyser les configs exportées (Fortinet, Cisco...) | Parsers custom Python |
| **Collecte WinRM/SSH** | Récupérer infos serveurs automatiquement | Paramiko, pywinrm |
| **AD Auditor** | Requêtes LDAP pour auditer AD | ldap3, BloodHound integration |
| **Analyseur de règles FW** | Détecter les règles trop permissives | Parser custom |
| **Vérificateur SSL/TLS** | Tester les certificats et protocoles | ssl, cryptography |
| **Benchmark CIS** | Comparer configs vs CIS Benchmarks | Scripts d'évaluation |

````python
"""
Exemple d'outil intégré : Analyseur de config Fortinet
"""
from dataclasses import dataclass
from typing import list


@dataclass
class FirewallFinding:
    control_id: str
    status: str  # "compliant", "non_compliant", "partial"
    evidence: str
    details: str


class FortiGateConfigAnalyzer:
    def __init__(self, config_text: str):
        self.config = config_text
        self.findings: list[FirewallFinding] = []

    def check_any_any_rules(self) -> FirewallFinding:
        """FW-011: Vérifie l'absence de règles any-any"""
        # Parse les policies
        dangerous_rules = []
        in_policy = False
        current_policy = {}

        for line in self.config.split('\n'):
            line = line.strip()
            if 'edit' in line and in_policy:
                if (current_policy.get('srcaddr') == 'all' and
                    current_policy.get('dstaddr') == 'all' and
                    current_policy.get('action') == 'accept'):
                    dangerous_rules.append(current_policy.get('id', 'unknown'))
                current_policy = {}
            if 'config firewall policy' in line:
                in_policy = True
            if 'set srcaddr' in line and '"all"' in line:
                current_policy['srcaddr'] = 'all'
            if 'set dstaddr' in line and '"all"' in line:
                current_policy['dstaddr'] = 'all'
            if 'set action accept' in line:
                current_policy['action'] = 'accept'

        if dangerous_rules:
            return FirewallFinding(
                control_id="FW-011",
                status="non_compliant",
                evidence=f"Règles any-any détectées: {dangerous_rules}",
                details="Des règles autorisant tout le trafic ont été trouvées"
            )
        return FirewallFinding(
            control_id="FW-011",
            status="compliant",
            evidence="Aucune règle any-any détectée",
            details=""
        )

    def run_all_checks(self) -> list[FirewallFinding]:
        self.findings.append(self.check_any_any_rules())
        # ... autres checks
        return self.findings
````

---

### **Phase 5 — Rapports & Remédiation** (Semaines 16-18)

| Tâche | Détail |
|-------|--------|
| Génération PDF | Rapport d'audit complet avec jinja2 + weasyprint |
| Export Word | Template .docx personnalisable (python-docx) |
| Plan de remédiation | Priorisation automatique par sévérité et effort |
| Suivi des remédiations | Statut des actions correctives |
| Comparaison | Comparer deux audits dans le temps (progression) |

---

### **Phase 6 — Fonctionnalités Avancées** (Semaines 19+)

| Tâche | Détail |
|-------|--------|
| Multi-tenant | Gestion de plusieurs clients |
| API REST | Intégration avec d'autres outils |
| Scheduling | Planification d'audits récurrents |
| IA/LLM | Suggestions de remédiation assistées par IA |
| Marketplace de référentiels | Partage communautaire |
| Intégration SIEM | Import de données depuis Wazuh, Elastic... |

---

## 🛠️ Stack Technique Recommandée

| Couche | Technologie | Justification |
|--------|------------|---------------|
| Backend | **Python + FastAPI** | Rapide, async, bonne doc auto (Swagger) |
| Frontend | **Vue.js 3 + Vuetify** ou **React + MUI** | Composants riches pour dashboards |
| BDD | **SQLite** (dev) → **PostgreSQL** (prod) | Comme CISO Assistant |
| ORM | **SQLAlchemy + Alembic** | Migrations de schéma |
| Rapports | **Jinja2 + WeasyPrint** | Génération PDF |
| Outils | **python-nmap, paramiko, pywinrm, ldap3** | Collecte automatisée |
| Déploiement | **Docker + Docker Compose** | Facilité de déploiement |
| Auth | **JWT + OAuth2** | Sécurité standard |

---

## 📁 Structure de Projet Suggérée

```
AssistantAudit/
├── backend/
│   ├── app/
│   │   ├── api/           # Routes FastAPI
│   │   ├── core/          # Config, sécurité, settings
│   │   ├── models/        # Modèles SQLAlchemy
│   │   ├── schemas/       # Schémas Pydantic
│   │   ├── services/      # Logique métier
│   │   └── tools/         # Outils intégrés (scanners, parsers)
│   ├── migrations/        # Alembic
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/
│   │   └── services/
├── frameworks/            # Référentiels YAML
│   ├── firewall_audit.yaml
│   ├── switch_audit.yaml
│   ├── server_windows.yaml
│   ├── active_directory.yaml
│   └── ...
├── templates/             # Templates de rapports
│   ├── report_pdf.html
│   └── report_docx.py
├── docker-compose.yml
└── README.md
```

---

## ✅ Prochaine action recommandée

1. **Commencer par Phase 1** : Initialiser le projet, définir le modèle de données
2. **En parallèle** : Convertir vos mini-audits existants en fichiers YAML (Phase 2)
3. Créer un prototype fonctionnel minimal : un référentiel → une campagne → un rapport

Voulez-vous que je commence par initialiser la structure du projet, créer le modèle de données, ou convertir un de vos mini-audits en référentiel YAML ?

User: Alors il faut aussi pensé qu'on va faires Audit M365 pour ça je pensais me baser en backend sur Monkey 365 pour ça

GitHub Copilot: 

# Intégration Monkey365 pour l'Audit M365

Excellente idée ! **Monkey365** est un outil PowerShell open-source mature qui audite M365, Azure AD et Azure. L'intégrer comme moteur backend pour la partie cloud est très pertinent.

---

## 🐒 Ce que Monkey365 couvre déjà

| Domaine | Exemples de checks |
|---------|-------------------|
| **Entra ID (Azure AD)** | MFA, Conditional Access, PIM, Guest policies, Password policies |
| **Exchange Online** | Transport rules, DKIM/DMARC/SPF, Audit logging, Mailbox permissions |
| **SharePoint Online** | Partage externe, accès anonyme, versioning |
| **OneDrive** | Politique de partage, sync client |
| **Teams** | Guest access, external sharing, meeting policies |
| **Compliance Center** | DLP, Retention, eDiscovery, Audit logs |
| **Azure** | NSG, Storage, Key Vault, VMs, RBAC |

---

## 📐 Architecture d'intégration

```
AssistantAudit
│
├── Core Engine
│   ├── Référentiels YAML
│   │   ├── firewall_audit.yaml
│   │   ├── m365_audit.yaml          ◄── Mappé aux règles Monkey365
│   │   ├── azure_ad_audit.yaml      ◄── Mappé aux règles Monkey365
│   │   └── ...
│   │
│   └── Evaluation Engine
│       ├── Local Tools (nmap, parsers...)
│       └── Monkey365 Bridge ◄────────────────────┐
│                                                   │
├── tools/                                          │
│   ├── monkey365_runner/                           │
│   │   ├── executor.py      # Pilote Monkey365     │
│   │   ├── parser.py        # Parse les résultats  │
│   │   ├── mapper.py        # Mappe vers contrôles │
│   │   └── config.py        # Configuration auth   │
│   │                                               │
│   └── ...                                         │
│                                                   │
└── integrations/                                   │
    └── monkey365/           # Submodule ou install  ┘
        └── (clone du repo Monkey365)
```

---

## 🔧 Comment intégrer Monkey365

### Approche 1 : Exécution PowerShell depuis Python (Recommandée)

````python
"""
Bridge Python → Monkey365 (PowerShell)
Exécute Monkey365 et récupère les résultats JSON
"""
import subprocess
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class M365Provider(str, Enum):
    MICROSOFT365 = "Microsoft365"
    AZURE = "Azure"
    ENTRA_ID = "EntraID"


class AuthMethod(str, Enum):
    INTERACTIVE = "interactive"
    CLIENT_CREDENTIALS = "client_credentials"
    CERTIFICATE = "certificate"


@dataclass
class Monkey365Config:
    provider: M365Provider = M365Provider.MICROSOFT365
    auth_method: AuthMethod = AuthMethod.CLIENT_CREDENTIALS
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    certificate_path: Optional[str] = None
    output_dir: str = "./monkey365_output"
    rulesets: list[str] = field(default_factory=lambda: [
        "cis_m365_benchmark"
    ])
    # Plugins spécifiques à exécuter (vide = tous)
    plugins: list[str] = field(default_factory=list)


class Monkey365Executor:
    """
    Exécute Monkey365 via PowerShell et récupère les résultats
    """

    def __init__(self, config: Monkey365Config):
        self.config = config
        self.monkey365_path = self._find_monkey365()
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _find_monkey365(self) -> Path:
        """Localise l'installation de Monkey365"""
        possible_paths = [
            Path("./integrations/monkey365/Invoke-Monkey365.ps1"),
            Path(os.environ.get("MONKEY365_PATH", "")),
        ]
        for p in possible_paths:
            if p.exists():
                return p
        raise FileNotFoundError(
            "Monkey365 non trouvé. Installer avec: "
            "git submodule add https://github.com/silverhack/monkey365 "
            "integrations/monkey365"
        )

    def _build_command(self, scan_id: str) -> str:
        """Construit la commande PowerShell pour Monkey365"""
        output_path = self.output_dir / scan_id

        # Construction du script PowerShell
        ps_script = f"""
        Import-Module '{self.monkey365_path.parent}' -Force

        $params = @{{
            Instance       = '{self.config.provider.value}'
            Analysis       = @({', '.join(f"'{p}'" for p in self._get_analysis_list())})
            ExportTo       = @('JSON', 'HTML')
            OutDir         = '{output_path}'
            TenantId       = '{self.config.tenant_id}'
        }}
        """

        if self.config.auth_method == AuthMethod.CLIENT_CREDENTIALS:
            ps_script += f"""
        $clientSecret = ConvertTo-SecureString '{self.config.client_secret}' -AsPlainText -Force
        $credential = New-Object System.Management.Automation.PSCredential(
            '{self.config.client_id}', $clientSecret
        )
        $params['AppCredential'] = $credential
        $params['ConfidentialApp'] = $true
        """
        elif self.config.auth_method == AuthMethod.CERTIFICATE:
            ps_script += f"""
        $params['ClientId'] = '{self.config.client_id}'
        $params['CertificateThumbprint'] = '{self.config.certificate_path}'
        """

        if self.config.rulesets:
            ruleset_paths = ', '.join(
                f"'{self.monkey365_path.parent / 'rulesets' / r}.json'"
                for r in self.config.rulesets
            )
            ps_script += f"""
        $params['RuleSets'] = @({ruleset_paths})
        """

        ps_script += """
        Invoke-Monkey365 @params
        """

        return ps_script

    def _get_analysis_list(self) -> list[str]:
        """Retourne la liste des plugins/analyses à exécuter"""
        if self.config.plugins:
            return self.config.plugins

        # Par défaut selon le provider
        default_analyses = {
            M365Provider.MICROSOFT365: [
                "ExchangeOnline", "SharePointOnline",
                "MicrosoftTeams", "MicrosoftForms",
                "Purview"
            ],
            M365Provider.ENTRA_ID: [
                "EntraID", "EntraIDIdentityGovernance",
                "ConditionalAccess"
            ],
            M365Provider.AZURE: [
                "Compute", "Networking", "Storage",
                "KeyVault", "RBAC", "Monitor"
            ]
        }
        return default_analyses.get(self.config.provider, [])

    async def run_scan(self, scan_id: str) -> dict:
        """
        Lance un scan Monkey365 et retourne les résultats parsés
        """
        ps_command = self._build_command(scan_id)

        # Écrire le script temporaire
        script_path = self.output_dir / f"{scan_id}_script.ps1"
        script_path.write_text(ps_command, encoding='utf-8')

        try:
            process = subprocess.run(
                [
                    "pwsh", "-NoProfile", "-NonInteractive",
                    "-ExecutionPolicy", "Bypass",
                    "-File", str(script_path)
                ],
                capture_output=True,
                text=True,
                timeout=3600  # 1h max
            )

            if process.returncode != 0:
                return {
                    "status": "error",
                    "scan_id": scan_id,
                    "error": process.stderr,
                    "stdout": process.stdout
                }

            # Parser les résultats JSON générés par Monkey365
            results = self._parse_output(scan_id)
            return {
                "status": "success",
                "scan_id": scan_id,
                "results": results
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "scan_id": scan_id,
                "error": "Scan exceeded 1 hour timeout"
            }
        finally:
            # Nettoyer le script temporaire
            if script_path.exists():
                script_path.unlink()

    def _parse_output(self, scan_id: str) -> list[dict]:
        """Parse les fichiers JSON de sortie Monkey365"""
        output_path = self.output_dir / scan_id
        results = []

        # Monkey365 génère des JSON dans le répertoire de sortie
        for json_file in output_path.rglob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding='utf-8'))
                if isinstance(data, list):
                    results.extend(data)
                elif isinstance(data, dict):
                    results.append(data)
            except json.JSONDecodeError:
                continue

        return results
````

### Mapper les résultats Monkey365 → Référentiel AssistantAudit

````python
"""
Mappe les findings Monkey365 vers les contrôles du référentiel AssistantAudit
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class MappedFinding:
    control_id: str          # ID dans notre référentiel (ex: M365-EXO-001)
    monkey365_rule_id: str   # ID de la règle Monkey365
    title: str
    status: str              # compliant / non_compliant / partial / not_assessed
    severity: str            # critical / high / medium / low / info
    evidence: str            # Preuve collectée
    affected_resources: list[str]
    remediation: str
    cis_reference: Optional[str] = None


class Monkey365Mapper:
    """
    Mappe les résultats Monkey365 vers le format AssistantAudit
    """

    # Mapping entre les règles Monkey365 et nos contrôles
    RULE_MAPPING = {
        # Exchange Online
        "monkey365_eo_audit_enabled": {
            "control_id": "M365-EXO-001",
            "category": "Exchange Online - Journalisation"
        },
        "monkey365_eo_transport_rules": {
            "control_id": "M365-EXO-010",
            "category": "Exchange Online - Transport"
        },
        "monkey365_eo_dkim_enabled": {
            "control_id": "M365-EXO-020",
            "category": "Exchange Online - Authentification Email"
        },
        "monkey365_eo_dmarc_policy": {
            "control_id": "M365-EXO-021",
            "category": "Exchange Online - Authentification Email"
        },

        # Entra ID
        "monkey365_aad_mfa_status": {
            "control_id": "M365-AAD-001",
            "category": "Entra ID - Authentification"
        },
        "monkey365_aad_conditional_access": {
            "control_id": "M365-AAD-010",
            "category": "Entra ID - Accès Conditionnel"
        },
        "monkey365_aad_guest_policy": {
            "control_id": "M365-AAD-020",
            "category": "Entra ID - Identités Externes"
        },
        "monkey365_aad_password_policy": {
            "control_id": "M365-AAD-030",
            "category": "Entra ID - Mots de passe"
        },

        # SharePoint Online
        "monkey365_spo_external_sharing": {
            "control_id": "M365-SPO-001",
            "category": "SharePoint Online - Partage"
        },
        "monkey365_spo_anonymous_links": {
            "control_id": "M365-SPO-002",
            "category": "SharePoint Online - Partage"
        },

        # Teams
        "monkey365_teams_external_access": {
            "control_id": "M365-TEAMS-001",
            "category": "Teams - Accès Externe"
        },
        "monkey365_teams_guest_access": {
            "control_id": "M365-TEAMS-002",
            "category": "Teams - Accès Invité"
        },
    }

    @classmethod
    def map_results(cls, monkey365_results: list[dict]) -> list[MappedFinding]:
        """Convertit les résultats Monkey365 en findings AssistantAudit"""
        mapped = []

        for finding in monkey365_results:
            rule_id = finding.get("idSuffix", finding.get("id", ""))
            mapping = cls.RULE_MAPPING.get(rule_id)

            if not mapping:
                # Règle non mappée — on la garde quand même
                control_id = f"M365-UNMAPPED-{rule_id}"
            else:
                control_id = mapping["control_id"]

            # Monkey365 utilise des niveaux : Good, Warning, Fail, Info, Manual
            status_map = {
                "Good": "compliant",
                "Pass": "compliant",
                "Warning": "partial",
                "Fail": "non_compliant",
                "Info": "info",
                "Manual": "not_assessed"
            }

            severity_map = {
                "critical": "critical",
                "high": "high",
                "medium": "medium",
                "low": "low",
                "info": "info"
            }

            mapped.append(MappedFinding(
                control_id=control_id,
                monkey365_rule_id=rule_id,
                title=finding.get("title", finding.get("checkName", "")),
                status=status_map.get(
                    finding.get("level", finding.get("status", "")),
                    "not_assessed"
                ),
                severity=severity_map.get(
                    finding.get("severity", "medium"), "medium"
                ),
                evidence=str(finding.get("output", finding.get("rawData", ""))),
                affected_resources=finding.get(
                    "affectedResources",
                    finding.get("resources", [])
                ),
                remediation=finding.get(
                    "remediation",
                    finding.get("rationale", "")
                ),
                cis_reference=finding.get("references", {}).get("cis", None)
            ))

        return mapped
````

---

### Référentiel M365 correspondant

````yaml
framework:
  name: "Audit Microsoft 365"
  version: "1.0"
  description: "Référentiel d'audit M365 - basé sur CIS Benchmark et Monkey365"
  engine: "monkey365"  # ◄── Indique le moteur d'évaluation
  
  engine_config:
    provider: "Microsoft365"
    rulesets:
      - "cis_m365_benchmark"
    auth_methods:
      - "client_credentials"
      - "certificate"
      - "interactive"
    required_permissions:
      - "Directory.Read.All"
      - "Policy.Read.All"
      - "SecurityEvents.Read.All"
      - "Exchange.ManageAsApp"

  categories:
    - name: "Entra ID - Authentification"
      controls:
        - id: M365-AAD-001
          title: "MFA activé pour tous les utilisateurs"
          description: "L'authentification multifacteur est obligatoire pour tous les comptes"
          severity: critical
          check_type: automatic
          monkey365_rule: "monkey365_aad_mfa_status"
          cis_reference: "CIS M365 1.1.1"
          remediation: |
            1. Aller dans Entra ID > Sécurité > Accès conditionnel
            2. Créer une politique exigeant le MFA pour tous les utilisateurs
            3. Exclure uniquement les comptes de service avec justification

        - id: M365-AAD-002
          title: "Méthodes d'authentification Legacy bloquées"
          description: "Les protocoles d'authentification legacy (POP, IMAP, SMTP Auth) sont bloqués"
          severity: critical
          check_type: automatic
          monkey365_rule: "monkey365_aad_legacy_auth"
          cis_reference: "CIS M365 1.1.3"

    - name: "Entra ID - Accès Conditionnel"
      controls:
        - id: M365-AAD-010
          title: "Politiques d'accès conditionnel configurées"
          description: "Des politiques CA couvrent les scénarios critiques"
          severity: high
          check_type: automatic
          monkey365_rule: "monkey365_aad_conditional_access"
          sub_checks:
            - "CA bloquant les pays non autorisés"
            - "CA exigeant appareil conforme"
            - "CA bloquant legacy auth"
            - "CA exigeant MFA pour admins"

        - id: M365-AAD-011
          title: "Politique de risque Sign-in configurée"
          description: "Une politique détectant les connexions risquées est active"
          severity: high
          check_type: automatic
          monkey365_rule: "monkey365_aad_signin_risk"

    - name: "Entra ID - Identités Externes"
      controls:
        - id: M365-AAD-020
          title: "Politique d'invitation des invités restrictive"
          description: "Seuls les admins peuvent inviter des utilisateurs externes"
          severity: high
          check_type: automatic
          monkey365_rule: "monkey365_aad_guest_policy"

    - name: "Entra ID - Rôles & Privilèges"
      controls:
        - id: M365-AAD-030
          title: "Nombre de Global Admins limité (2-4)"
          description: "Le nombre de Global Administrators est entre 2 et 4"
          severity: critical
          check_type: automatic
          monkey365_rule: "monkey365_aad_global_admins_count"

        - id: M365-AAD-031
          title: "PIM activé pour les rôles privilégiés"
          description: "Privileged Identity Management est utilisé pour les rôles sensibles"
          severity: high
          check_type: automatic
          monkey365_rule: "monkey365_aad_pim_enabled"

    - name: "Exchange Online - Sécurité"
      controls:
        - id: M365-EXO-001
          title: "Journalisation d'audit activée"
          description: "L'audit unifié est activé dans Exchange Online"
          severity: critical
          check_type: automatic
          monkey365_rule: "monkey365_eo_audit_enabled"
          cis_reference: "CIS M365 3.1.1"

        - id: M365-EXO-020
          title: "DKIM configuré et actif"
          description: "DKIM est configuré pour tous les domaines"
          severity: high
          check_type: automatic
          monkey365_rule: "monkey365_eo_dkim_enabled"

        - id: M365-EXO-021
          title: "DMARC configuré avec policy reject/quarantine"
          description: "Un enregistrement DMARC avec politique enforce existe"
          severity: high
          check_type: automatic
          monkey365_rule: "monkey365_eo_dmarc_policy"

        - id: M365-EXO-022
          title: "SPF configuré correctement"
          description: "L'enregistrement SPF est présent et correctement configuré"
          severity: high
          check_type: automatic
          monkey365_rule: "monkey365_eo_spf_record"

    - name: "SharePoint Online - Partage"
      controls:
        - id: M365-SPO-001
          title: "Partage externe limité"
          description: "Le partage externe est limité aux invités existants ou désactivé"
          severity: high
          check_type: automatic
          monkey365_rule: "monkey365_spo_external_sharing"

        - id: M365-SPO-002
          title: "Liens anonymes désactivés"
          description: "Les liens 'Anyone' ne sont pas autorisés"
          severity: critical
          check_type: automatic
          monkey365_rule: "monkey365_spo_anonymous_links"

    - name: "Teams - Configuration"
      controls:
        - id: M365-TEAMS-001
          title: "Accès externe contrôlé"
          description: "La fédération Teams est limitée aux domaines autorisés"
          severity: medium
          check_type: automatic
          monkey365_rule: "monkey365_teams_external_access"

        - id: M365-TEAMS-002
          title: "Accès invité contrôlé"
          description: "L'accès invité dans Teams est configuré selon la politique"
          severity: medium
          check_type: automatic
          monkey365_rule: "monkey365_teams_guest_access"

    - name: "Conformité & Protection des données"
      controls:
        - id: M365-COMP-001
          title: "Politiques DLP configurées"
          description: "Des politiques de prévention de fuite de données sont actives"
          severity: high
          check_type: semi-automatic
          monkey365_rule: "monkey365_purview_dlp"

        - id: M365-COMP-002
          title: "Rétention des logs d'audit"
          description: "Les logs d'audit sont conservés au minimum 90 jours"
          severity: high
          check_type: automatic
          monkey365_rule: "monkey365_purview_audit_retention"
````

---

## 🔄 Workflow d'un audit M365 dans AssistantAudit

```
┌──────────────────────────────────────────────────────────────┐
│ 1. CRÉATION CAMPAGNE                                         │
│    Auditeur sélectionne le référentiel "Audit M365"          │
│    Configure le tenant (tenant_id, auth method)              │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. SCAN AUTOMATIQUE                                          │
│    AssistantAudit lance Monkey365 via le bridge Python        │
│    ┌─────────────────────────────────────────────┐           │
│    │  pwsh → Invoke-Monkey365 → JSON output      │           │
│    └─────────────────────────────────────────────┘           │
│    Progression affichée en temps réel                        │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. MAPPING AUTOMATIQUE                                       │
│    Résultats Monkey365 → Contrôles du référentiel            │
│    Pré-remplissage des statuts + preuves                     │
│    ┌──────────────────────────────────────┐                  │
│    │ M365-AAD-001: ✅ Compliant (auto)    │                  │
│    │ M365-AAD-010: ❌ Non-Compliant (auto)│                  │
│    │ M365-EXO-001: ⚠️  Partial (auto)     │                  │
│    │ M365-COMP-001: ❔ Manual review       │                  │
│    └──────────────────────────────────────┘                  │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. REVUE MANUELLE                                            │
│    L'auditeur valide/ajuste les résultats auto               │
│    Complete les contrôles manuels                            │
│    Ajoute ses observations                                   │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. RAPPORT                                                   │
│    Génération du rapport d'audit M365 complet                │
│    Avec scores, graphiques, plan de remédiation              │
└──────────────────────────────────────────────────────────────┘
```

---

## 📦 Installation de Monkey365

````powershell
# Installation de Monkey365 comme sous-module

# Option 1: Git submodule
git submodule add https://github.com/silverhack/monkey365.git integrations/monkey365

# Option 2: PowerShell Gallery
Install-Module -Name monkey365 -Scope CurrentUser -Force

# Vérification
Import-Module ./integrations/monkey365 -Force
Get-Command Invoke-Monkey365
````

---

## 📋 Plan mis à jour

| Phase | Contenu | Moteur |
|-------|---------|--------|
| Phase 1 | Fondations & Modèle de données | - |
| Phase 2 | Référentiels (Infra **+ M365**) | - |
| Phase 3 | Interface Utilisateur | - |
| Phase 4a | Outils intégrés infra | nmap, parsers, SSH/WinRM |
| **Phase 4b** | **Outils intégrés M365/Azure** | **Monkey365** |
| Phase 5 | Rapports & Remédiation | - |
| Phase 6 | Fonctionnalités avancées | - |

L'avantage majeur : Monkey365 évolue avec les changements de Microsoft, vous n'avez qu'à maintenir le **mapping** entre leurs règles et vos contrôles.

Voulez-vous que je commence à initialiser la structure du projet, ou que je développe un autre référentiel spécifique ?