#!/usr/bin/env bash
set -euo pipefail

echo "======================================"
echo " NFCC SCORE CONTRACT MIGRATION"
echo "======================================"

echo "[1/8] Backing up current state..."

BACKUP_DIR="backup_score_migration_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

cp -r src "$BACKUP_DIR/"
cp -r tests "$BACKUP_DIR/" || true

echo "Backup stored at: $BACKUP_DIR"

echo "[2/8] Removing duplicate AlertPayload implementations..."

if [ -d "src/alerts/core" ]; then
    echo "Removing experimental core AlertPayload..."
    rm -rf src/alerts/core
fi

echo "[3/8] Fixing imports (AlertPayload canonical import)"

find src tests -type f -name "*.py" -exec sed -i \
's/from .*AlertPayload/from src.alerts.models import AlertPayload/g' {} +

echo "[4/8] Replacing risk_score → score in code"

# Fix direct attribute access
find src -type f -name "*.py" -exec sed -i \
's/payload\.risk_score/payload.score/g' {} +

# Fix standalone usage
find src tests -type f -name "*.py" -exec sed -i \
's/\brisk_score\b/score/g' {} +

echo "[5/8] Fix engine fallback logic"

sed -i 's/payload.get("score") or payload.get("risk_score")/payload.get("score")/g' src/alerts/engine.py || true

sed -i 's/kwargs.get("score") or kwargs.get("risk_score")/kwargs.get("score")/g' src/alerts/engine.py || true

echo "[6/8] Fix API layer"

if [ -f "src/api/main.py" ]; then
    sed -i 's/risk_score/score/g' src/api/main.py
fi

echo "[7/8] Fix tests"

find tests -type f -name "*.py" -exec sed -i \
's/"risk_score"/"score"/g' {} +

find tests -type f -name "*.py" -exec sed -i \
's/\brisk_score\b/score/g' {} +

echo "Checking alert system only..."

REMAINING=$(grep -R "risk_score" src/alerts src/api tests || true)

if [ -n "$REMAINING" ]; then
    echo "❌ MIGRATION FAILED — leftover risk_score found:"
    echo "$REMAINING"
    exit 1
fi

REMAINING=$(grep -R "risk_score" src/alerts src/api tests || true)
if [ -n "$REMAINING" ]; then
    echo "❌ MIGRATION FAILED — leftover risk_score found:"
    echo "$REMAINING"
    exit 1
fi

echo "======================================"
echo " MIGRATION SUCCESSFUL"
echo "======================================"

echo "Next steps:"
echo "  pytest tests/ -v"
echo "  git add -A"
echo "  git commit -m 'fix: unify score contract'"
