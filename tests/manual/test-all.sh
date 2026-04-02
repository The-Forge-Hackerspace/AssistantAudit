#!/bin/bash
# =============================================================================
# Lancer toutes les suites de tests manuels
# =============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

echo "=========================================="
echo "Execution de TOUTES les suites de tests manuels"
echo "=========================================="

check_jq
check_docker

# Suites de tests (ajouter les nouvelles suites ici)
SUITES=(
    "01-docker-hardening/test-docker-hardening.sh"
)

PASSED=0; FAILED=0
for suite in "${SUITES[@]}"; do
    echo ""
    echo "=========================================="
    echo "Execution: $suite"
    echo "=========================================="
    if "$SCRIPT_DIR/$suite"; then
        ((++PASSED))
        print_status "PASS" "$suite"
    else
        ((++FAILED))
        print_status "FAIL" "$suite"
    fi
done

echo ""
echo "=========================================="
echo "TOTAL: $PASSED suites OK, $FAILED en echec"
echo "=========================================="
[ $FAILED -eq 0 ] && exit 0 || exit 1
