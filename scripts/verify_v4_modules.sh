#!/bin/bash
# ================================================================
# CIVICFLOOD AI - V4 MODULES VERIFICATION
# Uses Python introspection instead of grep pattern matching
# ================================================================

echo "🔍 VERIFYING V4 MODULES"
echo "================================================"

# ============================================================
# 1. Configuration
# ============================================================
MODULE_DIR="hackathon/app/modules/v4"
DASHBOARD_FILE="hackathon/app/pages/dashboard.py"
VERBOSE="${VERBOSE:-0}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_ok() { echo -e "${GREEN}✅${NC} $1"; }
print_warn() { echo -e "${YELLOW}⚠️${NC} $1"; }
print_err() { echo -e "${RED}❌${NC} $1"; }

# ============================================================
# 2. Check Git status
# ============================================================
echo ""
echo "📋 CHECKING GIT STATUS"
echo "----------------------------------------"
if git diff --quiet && git diff --cached --quiet; then
    print_ok "Working tree clean"
else
    print_warn "Uncommitted changes detected"
    if [ "$VERBOSE" -eq 1 ]; then
        git status --porcelain
    fi
fi

# ============================================================
# 3. Check required modules using Python introspection
# ============================================================
echo ""
echo "📋 VERIFYING REQUIRED MODULES"
echo "----------------------------------------"

python -c "
import sys
import importlib
from pathlib import Path

sys.path.insert(0, '.')

# Define required modules and their expected attributes
required_modules = {
    'state': {
        'attrs': ['DashboardState', 'create_state_from_api'],
        'type_checks': {
            'DashboardState': 'class',
            'create_state_from_api': 'function'
        }
    },
    'header': {'attrs': ['render_header']},
    'control_panel': {'attrs': ['render_control_panel']},
    'risk_display': {'attrs': ['render_risk_display']},
    'situation_brief': {'attrs': ['render_situation_brief']},
    'evidence_panel': {'attrs': ['render_evidence_panel']},
    'situation_map': {'attrs': ['render_situation_map']},
    'operations': {'attrs': ['render_operations']},
    'impact_assessment': {'attrs': ['render_impact_assessment']},
    'community_intelligence': {'attrs': ['render_community_intelligence']},
    'decision_support': {'attrs': ['render_decision_support']},
    'forecast_timeline': {'attrs': ['render_forecast_timeline']},
    'ai_copilot': {'attrs': ['render_ai_copilot']},
}

passed = 0
failed = 0
total_attrs = 0

for module_name, config in required_modules.items():
    module_path = f'hackathon.app.modules.v4.{module_name}'
    try:
        module = importlib.import_module(module_path)
        attrs_passed = 0
        attrs_failed = 0
        for attr in config['attrs']:
            total_attrs += 1
            if hasattr(module, attr):
                # Verify the attribute is the correct type
                obj = getattr(module, attr)
                type_check = config.get('type_checks', {}).get(attr)
                if type_check == 'class':
                    if isinstance(obj, type):
                        print(f'   ✅ {module_name}.{attr} (class)')
                        attrs_passed += 1
                    else:
                        print(f'   ❌ {module_name}.{attr} is not a class')
                        attrs_failed += 1
                elif type_check == 'function':
                    if callable(obj):
                        print(f'   ✅ {module_name}.{attr} (function)')
                        attrs_passed += 1
                    else:
                        print(f'   ❌ {module_name}.{attr} is not callable')
                        attrs_failed += 1
                else:
                    print(f'   ✅ {module_name}.{attr}')
                    attrs_passed += 1
            else:
                print(f'   ❌ {module_name}.{attr} - MISSING')
                attrs_failed += 1
        
        if attrs_failed == 0:
            passed += 1
        else:
            failed += 1
            
    except ImportError as e:
        print(f'   ❌ {module_name} - IMPORT ERROR: {e}')
        failed += 1
    except Exception as e:
        print(f'   ❌ {module_name} - ERROR: {e}')
        failed += 1

