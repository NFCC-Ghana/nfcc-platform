#!/bin/bash

echo "================================================================"
echo "🔍 UNKNOWN FILES INVESTIGATION"
echo "================================================================"
echo ""

# ================================================================
# 1. control_panel.py
# ================================================================
echo "📄 control_panel.py"
echo "-------------------"
echo "Location: hackathon/app/modules/v4/control_panel.py"

if [ -f "hackathon/app/modules/v4/control_panel.py" ]; then
    echo "Exists: ✅"
    
    # Check imports
    echo ""
    echo "Imports found:"
    grep -r "control_panel" hackathon/ src/ --include="*.py" 2>/dev/null | grep -v backup | grep -v archive | grep -v __pycache__ | head -5 || echo "   None found"
    
    # Check if it's imported by dashboard
    echo ""
    echo "Referenced in dashboard.py:"
    grep "control_panel" hackathon/app/pages/dashboard.py 2>/dev/null || echo "   Not found"
    
    # Check git history
    echo ""
    echo "Git history:"
    git log --oneline -- hackathon/app/modules/v4/control_panel.py 2>/dev/null | head -3 || echo "   No git history"
    
    # Check file size
    echo ""
    echo "File size: $(wc -l < hackathon/app/modules/v4/control_panel.py 2>/dev/null || echo 0) lines"
else
    echo "Exists: ❌"
fi

echo ""
echo "---------------------------------------------------"
echo ""

# ================================================================
# 2. impact_assessment.py
# ================================================================
echo "📄 impact_assessment.py"
echo "----------------------"
echo "Location: hackathon/app/modules/v4/impact_assessment.py"

if [ -f "hackathon/app/modules/v4/impact_assessment.py" ]; then
    echo "Exists: ✅"
    
    # Check imports
    echo ""
    echo "Imports found:"
    grep -r "impact_assessment" hackathon/ src/ --include="*.py" 2>/dev/null | grep -v backup | grep -v archive | grep -v __pycache__ | head -5 || echo "   None found"
    
    # Check if it's imported by dashboard
    echo ""
    echo "Referenced in dashboard.py:"
    grep "impact_assessment" hackathon/app/pages/dashboard.py 2>/dev/null || echo "   Not found"
    
    # Check git history
    echo ""
    echo "Git history:"
    git log --oneline -- hackathon/app/modules/v4/impact_assessment.py 2>/dev/null | head -3 || echo "   No git history"
    
    # Check file size
    echo ""
    echo "File size: $(wc -l < hackathon/app/modules/v4/impact_assessment.py 2>/dev/null || echo 0) lines"
else
    echo "Exists: ❌"
fi

echo ""
echo "---------------------------------------------------"
echo ""

# ================================================================
# 3. risk_display.py
# ================================================================
echo "📄 risk_display.py"
echo "-----------------"
echo "Location: hackathon/app/modules/v4/risk_display.py"

if [ -f "hackathon/app/modules/v4/risk_display.py" ]; then
    echo "Exists: ✅"
    
    # Check imports
    echo ""
    echo "Imports found:"
    grep -r "risk_display" hackathon/ src/ --include="*.py" 2>/dev/null | grep -v backup | grep -v archive | grep -v __pycache__ | head -5 || echo "   None found"
    
    # Check if it's imported by dashboard
    echo ""
    echo "Referenced in dashboard.py:"
    grep "risk_display" hackathon/app/pages/dashboard.py 2>/dev/null || echo "   Not found"
    
    # Check git history
    echo ""
    echo "Git history:"
    git log --oneline -- hackathon/app/modules/v4/risk_display.py 2>/dev/null | head -3 || echo "   No git history"
    
    # Check file size
    echo ""
    echo "File size: $(wc -l < hackathon/app/modules/v4/risk_display.py 2>/dev/null || echo 0) lines"
else
    echo "Exists: ❌"
fi

echo ""
echo "---------------------------------------------------"
echo ""

# ================================================================
# 4. dashboard_fixed.py
# ================================================================
echo "📄 dashboard_fixed.py"
echo "--------------------"
echo "Location: hackathon/app/pages/dashboard_fixed.py"

