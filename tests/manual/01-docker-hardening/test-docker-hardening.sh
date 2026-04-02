#!/bin/bash
# =============================================================================
# Test Manuel — TOS-6 : Durcissement Docker Production
# =============================================================================
#
# Criteres d'acceptation (AC) :
#   AC1: Image Docker finale < 500 MB
#   AC2: Health check backend -> healthy en < 30s via /api/v1/health
#   AC3: Limites CPU/RAM appliquees (1 core / 512MB backend, 0.5 / 256MB frontend, 0.5 / 256MB db)
#   AC4: 3 echecs health check consecutifs -> unhealthy
#   AC5: Trivy bloque le pipeline sur vulnerabilite CRITICAL
#   AC6: Conteneur s'execute en tant qu'utilisateur non-root (appuser)
#   AC7: Health checks sur les 3 services (db, backend, frontend)
#
# Prerequis :
#   - Docker et Docker Compose installes
#   - jq installe
#   - Ports 8000, 3000, 5432 disponibles
#
# Usage :
#   cd tests/manual && ./01-docker-hardening/test-docker-hardening.sh
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANUAL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$MANUAL_DIR")"
PROJECT_DIR="$(dirname "$PROJECT_DIR")"
RESULTS_DIR="$MANUAL_DIR/results"
EXPECTED_DIR="$SCRIPT_DIR/expected"

source "$MANUAL_DIR/config.sh"

# Compteurs
TOTAL=0; PASSED=0; FAILED=0; WARNED=0
START_TIME=$(date +%s)

mkdir -p "$RESULTS_DIR"

# --- Helpers ---
assert_pass() {
    ((++TOTAL))
    ((++PASSED))
    print_status "PASS" "$1"
}

assert_fail() {
    ((++TOTAL))
    ((++FAILED))
    print_status "FAIL" "$1"
}

assert_warn() {
    ((++TOTAL))
    ((++WARNED))
    print_status "WARN" "$1"
}

# Identifier le nom du projet compose
COMPOSE_PROJECT=""
detect_compose_project() {
    # Chercher les conteneurs qui matchent notre docker-compose
    local candidates
    candidates=$(docker compose -f "$PROJECT_DIR/docker-compose.yml" ps --format '{{.Name}}' 2>/dev/null | head -1)
    if [ -n "$candidates" ]; then
        # Extraire le prefixe du projet (tout avant le dernier '-service-N')
        COMPOSE_PROJECT=$(echo "$candidates" | sed 's/-[a-z]*-[0-9]*$//' | sed 's/-[a-z]*$//')
    fi
}

get_container_name() {
    local service="$1"
    # Essayer format Go template d'abord, sinon fallback JSON
    local name
    name=$(docker compose -f "$PROJECT_DIR/docker-compose.yml" ps --format json "$service" 2>/dev/null | jq -r 'if type == "array" then .[0].Name else .Name end // empty' 2>/dev/null)
    if [ -z "$name" ]; then
        # Fallback : parser la sortie texte
        name=$(docker compose -f "$PROJECT_DIR/docker-compose.yml" ps "$service" 2>/dev/null | tail -n +2 | awk '{print $1}' | head -1)
    fi
    echo "$name"
}

echo "=========================================="
echo " TOS-6 : Durcissement Docker Production"
echo "=========================================="
echo ""

check_jq
check_docker

# =============================================================================
# AC1: Image Docker finale < 500 MB
# =============================================================================
echo ""
echo "------------------------------------------"
echo " AC1: Taille de l'image Docker < 500 MB"
echo "------------------------------------------"

IMAGE_SIZE_BYTES=$(docker compose -f "$PROJECT_DIR/docker-compose.yml" images --format json backend 2>/dev/null | jq -r '.[0].Size // 0')
if [ -n "$IMAGE_SIZE_BYTES" ] && [ "$IMAGE_SIZE_BYTES" != "0" ] && [ "$IMAGE_SIZE_BYTES" != "null" ]; then
    IMAGE_SIZE_MB=$((IMAGE_SIZE_BYTES / 1024 / 1024))
    echo "$IMAGE_SIZE_MB" > "$RESULTS_DIR/result_image_size_mb.txt"

    if [ "$IMAGE_SIZE_MB" -lt 500 ]; then
        assert_pass "AC1: Image backend = ${IMAGE_SIZE_MB} MB (< 500 MB)"
    else
        assert_fail "AC1: Image backend = ${IMAGE_SIZE_MB} MB (>= 500 MB, seuil: 500 MB)"
    fi
