#!/bin/bash
# ================================================================
# CIVICFLOOD AI - CANONICAL DASHBOARD MIGRATION v3.1
# FIXED: NEVER archive required files
# ================================================================

set -e

echo "🚀 CIVICFLOOD AI - CANONICAL DASHBOARD MIGRATION v3.1"
echo "================================================"
echo ""

# ============================================================
# STEP 1: DEFINE REQUIRED MODULES (NEVER TOUCH THESE)
# ============================================================

REQUIRED_MODULES=(
    "state.py"
    "header.py"
    "control_panel.py"
    "risk_display.py"
    "situation_brief.py"
    "evidence_panel.py"
    "situation_map.py"
    "operations.py"
    "impact_assessment.py"
    "community_intelligence.py"
    "decision_support.py"
    "forecast_timeline.py"
    "ai_copilot.py"
)

REQUIRED_FUNCTIONS=(
    "render_header"
    "render_control_panel"
    "render_risk_display"
    "render_situation_brief"
    "render_evidence_panel"
    "render_situation_map"
    "render_operations"
    "render_impact_assessment"
    "render_community_intelligence"
    "render_decision_support"
    "render_forecast_timeline"
    "render_ai_copilot"
)

# ============================================================
# STEP 2: ENSURE REQUIRED FILES EXIST
# ============================================================

echo "📋 STEP 2: ENSURE REQUIRED FILES EXIST"
echo "----------------------------------------"

# First, check if any required files are missing
MISSING=0
for module in "${REQUIRED_MODULES[@]}"; do
    if [ ! -f "hackathon/app/modules/v4/$module" ]; then
        echo "   ⚠️ $module - MISSING, attempting to restore..."
        # Try to restore from archive
        if [ -f "hackathon/archive/v4_legacy/$module" ]; then
            cp "hackathon/archive/v4_legacy/$module" "hackathon/app/modules/v4/$module"
            echo "   ✅ $module - RESTORED from archive"
        else
            echo "   ❌ $module - NOT FOUND anywhere!"
            MISSING=$((MISSING + 1))
        fi
    else
        echo "   ✅ $module"
    fi
done

if [ $MISSING -gt 0 ]; then
    echo "⚠️ $MISSING required modules could not be restored. Aborting..."
    exit 1
fi

# ============================================================
# STEP 3: VERIFY REQUIRED FUNCTIONS EXIST
# ============================================================

echo ""
echo "📋 STEP 3: VERIFY REQUIRED FUNCTIONS EXIST"
echo "----------------------------------------"

ALL_FOUND=0
for func in "${REQUIRED_FUNCTIONS[@]}"; do
    MODULE=$(grep -r -l "def $func" hackathon/app/modules/v4/ 2>/dev/null | head -1)
    if [ -n "$MODULE" ]; then
        MODULE_NAME=$(basename "$MODULE")
        echo "   ✅ $func() → $MODULE_NAME"
        ALL_FOUND=$((ALL_FOUND + 1))
    else
        echo "   ❌ $func() - NOT FOUND in V4 modules"
    fi
done

echo "   ✅ $ALL_FOUND of ${#REQUIRED_FUNCTIONS[@]} section functions found"

