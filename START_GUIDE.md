# Guide de Démarrage - AssistantAudit v2.0

## Vue d'ensemble

Le script `start.ps1` gère automatiquement le démarrage complet de la plateforme AssistantAudit, incluant :

- ✅ Vérification des prérequis (Python, Node.js, PowerShell 7+, Git)
- ✅ Configuration automatique de l'environnement (.env)
- ✅ Téléchargement et mise à jour des outils externes (PingCastle, Monkey365)
- ✅ Initialisation de la base de données
- ✅ Installation des dépendances (Python et Node.js)
- ✅ Rotation automatique des logs
- ✅ Démarrage des services backend et frontend
- ✅ Monitoring et auto-restart en cas de crash
- ✅ Arrêt propre avec Ctrl+C

---

## Modes d'Exécution

### Mode Standard (par défaut)

```powershell
.\start.ps1
```

**Caractéristiques :**
- Logs niveau INFO
- Hot-reload désactivé pour les performances
- Démarrage rapide (~10-20s)
- Idéal pour utilisation normale

### Mode Développement (`--dev`)

```powershell
.\start.ps1 --dev
```

**Caractéristiques :**
- **Logs niveau DEBUG** sur tous les composants
- **Hot-reload activé** (backend + frontend avec Turbopack)
- Timestamps millisecondes sur chaque opération
- Affichage détaillé de chaque étape
- Logs SQL des migrations Alembic
- Backend : `--log-level debug` + `--reload`
- Frontend : `next dev --turbo`
- Variables d'environnement : `LOG_LEVEL=DEBUG`

**Cas d'usage :**
- Développement de nouvelles fonctionnalités
- Debug de problèmes complexes
- Inspection des requêtes SQL
- Analyse de performance détaillée

### Mode Production (`--build`)

```powershell
.\start.ps1 --build
```

**Caractéristiques :**
- **Build optimisé** du frontend (`next build`)
- Backend en mode production avec **4 workers** uvicorn
- Pas de hot-reload
- Logs minimaux
- Crash = arrêt du script (pas de redémarrage auto)
- Variables d'environnement : `NODE_ENV=production`

**Cas d'usage :**
- Tests de performance
- Validation avant déploiement
- Démonstrations client

---

## Fonctionnalités Automatiques

### 1. Gestion de l'Environnement (.env)

**Création automatique :**
Si `.env` n'existe pas, le script :
1. Copie `.env.example` → `.env`
2. Génère une `SECRET_KEY` aléatoire sécurisée (64 caractères hex)
3. Configure `LOG_LEVEL=DEBUG` en mode `--dev`

**Variables auto-configurées :**
- `PINGCASTLE_PATH` : Défini automatiquement vers `tools/pingcastle/PingCastle.exe`
- `MONKEY365_PATH` : Défini automatiquement vers `tools/monkey365/Invoke-Monkey365.ps1`

### 2. Téléchargement des Outils Externes

#### PingCastle (Active Directory Audit)

**Première exécution :**
```
git clone --depth 1 https://github.com/netwrix/pingcastle tools/pingcastle
```

**Exécutions suivantes :**
```
git pull origin master  # Mise à jour automatique
```

Le script affiche le commit hash actuel après chaque update.

#### Monkey365 (Microsoft 365 Audit)

**Nouvelle fonctionnalité v2.0 !**

Téléchargement automatique similaire à PingCastle :
```
git clone --depth 1 https://github.com/silverhack/monkey365 tools/monkey365
```

**Prérequis :** PowerShell 7+ (le script affiche un warning si vous utilisez PowerShell 5.1)

### 3. Rotation des Logs

**Configuration :**
- Fichier surveillé : `backend/logs/assistantaudit.log`
- Taille maximale : **10 MB**
- Nombre d'archives : **5** (`.log.1` à `.log.5`)