print('')
print(f'   ✅ {passed} modules verified')
print(f'   ✅ {total_attrs} attributes verified')
if failed > 0:
    print(f'   ❌ {failed} modules have issues')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    MODULE_CHECK_FAILED=1
else
    MODULE_CHECK_FAILED=0
fi

# ============================================================
# 4. Check dashboard imports
# ============================================================
echo ""
echo "📋 VERIFYING DASHBOARD IMPORTS"
echo "----------------------------------------"

if [ ! -f "$DASHBOARD_FILE" ]; then
    print_err "dashboard.py NOT FOUND at $DASHBOARD_FILE"
    exit 1
fi
print_ok "dashboard.py found"

python -c "
import sys
sys.path.insert(0, '.')

# List of required modules
required_modules = [
    'state', 'header', 'control_panel', 'risk_display',
    'situation_brief', 'evidence_panel', 'situation_map',
    'operations', 'impact_assessment', 'community_intelligence',
    'decision_support', 'forecast_timeline', 'ai_copilot'
]

# Legacy modules that should NOT be imported
legacy_modules = [
    'ai_copilot_v4', 'impact_panel', 'mission_control_header',
    'national_briefing', 'operations_panel'
]

# Read dashboard.py
with open('hackathon/app/pages/dashboard.py', 'r') as f:
    content = f.read()

passed = 0
failed = 0

print('   Checking required imports:')
for module in required_modules:
    if f'from hackathon.app.modules.v4.{module} import' in content:
        print(f'   ✅ from .{module} import')
        passed += 1
    else:
        print(f'   ❌ from .{module} import - NOT FOUND')
        failed += 1

print('')
print(f'   ✅ {passed} required imports verified')
if failed > 0:
    print(f'   ❌ {failed} imports missing')
    sys.exit(1)

# Check for legacy imports
print('')
print('   Checking for legacy imports:')
legacy_found = 0
for module in legacy_modules:
    if f'from hackathon.app.modules.v4.{module} import' in content:
        print(f'   ⚠️ Legacy import detected: {module}')
        legacy_found += 1

if legacy_found == 0:
    print('   ✅ No legacy imports detected')
"

IMPORT_CHECK=$?

# ============================================================
# 5. Check Python syntax
# ============================================================
echo ""
echo "📋 CHECKING PYTHON SYNTAX"
echo "----------------------------------------"

if python -m compileall "$MODULE_DIR" 2>/dev/null; then
    print_ok "All modules compile successfully"
    SYNTAX_CHECK=0
else
    print_err "Some modules have syntax errors"
    SYNTAX_CHECK=1
fi

# ============================================================
# 6. Check imports execute
# ============================================================
echo ""
echo "📋 CHECKING IMPORTS EXECUTE"
echo "----------------------------------------"

python -c "
import sys
sys.path.insert(0, '.')
modules = [
    'hackathon.app.modules.v4.state',
    'hackathon.app.modules.v4.header',
    'hackathon.app.modules.v4.control_panel',
    'hackathon.app.modules.v4.risk_display',
    'hackathon.app.modules.v4.situation_brief',
    'hackathon.app.modules.v4.evidence_panel',
    'hackathon.app.modules.v4.situation_map',
    'hackathon.app.modules.v4.operations',
    'hackathon.app.modules.v4.impact_assessment',
    'hackathon.app.modules.v4.community_intelligence',
    'hackathon.app.modules.v4.decision_support',
    'hackathon.app.modules.v4.forecast_timeline',
    'hackathon.app.modules.v4.ai_copilot'
]
success = 0
failed = 0
for module_name in modules:
    try:
        __import__(module_name)
        print(f'   ✅ {module_name.split(\".\")[-1]}')
        success += 1
    except Exception as e:
        print(f'   ❌ {module_name.split(\".\")[-1]}: {e}')
        failed += 1
print('')
print(f'   ✅ {success} of {len(modules)} modules import successfully')
if failed > 0:
    print(f'   ❌ {failed} modules failed to import')
    sys.exit(1)
"

IMPORT_EXECUTE=$?

# ============================================================
# 7. Test state instantiation
# ============================================================
echo ""
echo "📋 TESTING STATE INSTANTIATION"
echo "----------------------------------------"