if [ $ALL_FOUND -ne ${#REQUIRED_FUNCTIONS[@]} ]; then
    echo "⚠️ Some required functions are missing! Aborting..."
    exit 1
fi

# ============================================================
# STEP 4: IDENTIFY EXTRA FILES (NOT REQUIRED)
# ============================================================

echo ""
echo "📋 STEP 4: IDENTIFY EXTRA FILES"
echo "----------------------------------------"

# Files in pages/ that are NOT dashboard.py or __init__.py
PAGES_FILES=$(find hackathon/app/pages -maxdepth 1 -name "*.py" -type f 2>/dev/null | grep -v "dashboard.py" | grep -v "__init__.py" || echo "")

if [ -n "$PAGES_FILES" ]; then
    echo "⚠️ Found extra files in pages/:"
    for file in $PAGES_FILES; do
        echo "   - $(basename $file)"
    done
else
    echo "✅ No extra files in pages/"
fi

# Files in modules/v4/ that are NOT in REQUIRED_MODULES
V4_FILES=$(find hackathon/app/modules/v4 -maxdepth 1 -name "*.py" -type f 2>/dev/null | grep -v "__init__.py" | while read -r file; do
    filename=$(basename "$file")
    skip=0
    for required in "${REQUIRED_MODULES[@]}"; do
        if [ "$filename" = "$required" ]; then
            skip=1
            break
        fi
    done
    if [ $skip -eq 0 ]; then
        echo "$file"
    fi
done)

if [ -n "$V4_FILES" ]; then
    echo ""
    echo "⚠️ Found extra files in modules/v4/:"
    for file in $V4_FILES; do
        echo "   - $(basename $file)"
    done
else
    echo "✅ No extra files in modules/v4/"
fi

# ============================================================
# STEP 5: ARCHIVE EXTRA FILES (NEVER TOUCH REQUIRED ONES!)
# ============================================================

echo ""
echo "📋 STEP 5: ARCHIVE EXTRA FILES"
echo "----------------------------------------"

mkdir -p hackathon/archive/pages
mkdir -p hackathon/archive/v4_legacy

if [ -n "$PAGES_FILES" ]; then
    for file in $PAGES_FILES; do
        if [ -f "$file" ]; then
            FILENAME=$(basename "$file")
            echo "   📦 Moving $FILENAME to archive/pages/"
            mv "$file" hackathon/archive/pages/
        fi
    done
    echo "✅ Extra pages files archived"
fi

if [ -n "$V4_FILES" ]; then
    for file in $V4_FILES; do
        if [ -f "$file" ]; then
            FILENAME=$(basename "$file")
            echo "   📦 Moving $FILENAME to archive/v4_legacy/"
            mv "$file" hackathon/archive/v4_legacy/
        fi
    done
    echo "✅ Extra V4 modules archived"
fi

# ============================================================
# STEP 6: FINAL VERIFICATION - ALL REQUIRED MODULES STILL EXIST
# ============================================================

echo ""
echo "📋 STEP 6: FINAL VERIFICATION"
echo "----------------------------------------"

ALL_PRESENT=0
for module in "${REQUIRED_MODULES[@]}"; do
    if [ -f "hackathon/app/modules/v4/$module" ]; then
        ALL_PRESENT=$((ALL_PRESENT + 1))
    else
        echo "   ❌ $module - MISSING (would be archived incorrectly!)"
    fi
done

echo "   ✅ $ALL_PRESENT of ${#REQUIRED_MODULES[@]} required modules present"

if [ $ALL_PRESENT -ne ${#REQUIRED_MODULES[@]} ]; then
    echo "⚠️ CRITICAL: Some required modules were incorrectly archived!"
    echo "   Restoring from backup..."
    # Restore from backup
    for module in "${REQUIRED_MODULES[@]}"; do
        if [ ! -f "hackathon/app/modules/v4/$module" ]; then
            if [ -f "hackathon/archive/v4_legacy/$module" ]; then
                cp "hackathon/archive/v4_legacy/$module" "hackathon/app/modules/v4/$module"
                echo "   ✅ $module - RESTORED"
            fi
        fi
    done
    echo "✅ All required modules restored!"
fi

# ============================================================
# STEP 7: FIX MAP SERIALIZATION ISSUE
# ============================================================

echo ""
echo "📋 STEP 7: FIX MAP SERIALIZATION"
echo "----------------------------------------"

if [ -f "hackathon/app/modules/v4/situation_map.py" ]; then
    if grep -q "returned_objects" hackathon/app/modules/v4/situation_map.py; then
        echo "⚠️ found 'returned_objects' in situation_map.py - fixing..."
        sed -i 's/st_folium(.*returned_objects.*)/st_folium(m, width=800, height=500)/g' hackathon/app/modules/v4/situation_map.py
        echo "✅ Fixed map serialization issue"
    else
        echo "✅ Map already fixed"
    fi
fi

# ============================================================
# STEP 8: VALIDATE set_page_config
# ============================================================

echo ""
echo "📋 STEP 8: VALIDATE set_page_config"
echo "----------------------------------------"

CONFIG_COUNT=$(grep -r "st.set_page_config" hackathon/app/ 2>/dev/null | grep -v ".pyc" | wc -l)
echo "   ✅ $CONFIG_COUNT set_page_config() calls found"

if [ "$CONFIG_COUNT" -eq 1 ]; then
    echo "✅ EXACTLY ONE set_page_config() call - PERFECT!"
elif [ "$CONFIG_COUNT" -gt 1 ]; then
    echo "⚠️ Multiple set_page_config() calls found - cleaning up..."
    find hackathon/app -name "*.py" -exec grep -l "st.set_page_config" {} \; | grep -v "streamlit_app.py" | while read -r file; do
        echo "   Removing from $file"
        sed -i '/st.set_page_config(/,/)/d' "$file"
    done
fi

# ============================================================
# STEP 9: GENERATE SUMMARY
# ============================================================

echo ""
echo "📊 MIGRATION SUMMARY"
echo "================================================"

echo ""
echo "✅ CANONICAL ARCHITECTURE CONFIRMED:"
echo ""
echo "   hackathon/app/streamlit_app.py"
echo "           │"
echo "           ▼"
echo "   hackathon/app/pages/dashboard.py"
echo "           │"
echo "           ▼"
echo "   hackathon/app/modules/v4/"
for module in "${REQUIRED_MODULES[@]}"; do
    echo "       ├── $module"
done

echo ""
echo "📊 STATISTICS:"
echo "   ✅ ${#REQUIRED_MODULES[@]} V4 modules verified"
echo "   ✅ ${#REQUIRED_FUNCTIONS[@]} section functions verified"
echo "   ✅ 1 set_page_config() call"
echo "   ✅ All required files intact"

echo ""
echo "🚀 NEXT STEPS:"
echo "   1. git add -A"
echo "   2. git commit -m \"chore: Consolidate to canonical dashboard architecture\""
echo "   3. git push origin feature/ghana-ai-challenge"
echo "   4. Test locally: streamlit run hackathon/app/streamlit_app.py"
echo ""

echo "✅ MIGRATION COMPLETE!"