**Fonctionnement :**
1. Au démarrage, si `assistantaudit.log` > 10 MB :
   - Renommage `.log` → `.log.1`
   - Rotation des archives existantes
   - Suppression de `.log.5` (la plus ancienne)

### 4. Gestion des Processus

#### Fichiers PID

Le script crée des fichiers de tracking :
- `backend/instance/backend.pid` → PID du processus uvicorn
- `frontend/.next/frontend.pid` → PID du processus Next.js

**Avantages :**
- Détection des processus zombies au démarrage
- Cleanup automatique avant libération des ports
- Traçabilité des processus actifs

#### Auto-restart (Mode Dev/Standard)

Si un service crash pendant l'exécution :
```
[!] Le backend s'est arrêté (code 1)
[!] Redémarrage automatique...
[VERBOSE] Backend redémarré avec PID 12345
```

**Note :** En mode `--build`, un crash arrête le script (comportement production).

### 5. Arrêt Propre

Ctrl+C déclenche :
1. Arrêt gracieux des processus (tree kill avec `/T`)
2. Libération des ports 8000 et 3000
3. Suppression des fichiers PID
4. Affichage du temps total d'exécution

---

## Ports et URLs

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| **Backend** | 8000 | http://localhost:8000 | API FastAPI |
| **Frontend** | 3000 | http://localhost:3000 | Interface Next.js |
| **Swagger** | 8000 | http://localhost:8000/docs | Documentation API |
| **ReDoc** | 8000 | http://localhost:8000/redoc | Documentation alternative |

---

## Prérequis

### Obligatoires

| Outil | Version Minimum | Vérification |
|-------|----------------|--------------|
| **Python** | 3.8+ | `python --version` |
| **Node.js** | 18+ | `node --version` |

### Recommandés

| Outil | Version Minimum | Note |
|-------|----------------|------|
| **PowerShell** | 7.0+ | Requis pour Monkey365 |
| **Git** | 2.x | Pour téléchargement auto des outils |
| **Nmap** | 7.x | Pour scanner réseau (optionnel) |

**Installation PowerShell 7 :**
```powershell
# Via winget
winget install Microsoft.PowerShell

# Ou télécharger : https://aka.ms/powershell
```

Ensuite, exécutez le script avec :
```powershell
pwsh .\start.ps1 --dev
```

---

## Logs et Debugging

### Logs Backend

**Emplacement :** `backend/logs/assistantaudit.log`

**Niveaux :**
- Mode standard : `INFO`
- Mode `--dev` : `DEBUG`

**Visualisation temps réel :**
```powershell
Get-Content backend\logs\assistantaudit.log -Wait -Tail 20
```

### Logs Mode Verbose

En mode `--dev`, tous les logs incluent des timestamps précis :

```
[14:32:15.123] [VERBOSE] Vérification du port 8000...
[14:32:15.456] [VERBOSE] Port 8000 libéré après 0s
[14:32:16.789] [OK] venv activé
```

### Affichage des Dernières Erreurs

Si le backend crash au démarrage en mode `--dev`, les 20 dernières lignes du log sont affichées automatiquement.

---

## Dépannage

### "Backend a crashé au démarrage"

1. Vérifier les logs :
   ```powershell
   Get-Content backend\logs\assistantaudit.log -Tail 50
   ```

2. Tester en mode verbose :
   ```powershell
   .\start.ps1 --dev
   ```

3. Vérifier les migrations :
   ```powershell
   cd backend
   python -m alembic current
   ```

### "Port 8000/3000 déjà utilisé"

Le script nettoie automatiquement les ports, mais si le problème persiste :

```powershell
# Trouver le processus
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess

# Tuer le processus (remplacer PID)
taskkill /PID 12345 /F
```

### "PingCastle/Monkey365 non téléchargé"

**Cause :** Git non installé ou problème réseau

