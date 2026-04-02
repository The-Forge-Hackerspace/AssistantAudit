#!/bin/bash
# Configuration partagee pour les scripts de test manuels
export BASE_URL="${BASE_URL:-http://localhost:8000}"
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export NC='\033[0m'

print_status() {
    local status="$1"; local message="$2"
    case $status in
        "PASS") echo -e "${GREEN}[PASS]${NC} $message" ;;
        "FAIL") echo -e "${RED}[FAIL]${NC} $message" ;;
        "WARN") echo -e "${YELLOW}[WARN]${NC} $message" ;;
        "INFO") echo -e "[INFO] $message" ;;
    esac
}

check_jq() {
    command -v jq &> /dev/null || { echo "Erreur: jq requis (apt-get install jq)"; exit 1; }
}

check_docker() {
    command -v docker &> /dev/null || { echo "Erreur: docker requis"; exit 1; }
    docker compose version &> /dev/null || { echo "Erreur: docker compose requis"; exit 1; }
    print_status "INFO" "Docker et Docker Compose disponibles"
}

check_api() {
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/health" 2>/dev/null)
    if [ "$response" != "200" ]; then
        echo "Erreur: API non joignable a $BASE_URL (HTTP $response)"
        exit 1
    fi
    print_status "INFO" "API joignable a $BASE_URL"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export SCRIPT_DIR
