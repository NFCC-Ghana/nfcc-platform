#!/usr/bin/env bash
set -euo pipefail

# ================================================================
# NFCC DISCOVERY SCRIPT - PHASE 1
# ================================================================
# This script performs READ-ONLY discovery of the repository.
# It does NOT delete, move, rename, or modify any files.
# All output is written to cleanup_workspace/reports/
# ================================================================

# Get repository root (works from anywhere)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# Create workspace
mkdir -p cleanup_workspace/reports
mkdir -p cleanup_workspace/manifests
mkdir -p cleanup_workspace/scripts
mkdir -p cleanup_workspace/archive_candidates

TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
BRANCH="$(git branch --show-current 2>/dev/null || echo "unknown")"
COMMIT="$(git rev-parse HEAD 2>/dev/null | cut -c1-8 || echo "unknown")"

echo "================================================================"
echo "🔍 NFCC DISCOVERY SCRIPT - PHASE 1"
echo "================================================================"
echo ""
echo "Repository: $REPO_ROOT"
echo "Branch: $BRANCH"
echo "Commit: $COMMIT"
echo "Timestamp: $TIMESTAMP"
echo ""
echo "⚠️  THIS IS READ-ONLY - NO FILES WILL BE CHANGED"
echo ""

# ================================================================
# 1. REPOSITORY INVENTORY
# ================================================================
echo "📊 1. GENERATING REPOSITORY INVENTORY..."

# All files (excluding common ignored paths)
find . \
    -not -path "./.git/*" \
    -not -path "./.venv/*" \
    -not -path "./venv/*" \
    -not -path "./__pycache__/*" \
    -not -path "./.pytest_cache/*" \
    -not -path "./htmlcov/*" \
    -not -path "./reports/*" \
    -not -path "./cleanup_workspace/*" \
    -type f \
    | sort \
    > cleanup_workspace/reports/all_files.txt

# Python files
find . \
    -type f \
    -name "*.py" \
    -not -path "./.git/*" \
    -not -path "./__pycache__/*" \
    -not -path "./cleanup_workspace/*" \
    | sort \
    > cleanup_workspace/reports/python_files.txt

# Directories
find . \
    -type d \
    -not -path "./.git/*" \
    -not -path "./.venv/*" \
    -not -path "./venv/*" \
    -not -path "./__pycache__/*" \
    -not -path "./cleanup_workspace/*" \
    | sort \
    > cleanup_workspace/reports/directories.txt

# Non-Python files
comm -23 \
    cleanup_workspace/reports/all_files.txt \
    cleanup_workspace/reports/python_files.txt \
    > cleanup_workspace/reports/non_python_files.txt

echo "   ✅ Total files: $(wc -l < cleanup_workspace/reports/all_files.txt)"
echo "   ✅ Python files: $(wc -l < cleanup_workspace/reports/python_files.txt)"
echo "   ✅ Directories: $(wc -l < cleanup_workspace/reports/directories.txt)"

# ================================================================
# 2. GIT STATE CAPTURE
# ================================================================
echo ""
echo "📊 2. CAPTURING GIT STATE..."

# Branches
git branch -a 2>/dev/null | sort > cleanup_workspace/reports/git_branches.txt

# Tags
git tag -l 2>/dev/null | sort > cleanup_workspace/reports/git_tags.txt

# Recent commits
git log --oneline -20 2>/dev/null > cleanup_workspace/reports/git_recent_commits.txt

echo "   ✅ Branches: $(wc -l < cleanup_workspace/reports/git_branches.txt)"
echo "   ✅ Tags: $(wc -l < cleanup_workspace/reports/git_tags.txt)"

# ================================================================
# 3. BACKUP CANDIDATES
# ================================================================
echo ""
echo "📊 3. FINDING BACKUP CANDIDATES..."

find . \
    -type f \
    -not -path "./cleanup_workspace/*" \
    | grep -Ei "\.(backup|bak|orig|original|old|copy|fixed|render|working|tmp|temp|swp)$" \
    | sort \
    > cleanup_workspace/reports/backup_candidates.txt || true

find . \
    -type f \
    -not -path "./cleanup_workspace/*" \
    | grep -Ei "backup|bak|orig|original|copy|fixed|render" \
    | sort \
    >> cleanup_workspace/reports/backup_candidates.txt || true

sort -u cleanup_workspace/reports/backup_candidates.txt -o cleanup_workspace/reports/backup_candidates.txt 2>/dev/null || true

