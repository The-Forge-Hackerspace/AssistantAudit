#!/usr/bin/env bash
# ============================================================
#  AssistantAudit — Script de démarrage (Linux / macOS)
# ============================================================
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/venv"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${CYAN}[AssistantAudit]${NC} $1"; }
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
fail()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

cleanup() {
    log "Arrêt des services..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && ok "Backend arrêté"
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && ok "Frontend arrêté"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── En-tête ──
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         AssistantAudit v2.0.0                ║${NC}"
echo -e "${CYAN}║     Plateforme d'audit d'infrastructure IT   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Vérification des prérequis ──
log "Vérification des prérequis..."

command -v python3 >/dev/null 2>&1 || fail "Python 3 requis. Installez-le : https://python.org"
command -v node >/dev/null 2>&1    || fail "Node.js requis. Installez-le : https://nodejs.org"
command -v npm >/dev/null 2>&1     || fail "npm requis."

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
NODE_VERSION=$(node --version 2>&1)
ok "Python $PYTHON_VERSION"
ok "Node.js $NODE_VERSION"

if command -v nmap >/dev/null 2>&1; then
    NMAP_VERSION=$(nmap --version 2>&1 | head -1)
    ok "$NMAP_VERSION"
else
    warn "Nmap non trouvé — le scanner réseau ne fonctionnera pas"
fi

# ── Environnement virtuel Python ──
if [ ! -d "$VENV_DIR" ]; then
    log "Création de l'environnement virtuel Python..."
    python3 -m venv "$VENV_DIR"
    ok "venv créé dans $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
ok "venv activé"

# ── Dépendances backend ──
log "Installation des dépendances backend..."
pip install -q -r "$BACKEND_DIR/requirements.txt"
ok "Dépendances Python installées"

# ── Initialisation BDD ──
if [ ! -f "$BACKEND_DIR/instance/assistantaudit.db" ]; then
    log "Première exécution — initialisation de la base de données..."
    cd "$BACKEND_DIR"
    python init_db.py
    cd "$ROOT_DIR"
    ok "Base de données initialisée (admin / Admin@2026!)"
else
    ok "Base de données existante détectée"
fi

# ── Migrations Alembic ──
log "Application des migrations..."
cd "$BACKEND_DIR"
python -m alembic upgrade head 2>/dev/null || warn "Migrations déjà à jour ou stamp nécessaire"
cd "$ROOT_DIR"

# ── Dépendances frontend ──
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    log "Installation des dépendances frontend..."
    cd "$FRONTEND_DIR"
    npm install --silent
    cd "$ROOT_DIR"
    ok "Dépendances Node.js installées"
else
    ok "node_modules existant"
fi

# ── Démarrage backend ──
log "Démarrage du backend (port $BACKEND_PORT)..."
cd "$ROOT_DIR"
python -m uvicorn backend.app.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --reload \
    --log-level info &
BACKEND_PID=$!

# Attendre que le backend soit prêt
for i in $(seq 1 30); do
    if curl -s "http://localhost:$BACKEND_PORT/api/v1/health" >/dev/null 2>&1; then
        ok "Backend prêt sur http://localhost:$BACKEND_PORT"
        break
    fi
    if [ "$i" -eq 30 ]; then
        fail "Le backend n'a pas démarré dans les 30 secondes"
    fi
    sleep 1
done

# ── Démarrage frontend ──
log "Démarrage du frontend (port $FRONTEND_PORT)..."
cd "$FRONTEND_DIR"
npm run dev -- --port "$FRONTEND_PORT" &
FRONTEND_PID=$!
cd "$ROOT_DIR"

sleep 3
ok "Frontend prêt sur http://localhost:$FRONTEND_PORT"

# ── Récapitulatif ──
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Tout est prêt !                    ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Frontend  : http://localhost:$FRONTEND_PORT          ║${NC}"
echo -e "${GREEN}║  API       : http://localhost:$BACKEND_PORT           ║${NC}"
echo -e "${GREEN}║  Swagger   : http://localhost:$BACKEND_PORT/docs      ║${NC}"
echo -e "${GREEN}║  Login     : admin / Admin@2026!             ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Ctrl+C pour arrêter les services            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Garder le script en vie ──
wait
