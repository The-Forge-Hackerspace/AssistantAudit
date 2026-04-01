# Guide d'exploitation (Runbook)

---

## Prérequis

| Outil | Version minimale | Obligatoire |
|-------|------------------|-------------|
| Python | 3.13+ | Oui |
| Node.js | 18+ | Oui |
| Git | Toute version récente | Oui |
| PowerShell | 7+ | Non (Windows uniquement) |
| Nmap | Toute version | Non (scans réseau) |
| OpenSSL | Toute version | Non (génération certificats) |

---

## Installation Docker (recommandé)

```bash
cp .env.example .env          # Configurer les variables
docker compose up -d          # Démarrer tous les services
docker compose logs -f        # Suivre les logs
docker compose down           # Arrêter
```

---

## Installation manuelle

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate     # Linux/macOS
# ou .venv\Scripts\activate   # Windows
pip install -r requirements.txt
python init_db.py             # Première fois uniquement
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev                   # Développement (port 3000)
# ou npm run build && npm start  # Production
```

---

## Configuration

Copier `.env.example` vers `.env` et renseigner :

| Variable | Exemple | Remarque |
|----------|---------|----------|
| `SECRET_KEY` | Chaîne aléatoire 32+ chars | Critique en production |
| `DATABASE_URL` | `postgresql://user:pass@db/audit` | SQLite accepté en dev |
| `ENCRYPTION_KEY` | Base64 32 bytes | Générer avec `python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"` |
| `FILE_ENCRYPTION_KEY` | Base64 32 bytes | Idem |
| `ENV` | `development` | Mettre `production` pour désactiver Swagger |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | JSON array de strings |

---

## Migrations de base de données

```bash
cd backend
# Créer une migration après modification des modèles
alembic revision --autogenerate -m "description_du_changement"
# Appliquer les migrations
alembic upgrade head
# Revenir en arrière
alembic downgrade -1
```

---

## Tests

```bash
cd backend
pytest -q                     # Tous les tests
pytest -q tests/test_auth.py  # Un fichier spécifique
pytest -q -k "websocket"      # Filtrer par nom
```

---

## Monkey365 (audit Microsoft 365 / Azure)

Monkey365 nécessite une session Windows interactive pour l'authentification OAuth :

```powershell
# Sur un poste Windows avec PowerShell 7+
.\install_m365_modules.ps1    # Installation des modules PS
# Puis lancer un scan depuis l'interface web
```

> Note : l'authentification interactive ne fonctionne pas en mode headless ou depuis un conteneur.

---

## Maintenance

### Rotation des logs

Les logs applicatifs sont gérés par `RotatingFileHandler` :
- Taille maximale : **50 MB** par fichier
- Nombre de backups : **5**
- Emplacement : `DATA_DIR/logs/`

### Sauvegardes base de données

```bash
# PostgreSQL
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
# Restauration
psql $DATABASE_URL < backup_20260101.sql
```

### Gestion des certificats

Placer les fichiers `cert.pem` / `key.pem` dans le volume `app-certs` (chemin : `CERTS_DIR`).

---

## Dépannage

| Problème | Cause probable | Solution |
|----------|----------------|----------|
| Erreur CORS | `CORS_ORIGINS` mal configuré | Vérifier le format JSON array dans `.env` |
| Port 8000 occupé | Autre processus actif | `lsof -i :8000` puis kill, ou changer le port |
| Port 3000 occupé | Idem | `lsof -i :3000` |
| Migrations en échec | Conflit de version Alembic | `alembic stamp head` puis réessayer |
| SQLite vs PostgreSQL | Comportement différent sur JSON | Utiliser PostgreSQL en staging/production |
| `ENCRYPTION_KEY` manquante | Variable non définie | Vérifier `.env` et redémarrer le service |
| Agents déconnectés | Heartbeat timeout | Vérifier la connectivité réseau vers le backend |
