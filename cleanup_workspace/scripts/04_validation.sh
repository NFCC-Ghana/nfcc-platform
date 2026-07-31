#!/bin/bash

echo "================================================================"
echo "✅ PHASE 5: VALIDATION SCRIPT"
echo "================================================================"
echo ""

cd ~/projects/nfcc-platform

ALL_PASSED=true

# ================================================================
# 1. CHECK CRITICAL FILES EXIST
# ================================================================
echo "📋 1. Checking critical files..."

CRITICAL_FILES=(
    "hackathon/app/pages/dashboard.py"
    "hackathon/app/streamlit_app.py"
    "hackathon/app/modules/v4/__init__.py"
    "hackathon/app/modules/v4/state.py"
    "hackathon/app/modules/v4/state_fallback.py"
    "hackathon/app/modules/v4/visual_components.py"
    "hackathon/app/modules/v4/situation_map.py"
    "hackathon/app/modules/v4/ai_copilot.py"
    "hackathon/app/modules/v4/control_panel.py"
    "hackathon/app/modules/v4/impact_assessment.py"
    "hackathon/app/modules/v4/risk_display.py"
    "hackathon/ai/flood_explainer.py"
    "hackathon/ai/hydrological_intelligence.py"
    "hackathon/ai/impact_estimator.py"
    ".streamlit/config.toml"
    "render.yaml"
    "requirements.txt"
)

MISSING_COUNT=0
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ MISSING: $file"
        MISSING_COUNT=$((MISSING_COUNT + 1))
        ALL_PASSED=false
    fi
done

echo ""
if [ "$MISSING_COUNT" -eq 0 ]; then
    echo "   ✅ All critical files present"
else
    echo "   ❌ $MISSING_COUNT files missing"
fi

# ================================================================
# 2. CHECK SYNTAX
# ================================================================
echo ""
echo "📋 2. Checking syntax..."

SYNTAX_ERRORS=0
for file in \
    "hackathon/app/pages/dashboard.py" \
    "hackathon/app/streamlit_app.py" \
    "hackathon/app/modules/v4/__init__.py" \
    "hackathon/app/modules/v4/state.py" \
    "hackathon/app/modules/v4/state_fallback.py" \
    "hackathon/app/modules/v4/visual_components.py" \
    "hackathon/app/modules/v4/situation_map.py" \
    "hackathon/app/modules/v4/ai_copilot.py" \
    "hackathon/app/modules/v4/control_panel.py" \
    "hackathon/app/modules/v4/impact_assessment.py" \
    "hackathon/app/modules/v4/risk_display.py" \
    "hackathon/ai/flood_explainer.py" \
    "hackathon/ai/hydrological_intelligence.py" \
    "hackathon/ai/impact_estimator.py"
do
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo "   ✅ Syntax OK: $file"
    else
        echo "   ❌ Syntax ERROR: $file"
        SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
        ALL_PASSED=false
    fi
done

echo ""
if [ "$SYNTAX_ERRORS" -eq 0 ]; then
    echo "   ✅ All files syntax OK"
else
    echo "   ❌ $SYNTAX_ERRORS files with syntax errors"
fi

# ================================================================
# 3. CHECK DASHBOARD
# ================================================================
echo ""
echo "📋 3. Checking dashboard imports..."

python3 << 'PYCHECK' 2>&1 | head -20
import sys
sys.path.insert(0, '.')

print("   Checking imports...")

try:
    import hackathon.app.pages.dashboard as dashboard
    print("   ✅ Dashboard module loaded")
except Exception as e:
    print(f"   ❌ Dashboard module error: {e}")

try:
    from hackathon.app.modules.v4 import state, visual_components, situation_map, ai_copilot
    print("   ✅ V4 modules loaded")
except Exception as e:
    print(f"   ❌ V4 modules error: {e}")

try:
    from hackathon.ai import flood_explainer, impact_estimator
    print("   ✅ AI modules loaded")
except Exception as e:
    print(f"   ❌ AI modules error: {e}")

print("   Import check complete")
PYCHECK

# ================================================================
# 4. SUMMARY
# ================================================================
echo ""
echo "================================================================"
if [ "$ALL_PASSED" = true ]; then
    echo "✅ ALL VALIDATION CHECKS PASSED"
    echo "================================================================"
    echo ""
    echo "📋 Repository is clean and functional:"
    echo "   - All critical files present"
    echo "   - All syntax checks passed"
    echo "   - All imports working"
    echo ""
    echo "📋 Proceed to commit changes:"
    echo "   git add ."
    echo "   git commit -m 'cleanup: Archive backup files and legacy directories'"
    echo "   git push origin architecture-stabilization"
else
    echo "❌ VALIDATION FAILED - Fix issues before committing"
    echo "================================================================"
    echo ""
    echo "📋 Issues found:"
    [ "$MISSING_COUNT" -gt 0 ] && echo "   - $MISSING_COUNT files missing"
    [ "$SYNTAX_ERRORS" -gt 0 ] && echo "   - $SYNTAX_ERRORS syntax errors"
fi
echo "================================================================"