if [ -f "hackathon/app/pages/dashboard_fixed.py" ]; then
    echo "Exists: ✅"
    
    # Check imports
    echo ""
    echo "Imports found:"
    grep -r "dashboard_fixed" hackathon/ src/ --include="*.py" 2>/dev/null | grep -v backup | grep -v archive | grep -v __pycache__ | head -5 || echo "   None found"
    
    # Check git history
    echo ""
    echo "Git history:"
    git log --oneline -- hackathon/app/pages/dashboard_fixed.py 2>/dev/null | head -3 || echo "   No git history"
    
    # Check file size
    echo ""
    echo "File size: $(wc -l < hackathon/app/pages/dashboard_fixed.py 2>/dev/null || echo 0) lines"
else
    echo "Exists: ❌"
fi

echo ""
echo "---------------------------------------------------"
echo ""

# ================================================================
# 5. visual_components_fixed.py
# ================================================================
echo "📄 visual_components_fixed.py"
echo "-----------------------------"
echo "Location: hackathon/app/modules/v4/visual_components_fixed.py"

if [ -f "hackathon/app/modules/v4/visual_components_fixed.py" ]; then
    echo "Exists: ✅"
    
    # Check imports
    echo ""
    echo "Imports found:"
    grep -r "visual_components_fixed" hackathon/ src/ --include="*.py" 2>/dev/null | grep -v backup | grep -v archive | grep -v __pycache__ | head -5 || echo "   None found"
    
    # Check git history
    echo ""
    echo "Git history:"
    git log --oneline -- hackathon/app/modules/v4/visual_components_fixed.py 2>/dev/null | head -3 || echo "   No git history"
    
    # Check file size
    echo ""
    echo "File size: $(wc -l < hackathon/app/modules/v4/visual_components_fixed.py 2>/dev/null || echo 0) lines"
else
    echo "Exists: ❌"
fi

echo ""
echo "---------------------------------------------------"
echo ""

# ================================================================
# 6. railway.json
# ================================================================
echo "📄 railway.json"
echo "---------------"
echo "Location: railway.json"

if [ -f "railway.json" ]; then
    echo "Exists: ✅"
    
    # Check content
    echo ""
    echo "Content:"
    cat railway.json 2>/dev/null | head -20 || echo "   Empty or unreadable"
else
    echo "Exists: ❌"
fi

echo ""
echo "---------------------------------------------------"
echo ""

# ================================================================
# SUMMARY
# ================================================================
echo ""
echo "================================================================"
echo "✅ UNKNOWN FILE INVESTIGATION COMPLETE"
echo "================================================================"
echo ""

echo "📋 RECOMMENDATIONS:"
echo ""

# Determine if files are used
if grep -r "control_panel" hackathon/ src/ --include="*.py" 2>/dev/null | grep -q -v "archive\|backup\|__pycache__"; then
    echo "   control_panel.py -> ✅ KEEP (has imports)"
else
    echo "   control_panel.py -> ⚠️ ARCHIVE (no imports found)"
fi

if grep -r "impact_assessment" hackathon/ src/ --include="*.py" 2>/dev/null | grep -q -v "archive\|backup\|__pycache__"; then
    echo "   impact_assessment.py -> ✅ KEEP (has imports)"
else
    echo "   impact_assessment.py -> ⚠️ ARCHIVE (no imports found)"
fi

if grep -r "risk_display" hackathon/ src/ --include="*.py" 2>/dev/null | grep -q -v "archive\|backup\|__pycache__"; then
    echo "   risk_display.py -> ✅ KEEP (has imports)"
else
    echo "   risk_display.py -> ⚠️ ARCHIVE (no imports found)"
fi

if [ -f "hackathon/app/pages/dashboard_fixed.py" ]; then
    if grep -r "dashboard_fixed" hackathon/ src/ --include="*.py" 2>/dev/null | grep -q -v "archive\|backup\|__pycache__"; then
        echo "   dashboard_fixed.py -> ✅ KEEP (has imports)"
    else
        echo "   dashboard_fixed.py -> ⚠️ ARCHIVE (no imports found)"
    fi
fi

if [ -f "hackathon/app/modules/v4/visual_components_fixed.py" ]; then
    if grep -r "visual_components_fixed" hackathon/ src/ --include="*.py" 2>/dev/null | grep -q -v "archive\|backup\|__pycache__"; then
        echo "   visual_components_fixed.py -> ✅ KEEP (has imports)"
    else
        echo "   visual_components_fixed.py -> ⚠️ ARCHIVE (no imports found)"
    fi
fi

echo ""
echo "================================================================"
