# Configuration des outils intégrés

## Vue d'ensemble

| Outil | Description | Dépendances | Variables d'env | Notes |
|---|---|---|---|---|
| **Nmap** | Scan réseau (ports, OS, services) | `nmap` dans le PATH | `NMAP_TIMEOUT` (défaut : 600s) | Flags bloqués : `--script`, `-oN`, `-oG`, `--interactive`. Flags autorisés : `-sS`, `-sT`, `-sV`, `-A`, `-Pn`, `-O` |
| **SSL Checker** | Analyse des certificats TLS | Stdlib Python (`ssl`, `socket`) | — | Teste SSLv3, TLS 1.0 à 1.3. Aucune dépendance externe |
| **SSH Collector** | Collecte de configuration via SSH | `paramiko` | — | Profils : `linux_server`, `opnsense`, `stormshield`, `fortigate`. Collecte : OS, réseau, sécurité, utilisateurs, services, stockage |
| **WinRM Collector** | Collecte de configuration Windows | `pywinrm` | — | Exécution via PowerShell Remoting (WinRM) |
| **AD Auditor** | Énumération Active Directory via LDAP | `ldap3` | — | Collecte : utilisateurs, groupes, GPOs, politiques de mots de passe, délégations, réplication |
| **Monkey365** | Audit M365 / Entra ID / Azure | `pwsh` + modules PS Monkey365 | `MONKEY365_PATH`, `MONKEY365_TIMEOUT` | Authentification interactive (Device Code). Nécessite les modules PowerShell Monkey365 installés |
| **Config Parser** | Analyse de configurations pare-feu | — | — | Fournisseurs supportés : Fortinet, OPNsense. Détection automatique du fournisseur |
| **ORADAD** | Analyse de sécurité AD (ANSSI) | Binaire ORADAD | — | Outil officiel ANSSI pour l'audit de sécurité Active Directory |

## Détails par outil

### Nmap

- **Emplacement** : `backend/app/tools/nmap_tool.py`
- **Timeout** : configurable via `NMAP_TIMEOUT` (secondes). Valeur par défaut : `600`
- **Sécurité** : validation des flags avant exécution — les flags dangereux sont rejetés

### Monkey365

- **Emplacement** : `backend/app/tools/monkey365_tool.py`
- **`MONKEY365_PATH`** : chemin vers le répertoire d'installation de Monkey365
- **`MONKEY365_TIMEOUT`** : timeout d'exécution en secondes
- **Auth** : flux Device Code — l'utilisateur s'authentifie via navigateur

### SSH Collector — Profils disponibles

| Profil | Cible |
|---|---|
| `linux_server` | Serveurs Linux génériques |
| `opnsense` | Pare-feu OPNsense |
| `stormshield` | Appliances Stormshield |
| `fortigate` | Pare-feu Fortinet FortiGate |