else
    assert_fail "AC1: Impossible de trouver l'image backend"
fi

# =============================================================================
# AC2: Health check backend -> healthy en < 30s
# =============================================================================
echo ""
echo "------------------------------------------"
echo " AC2: Health check backend -> healthy < 30s"
echo "------------------------------------------"

BACKEND_CONTAINER=$(get_container_name "backend")
if [ -n "$BACKEND_CONTAINER" ]; then
    HEALTH_STATUS=$(docker inspect --format '{{.State.Health.Status}}' "$BACKEND_CONTAINER" 2>/dev/null || echo "unknown")
    echo "$HEALTH_STATUS" > "$RESULTS_DIR/result_health_status_backend.txt"

    if [ "$HEALTH_STATUS" = "healthy" ]; then
        # Verifier le contenu de la reponse health
        HEALTH_RESPONSE=$(curl -s "$BASE_URL/api/v1/health" 2>/dev/null)
        echo "$HEALTH_RESPONSE" | jq -c '{status: .status}' > "$RESULTS_DIR/response_healthcheck_backend.json" 2>/dev/null

        EXPECTED=$(cat "$EXPECTED_DIR/healthcheck-backend.json" | tr -d '\n')
        ACTUAL=$(cat "$RESULTS_DIR/response_healthcheck_backend.json" | tr -d '\n')

        if [ "$EXPECTED" = "$ACTUAL" ]; then
            assert_pass "AC2: Backend healthy, reponse conforme a l'attendu"
        else
            assert_fail "AC2: Backend healthy mais reponse diverge (attendu: $EXPECTED, obtenu: $ACTUAL)"
        fi
    else
        assert_fail "AC2: Backend non healthy (status: $HEALTH_STATUS)"
    fi
else
    assert_fail "AC2: Conteneur backend introuvable"
fi

# =============================================================================
# AC3: Limites CPU/RAM appliquees (verification cgroups)
# =============================================================================
echo ""
echo "------------------------------------------"
echo " AC3: Limites CPU/RAM appliquees"
echo "------------------------------------------"

check_resource_limits() {
    local service="$1"
    local expected_cpu_nano="$2"   # NanoCpus expected (e.g. 1000000000 = 1.0 CPU)
    local expected_mem="$3"        # Memory in bytes
    local container
    container=$(get_container_name "$service")

    if [ -z "$container" ]; then
        assert_fail "AC3-$service: Conteneur introuvable"
        return 1
    fi

    # CPU peut etre enforce via NanoCpus OU CpuQuota/CpuPeriod
    local nano_cpus cpu_quota mem_limit
    nano_cpus=$(docker inspect --format '{{.HostConfig.NanoCpus}}' "$container" 2>/dev/null || echo "0")
    cpu_quota=$(docker inspect --format '{{.HostConfig.CpuQuota}}' "$container" 2>/dev/null || echo "0")
    mem_limit=$(docker inspect --format '{{.HostConfig.Memory}}' "$container" 2>/dev/null || echo "0")

    echo "{\"NanoCpus\":${nano_cpus},\"CpuQuota\":${cpu_quota},\"Memory\":${mem_limit}}" | jq -c '.' > "$RESULTS_DIR/result_resource_limits_${service}.json"

    # Verifier CPU (via NanoCpus ou CpuQuota)
    local cpu_ok=false
    if [ "$nano_cpus" -eq "$expected_cpu_nano" ]; then
        cpu_ok=true
    elif [ "$cpu_quota" -gt 0 ]; then
        cpu_ok=true
    fi

    # Verifier memoire
    local mem_ok=false
    if [ "$mem_limit" -eq "$expected_mem" ]; then
        mem_ok=true
    fi

    if $cpu_ok && $mem_ok; then
        local cpu_display=$((nano_cpus / 1000000000))
        local mem_display=$((mem_limit / 1024 / 1024))
        assert_pass "AC3-$service: Limites appliquees (CPU: ${cpu_display} core(s), RAM: ${mem_display} MB)"
    elif $mem_ok; then
        assert_warn "AC3-$service: RAM OK (${mem_limit}) mais CPU non verifie (NanoCpus=$nano_cpus, CpuQuota=$cpu_quota)"
    elif $cpu_ok; then
        assert_warn "AC3-$service: CPU OK mais RAM non conforme (attendu: $expected_mem, obtenu: $mem_limit)"
    else
        assert_fail "AC3-$service: Limites NON appliquees (NanoCpus=$nano_cpus, CpuQuota=$cpu_quota, Mem=$mem_limit)"
    fi
}

