#!/bin/bash
# RESTORE SCRIPT - Restore dashboard from backup

echo "🔄 RESTORING DASHBOARD FROM BACKUP"
echo "=================================="
echo ""

BACKUP_DIR=$(dirname "$0")
BACKUP_FILE="$BACKUP_DIR/dashboard_enhanced.py.backup"

if [ -f "$BACKUP_FILE" ]; then
    cp "$BACKUP_FILE" hackathon/app/pages/dashboard_enhanced.py
    echo "✅ Dashboard restored from: $BACKUP_FILE"
    echo "   Restart Streamlit to see changes"
else
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi
