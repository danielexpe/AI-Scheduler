#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

cd "$PROJECT_DIR"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  AI Mail Scheduler - Test Suite       ${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

TOTAL_TESTS=0
TOTAL_FAILED=0
TESTS_PASSED=()
TESTS_FAILED=()

run_test_module() {
    local module="$1"
    local name="$2"

    echo -e "${YELLOW}[RUNNING]${NC} $name ($module)"

    if $VENV_PYTHON -m unittest "tests.$module" -v 2>&1; then
        echo -e "${GREEN}[PASSED]${NC}  $name"
        TESTS_PASSED+=("$name")
    else
        echo -e "${RED}[FAILED]${NC}  $name"
        TESTS_FAILED+=("$name")
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
    fi
    echo ""
}

run_test_module "test_auth"       "Password Hashing"
run_test_module "test_models"     "Database Models (SQLite)"
run_test_module "test_scripts"    "Shell Scripts"
run_test_module "test_deepseek"   "DeepSeek Client (mocked)"
run_test_module "test_email"      "Email Sender (mocked)"
run_test_module "test_cron"       "Cron Manager (mocked)"
run_test_module "test_routes"     "Flask Routes (integration)"
run_test_module "test_integration" "Full Integration"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Results                              ${NC}"
echo -e "${CYAN}========================================${NC}"

echo -e "${GREEN}Passed: ${#TESTS_PASSED[@]}${NC}"
for t in "${TESTS_PASSED[@]}"; do
    echo -e "  ${GREEN}\xE2\x9C\x93${NC} $t"
done

echo -e "${RED}Failed: ${#TESTS_FAILED[@]}${NC}"
for t in "${TESTS_FAILED[@]}"; do
    echo -e "  ${RED}\xE2\x9C\x97${NC} $t"
done
echo ""

if [ ${#TESTS_FAILED[@]} -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