**Solution manuelle :**
```powershell
# PingCastle
git clone https://github.com/netwrix/pingcastle tools/pingcastle

# Monkey365
git clone https://github.com/silverhack/monkey365 tools/monkey365
```

### "PowerShell 5.x détecté"

**Warning affiché :**
```
[!] PowerShell 7+ recommandé pour Monkey365 (version actuelle: 5.1)
[!] Téléchargez PowerShell 7: https://aka.ms/powershell
[!] Exécutez ce script avec 'pwsh start.ps1' au lieu de 'powershell start.ps1'
```

**Impact :** Monkey365 nécessite PowerShell 7+ pour fonctionner correctement.

---

## Structure des Fichiers

```
AssistantAudit/
├── start.ps1                          # Script de démarrage (v2.0)
├── .env                               # Configuration (auto-créé)
├── .env.example                       # Template de configuration
├── backend/
│   ├── instance/
│   │   ├── assistantaudit.db         # Base de données SQLite
│   │   └── backend.pid               # PID du backend
│   ├── logs/
│   │   ├── assistantaudit.log        # Log principal
│   │   ├── assistantaudit.log.1      # Archive 1
│   │   └── ...
│   └── requirements.txt              # Dépendances Python
├── frontend/
│   ├── .next/
│   │   └── frontend.pid              # PID du frontend
│   └── package.json                  # Dépendances Node.js
├── tools/
│   ├── pingcastle/                   # Auto-téléchargé
│   │   └── PingCastle.exe
│   └── monkey365/                    # Auto-téléchargé (nouveau!)
│       └── Invoke-Monkey365.ps1
└── venv/                             # Environnement virtuel Python
    └── .deps_stamp                   # Hash requirements.txt
```

---

## Changements v2.0

### Nouvelles Fonctionnalités

✨ **Support Monkey365** : Téléchargement et configuration automatiques  
✨ **Mode `--build`** : Build production optimisé  
✨ **Logs verbeux** : Mode `--dev` avec timestamps et détails complets  
✨ **Rotation logs** : Gestion automatique des fichiers volumineux  
✨ **PID tracking** : Meilleure gestion des processus zombies  
✨ **PowerShell 7 check** : Validation et warnings appropriés  
✨ **Auto .env** : Création et configuration automatiques  

### Améliorations

🔧 **Code restructuré** : Fonctions réutilisables et commentées  
🔧 **Gestion d'erreurs** : Messages plus explicites et contextuels  
🔧 **Performance** : Installation conditionnelle des dépendances  
🔧 **Documentation** : Docstrings PowerShell sur toutes les fonctions  

---

## Exemples d'Utilisation

### Développement quotidien

```powershell
# Lancer avec logs DEBUG
.\start.ps1 --dev

# Dans un autre terminal - suivre les logs
Get-Content backend\logs\assistantaudit.log -Wait

# Arrêter : Ctrl+C dans le terminal start.ps1
```

### Test de performance

```powershell
# Build et démarrage production
.\start.ps1 --build

# Tester l'API
Measure-Command { curl http://localhost:8000/api/v1/health }
```

### Debugging de Monkey365

```powershell
# Vérifier l'installation
Test-Path tools\monkey365\Invoke-Monkey365.ps1

# Tester manuellement (PowerShell 7)
pwsh -File tools\monkey365\Invoke-Monkey365.ps1 -help
```

---

## Contacts et Support

**Documentation complète :** Voir les fichiers `wiki/*.md`  
**Issues GitHub :** https://github.com/T0SAGA97/AssistantAudit/issues  
**Logs d'erreur :** Toujours inclure `backend/logs/assistantaudit.log` dans les rapports de bug

---

## License

Ce projet utilise les outils externes suivants :
- **PingCastle** : https://github.com/netwrix/pingcastle (Licence : Propriétaire Netwrix)
- **Monkey365** : https://github.com/silverhack/monkey365 (Licence : MIT)

Voir les fichiers LICENSE respectifs pour plus de détails.