echo "   ✅ Backup candidates: $(wc -l < cleanup_workspace/reports/backup_candidates.txt 2>/dev/null || echo 0)"

# ================================================================
# 4. ARCHIVE DIRECTORIES
# ================================================================
echo ""
echo "📊 4. FINDING ARCHIVE DIRECTORIES..."

find . \
    -type d \
    -not -path "./cleanup_workspace/*" \
    -not -path "./.git/*" \
    | grep -Ei "archive|backup|disabled|legacy|old|obsolete|temp|tmp" \
    | sort \
    > cleanup_workspace/reports/archive_directories.txt || true

echo "   ✅ Archive directories: $(wc -l < cleanup_workspace/reports/archive_directories.txt 2>/dev/null || echo 0)"

# ================================================================
# 5. DUPLICATE NAMES
# ================================================================
echo ""
echo "📊 5. FINDING DUPLICATE NAMES..."

find . \
    -type f \
    -name "*.py" \
    -not -path "./cleanup_workspace/*" \
    -not -path "./.git/*" \
    | awk -F/ '{print $NF}' \
    | sort \
    | uniq -d \
    > cleanup_workspace/reports/duplicate_names.txt || true

echo "   ✅ Duplicate names: $(wc -l < cleanup_workspace/reports/duplicate_names.txt 2>/dev/null || echo 0)"

# ================================================================
# 6. DEPENDENCY ANALYSIS
# ================================================================
echo ""
echo "📊 6. ANALYZING DEPENDENCIES..."

# Import statements
grep -R "^import " hackathon/ src/ --include="*.py" 2>/dev/null \
    | sort \
    | uniq \
    > cleanup_workspace/reports/imports.txt || true

grep -R "^from " hackathon/ src/ --include="*.py" 2>/dev/null \
    | sort \
    | uniq \
    >> cleanup_workspace/reports/imports.txt || true

sort -u cleanup_workspace/reports/imports.txt -o cleanup_workspace/reports/imports.txt 2>/dev/null || true

# Dashboard imports
grep -R "from hackathon.app.pages.dashboard" hackathon/ src/ --include="*.py" 2>/dev/null \
    | sort \
    | uniq \
    > cleanup_workspace/reports/dashboard_imports.txt || true

# V4 module imports
grep -R "from hackathon.app.modules.v4" hackathon/ src/ --include="*.py" 2>/dev/null \
    | sort \
    | uniq \
    > cleanup_workspace/reports/v4_imports.txt || true

# Core src imports
grep -R "from src" hackathon/ src/ --include="*.py" 2>/dev/null \
    | sort \
    | uniq \
    > cleanup_workspace/reports/src_imports.txt || true

echo "   ✅ Imports found: $(wc -l < cleanup_workspace/reports/imports.txt 2>/dev/null || echo 0)"

# ================================================================
# 7. VALIDATION
# ================================================================
echo ""
echo "📊 7. VALIDATING WORKING FILES..."

WORKING_FILES=(
    "hackathon/app/pages/dashboard.py"
    "hackathon/app/streamlit_app.py"
    "hackathon/app/modules/v4/__init__.py"
    "hackathon/app/modules/v4/state.py"
    "hackathon/app/modules/v4/state_fallback.py"
    "hackathon/app/modules/v4/visual_components.py"
    "hackathon/app/modules/v4/situation_map.py"
    "hackathon/app/modules/v4/ai_copilot.py"
    "hackathon/app/modules/v4/control_panel.py"
    "hackathon/app/modules/v4/decision_support.py"
    "hackathon/app/modules/v4/evidence_panel.py"
    "hackathon/app/modules/v4/impact_assessment.py"
    "hackathon/app/modules/v4/operations.py"
    "hackathon/app/modules/v4/risk_display.py"
    "hackathon/ai/flood_explainer.py"
    "hackathon/ai/hydrological_intelligence.py"
    "hackathon/ai/impact_estimator.py"
    ".streamlit/config.toml"
    "render.yaml"
    "requirements.txt"
    "Dockerfile"
)

VALIDATION_FILE="cleanup_workspace/reports/validation.txt"
echo "# NFCC Working File Validation" > "$VALIDATION_FILE"
echo "# Timestamp: $TIMESTAMP" >> "$VALIDATION_FILE"
echo "" >> "$VALIDATION_FILE"

