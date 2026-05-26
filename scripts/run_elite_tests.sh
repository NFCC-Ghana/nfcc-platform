#!/bin/bash
# Elite resilience test runner

set -e

echo "🚀 Running Elite Resilience Test Suite"
echo "========================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run tests
run_test_category() {
    echo -e "\n${YELLOW}Running $1 tests...${NC}"
    shift
    pytest "$@" -v --tb=short
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1 tests passed${NC}"
    else
        echo -e "${RED}❌ $1 tests failed${NC}"
        exit 1
    fi
}

# Deterministic tests
run_test_category "Deterministic" \
    tests/test_elite_complete.py::TestEliteComprehensive::test_determinism_idempotent \
    tests/test_elite_complete.py::TestEliteComprehensive::test_replay_debugger

# Chaos tests
run_test_category "Chaos" \
    tests/test_elite_complete.py::TestEliteComprehensive::test_chaos_all_strategies \
    tests/test_elite_complete.py::TestEliteComprehensive::test_latency_injection

# Security tests
run_test_category "Security" \
    tests/test_elite_complete.py::TestEliteComprehensive::test_security_dos \
    tests/test_elite_complete.py::TestEliteComprehensive::test_security_injection

# Abuse tests
run_test_category "Abuse" \
    tests/test_elite_complete.py::TestEliteComprehensive::test_abuse_resilience

# Observability tests
run_test_category "Observability" \
    tests/test_elite_complete.py::TestEliteComprehensive::test_observability_complete

# Graceful degradation
run_test_category "Graceful Degradation" \
    tests/test_elite_complete.py::TestEliteComprehensive::test_graceful_degradation

# Full coverage
run_test_category "Full Coverage" \
    tests/test_elite_complete.py --cov=src --cov-report=term-missing

echo -e "\n${GREEN}🎉 All elite resilience tests passed!${NC}"