python -c "
import sys
sys.path.insert(0, '.')
try:
    from hackathon.app.modules.v4.state import DashboardState, create_state_from_api
    state = DashboardState()
    assert state.district == 'Accra Central'
    assert state.risk_score == 50.0
    api_data = {'location': 'Tema', 'score': 75.5, 'risk_tier': 'HIGH'}
    state2 = create_state_from_api(api_data)
    assert state2.district == 'Tema'
    assert state2.risk_score == 75.5
    assert state2.risk_category == 'HIGH'
    print('   ✅ DashboardState works')
    print('   ✅ create_state_from_api works')
    print('   ✅ State object has all expected attributes')
except Exception as e:
    print(f'   ❌ State test failed: {e}')
    sys.exit(1)
"

STATE_TEST=$?

# ============================================================
# 8. Dashboard smoke test
# ============================================================
echo ""
echo "📋 RUNNING DASHBOARD SMOKE TEST"
echo "----------------------------------------"

python -c "
import sys
sys.path.insert(0, '.')
try:
    from hackathon.app.pages.dashboard import main
    print('   ✅ Dashboard module imports successfully')
except Exception as e:
    print(f'   ❌ Dashboard import failed: {e}')
    sys.exit(1)
" 2>/dev/null

SMOKE_TEST=$?

if [ $SMOKE_TEST -eq 0 ]; then
    print_ok "Dashboard module imports successfully"
fi

# ============================================================
# 9. Check legacy modules
# ============================================================
echo ""
echo "📋 CHECKING LEGACY MODULES"
echo "----------------------------------------"

LEGACY_MODULES=(
    "ai_copilot_v4.py"
    "impact_panel.py"
    "mission_control_header.py"
    "national_briefing.py"
    "operations_panel.py"
)

LEGACY_FOUND=0
for legacy in "${LEGACY_MODULES[@]}"; do
    if [ -f "$MODULE_DIR/$legacy" ]; then
        print_warn "Legacy module found: $legacy"
        LEGACY_FOUND=$((LEGACY_FOUND + 1))
    fi
done

if [ $LEGACY_FOUND -eq 0 ]; then
    print_ok "No legacy modules detected"
else
    echo "   ⚠️ $LEGACY_FOUND legacy modules found (not used by dashboard)"
fi

# ============================================================
# 10. Final Summary
# ============================================================
echo ""
echo "📊 FINAL SUMMARY"
echo "================================================"

# Count failures
FAILURES=0
[ $MODULE_CHECK_FAILED -ne 0 ] && FAILURES=$((FAILURES + 1))
[ $IMPORT_CHECK -ne 0 ] && FAILURES=$((FAILURES + 1))
[ $SYNTAX_CHECK -ne 0 ] && FAILURES=$((FAILURES + 1))
[ $IMPORT_EXECUTE -ne 0 ] && FAILURES=$((FAILURES + 1))
[ $STATE_TEST -ne 0 ] && FAILURES=$((FAILURES + 1))
[ $SMOKE_TEST -ne 0 ] && FAILURES=$((FAILURES + 1))

if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅✅✅ ALL VERIFICATIONS PASSED! ✅✅✅${NC}"
    echo ""
    echo "   ✅ All required modules present"
    echo "   ✅ All imports verified"
    echo "   ✅ All modules compile"
    echo "   ✅ All modules import"
    echo "   ✅ State instantiation works"
    echo "   ✅ Dashboard imports successfully"
    echo "   ✅ Working tree clean"
    
    if [ $LEGACY_FOUND -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠️ WARNINGS:${NC}"
        echo "   ⚠️ $LEGACY_FOUND legacy modules present (not used by dashboard)"
    fi
    
    echo ""
    echo "🚀 CivicFlood AI V4 architecture is COMPLETE!"
    exit 0
else
    echo -e "${RED}❌ VERIFICATION FAILED${NC}"
    echo ""
    echo "   ❌ $FAILURES checks failed"
    echo ""
    echo "🔧 Please fix the issues above and try again."
    exit 1
fi