MISSING_COUNT=0
for file in "${WORKING_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file" >> "$VALIDATION_FILE"
    else
        echo "❌ $file MISSING" >> "$VALIDATION_FILE"
        ((MISSING_COUNT++))
    fi
done

echo "   ✅ Working files: $((${#WORKING_FILES[@]} - MISSING_COUNT)) of ${#WORKING_FILES[@]} present"
if [ "$MISSING_COUNT" -gt 0 ]; then
    echo "   ⚠️  $MISSING_COUNT files missing (see validation.txt)"
fi

# ================================================================
# 8. SYNTAX CHECK (if Python available)
# ================================================================
echo ""
echo "📊 8. CHECKING PYTHON SYNTAX..."

if command -v python3 &> /dev/null; then
    SYNTAX_FILE="cleanup_workspace/reports/syntax_check.txt"
    echo "# Python Syntax Check" > "$SYNTAX_FILE"
    echo "# Timestamp: $TIMESTAMP" >> "$SYNTAX_FILE"
    echo "" >> "$SYNTAX_FILE"

    # Check critical Python files
    CRITICAL_PY_FILES=(
        "hackathon/app/pages/dashboard.py"
        "hackathon/app/streamlit_app.py"
        "hackathon/app/modules/v4/__init__.py"
        "hackathon/app/modules/v4/state.py"
        "hackathon/app/modules/v4/visual_components.py"
        "hackathon/app/modules/v4/situation_map.py"
        "hackathon/app/modules/v4/ai_copilot.py"
        "hackathon/ai/flood_explainer.py"
        "src/api/main.py"
        "src/alerts/engine.py"
    )

    for py_file in "${CRITICAL_PY_FILES[@]}"; do
        if [ -f "$py_file" ]; then
            if python3 -m py_compile "$py_file" 2>/dev/null; then
                echo "✅ $py_file - syntax OK" >> "$SYNTAX_FILE"
            else
                echo "❌ $py_file - syntax ERROR" >> "$SYNTAX_FILE"
                python3 -m py_compile "$py_file" 2>&1 >> "$SYNTAX_FILE" || true
            fi
        else
            echo "⚠️  $py_file - not found" >> "$SYNTAX_FILE"
        fi
    done

    echo "   ✅ Syntax check complete: $SYNTAX_FILE"
else
    echo "   ⚠️  Python3 not found - skipping syntax check"
fi

# ================================================================
# 9. ARCHITECTURE SUMMARY
# ================================================================
echo ""
echo "📊 9. GENERATING ARCHITECTURE SUMMARY..."

cat > cleanup_workspace/reports/architecture_summary.md << EOF
# NFCC Architecture Summary

## Repository Information
- **Repository:** $REPO_ROOT
- **Branch:** $BRANCH
- **Commit:** $COMMIT
- **Timestamp:** $TIMESTAMP

## File Statistics
- **Total Files:** $(wc -l < cleanup_workspace/reports/all_files.txt 2>/dev/null || echo 0)
- **Python Files:** $(wc -l < cleanup_workspace/reports/python_files.txt 2>/dev/null || echo 0)
- **Directories:** $(wc -l < cleanup_workspace/reports/directories.txt 2>/dev/null || echo 0)

## Cleanup Candidates
- **Backup Candidates:** $(wc -l < cleanup_workspace/reports/backup_candidates.txt 2>/dev/null || echo 0)
- **Archive Directories:** $(wc -l < cleanup_workspace/reports/archive_directories.txt 2>/dev/null || echo 0)
- **Duplicate Names:** $(wc -l < cleanup_workspace/reports/duplicate_names.txt 2>/dev/null || echo 0)

## Working System Validation
- **Working Files Present:** $((${#WORKING_FILES[@]} - MISSING_COUNT)) of ${#WORKING_FILES[@]}
- **Missing Files:** $MISSING_COUNT

## Key Directories
### hackathon/
- **app/pages/** - Dashboard pages
- **app/modules/v4/** - V4 modules (active)
- **ai/** - AI modules

### src/
- **alerts/** - Alert engine
- **api/** - FastAPI endpoints
- **hydrology/** - Hydrology modules
- **community/** - Community modules
- **exposure/** - Exposure modules
- **models/** - ML models
- **config/** - Configuration
- **database/** - Database

## Next Steps
1. Review backup_candidates.txt
2. Review archive_directories.txt
3. Review duplicate_names.txt
4. Review validation.txt
5. Create Phase 2: Classification script
6. Create Phase 3: Archive script
7. Create Phase 4: Deletion script