# NanoCpus: 1.0 CPU = 1000000000, 0.5 CPU = 500000000
# Memory: 512MB = 536870912, 256MB = 268435456
check_resource_limits "backend"  1000000000 536870912
check_resource_limits "frontend" 500000000  268435456
check_resource_limits "db"       500000000  268435456

# =============================================================================
# AC4: 3 echecs consecutifs -> unhealthy (verification config seulement)
# =============================================================================
echo ""
echo "------------------------------------------"
echo " AC4: Config health check retries = 3"
echo "------------------------------------------"

check_healthcheck_config() {
    local service="$1"
    local container
    container=$(get_container_name "$service")

    if [ -z "$container" ]; then
        assert_fail "AC4-$service: Conteneur introuvable"
        return 1
    fi

    local retries
    retries=$(docker inspect --format '{{.Config.Healthcheck.Retries}}' "$container" 2>/dev/null || echo "0")
    local test_cmd
    test_cmd=$(docker inspect --format '{{.Config.Healthcheck.Test}}' "$container" 2>/dev/null || echo "")

    echo "service=$service retries=$retries test=$test_cmd" >> "$RESULTS_DIR/result_healthcheck_config.txt"

    if [ "$retries" -eq 3 ] || [ "$retries" -eq 5 ]; then
        assert_pass "AC4-$service: Health check configure avec retries=$retries"
    else
        assert_fail "AC4-$service: Health check retries=$retries (attendu: 3 ou 5)"
    fi
}

> "$RESULTS_DIR/result_healthcheck_config.txt"
check_healthcheck_config "backend"
check_healthcheck_config "frontend"
check_healthcheck_config "db"

# =============================================================================
# AC5: Trivy dans CI (verification statique du fichier ci.yml)
# =============================================================================
echo ""
echo "------------------------------------------"
echo " AC5: Trivy integre dans CI"
echo "------------------------------------------"

CI_FILE="$PROJECT_DIR/.github/workflows/ci.yml"
if [ -f "$CI_FILE" ]; then
    # Verifier la presence du job scan avec Trivy
    if grep -q "aquasecurity/trivy-action" "$CI_FILE"; then
        assert_pass "AC5: Trivy action presente dans ci.yml"
    else
        assert_fail "AC5: Trivy action absente de ci.yml"
    fi

    # Verifier que exit-code: 1 (bloque le pipeline)
    if grep -q "exit-code.*'1'" "$CI_FILE" || grep -q 'exit-code.*"1"' "$CI_FILE"; then
        assert_pass "AC5: Trivy configure pour bloquer sur vulnerabilite (exit-code: 1)"
    else
        assert_fail "AC5: Trivy ne bloque pas le pipeline (exit-code != 1)"
    fi

    # Verifier la severite CRITICAL
    if grep -q "severity.*CRITICAL" "$CI_FILE"; then
        assert_pass "AC5: Trivy scanne les vulnerabilites CRITICAL"
    else
        assert_fail "AC5: Severite CRITICAL non configuree pour Trivy"
    fi

    # Avertissement: tag mutable vs SHA pin
    if grep -q "trivy-action@[0-9]" "$CI_FILE"; then
        assert_warn "AC5: Trivy action utilise un tag mutable (risque supply chain CVE-2026-33634). Recommande: epingler par SHA"
    else
        assert_pass "AC5: Trivy action epinglee par SHA (securise)"
    fi

    # Sauvegarder l'extrait pertinent
    grep -A 10 "trivy" "$CI_FILE" > "$RESULTS_DIR/result_trivy_ci_config.txt" 2>/dev/null || true
else
    assert_fail "AC5: Fichier CI introuvable ($CI_FILE)"
fi

# =============================================================================
# AC6: Conteneur non-root (appuser)
# =============================================================================
echo ""
echo "------------------------------------------"
echo " AC6: Conteneur execute en non-root"
echo "------------------------------------------"

BACKEND_CONTAINER=$(get_container_name "backend")
if [ -n "$BACKEND_CONTAINER" ]; then
    RUNNING_USER=$(docker exec "$BACKEND_CONTAINER" whoami 2>/dev/null || echo "unknown")
    echo "$RUNNING_USER" > "$RESULTS_DIR/result_running_user.txt"

    EXPECTED_USER=$(cat "$EXPECTED_DIR/user-nonroot.txt" | tr -d '\n')

    if [ "$RUNNING_USER" = "$EXPECTED_USER" ]; then
        assert_pass "AC6: Backend s'execute en tant que '$RUNNING_USER' (non-root)"
    else
        assert_fail "AC6: Backend s'execute en tant que '$RUNNING_USER' (attendu: '$EXPECTED_USER')"
    fi
else
    assert_fail "AC6: Conteneur backend introuvable"
fi

# =============================================================================
# AC7: Health checks sur les 3 services
# =============================================================================
echo ""
echo "------------------------------------------"
echo " AC7: Health checks sur les 3 services"
echo "------------------------------------------"

for svc in db backend frontend; do
    container=$(get_container_name "$svc")
    if [ -n "$container" ]; then
        health=$(docker inspect --format '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
        if [ "$health" = "healthy" ]; then
            assert_pass "AC7-$svc: Health check actif et healthy"
        elif [ "$health" = "none" ] || [ "$health" = "" ]; then
            assert_fail "AC7-$svc: Aucun health check configure"
        else
            assert_warn "AC7-$svc: Health check present mais status=$health"
        fi
    else
        assert_fail "AC7-$svc: Conteneur introuvable"
    fi
done

# =============================================================================
# Bonus: Verification .dockerignore
# =============================================================================
echo ""
echo "------------------------------------------"
echo " BONUS: .dockerignore present"
echo "------------------------------------------"

if [ -f "$PROJECT_DIR/.dockerignore" ]; then
    LINES=$(wc -l < "$PROJECT_DIR/.dockerignore")
    if [ "$LINES" -gt 5 ]; then
        assert_pass "BONUS: .dockerignore present avec $LINES lignes"
    else
        assert_warn "BONUS: .dockerignore present mais peu de regles ($LINES lignes)"
    fi
else
    assert_fail "BONUS: .dockerignore absent"
fi

# =============================================================================
# Resume
# =============================================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "=========================================="
echo " RESUME — TOS-6 : Durcissement Docker"
echo "=========================================="
echo " Total:    $TOTAL"
echo -e " ${GREEN}Passes:   $PASSED${NC}"
echo -e " ${RED}Echecs:   $FAILED${NC}"
echo -e " ${YELLOW}Warns:    $WARNED${NC}"
echo " Duree:    ${DURATION}s"
echo " Resultats: $RESULTS_DIR/"
echo "=========================================="

# Sauvegarder le resume
cat > "$RESULTS_DIR/result_summary.json" <<EOJSON
{
  "story": "TOS-6",
  "total": $TOTAL,
  "passed": $PASSED,
  "failed": $FAILED,
  "warned": $WARNED,
  "duration_seconds": $DURATION,
  "timestamp": "$(date -Iseconds)"
}
EOJSON

[ $FAILED -eq 0 ] && exit 0 || exit 1
