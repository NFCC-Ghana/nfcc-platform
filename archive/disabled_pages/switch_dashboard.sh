#!/bin/bash
# DASHBOARD VERSION SWITCHER
# Usage: ./switch_dashboard.sh [original|enhanced|restore]

ORIGINAL="dashboard_enhanced.py"
ENHANCED="dashboard_enhanced_v2.py"
BACKUP_DIR="backups/$(ls -t backups/ | head -1)"

case "$1" in
    original)
        echo "🔄 Switching to ORIGINAL dashboard..."
        if [ -f "$BACKUP_DIR/$ORIGINAL.backup" ]; then
            cp "$BACKUP_DIR/$ORIGINAL.backup" "$ORIGINAL"
            echo "✅ Original dashboard restored"
        else
            echo "⚠️ Original backup not found, using current file"
        fi
        ;;
    enhanced)
        echo "🔄 Switching to ENHANCED dashboard..."
        if [ -f "$ENHANCED" ]; then
            # Backup current before switching
            cp "$ORIGINAL" "$BACKUP_DIR/${ORIGINAL}.pre_enhanced.backup"
            cp "$ENHANCED" "$ORIGINAL"
            echo "✅ Enhanced dashboard activated"
        else
            echo "❌ Enhanced dashboard not found"
        fi
        ;;
    restore)
        echo "🔄 Restoring from latest backup..."
        LATEST_BACKUP="backups/$(ls -t backups/ | head -1)"
        if [ -f "$LATEST_BACKUP/$ORIGINAL.backup" ]; then
            cp "$LATEST_BACKUP/$ORIGINAL.backup" "$ORIGINAL"
            echo "✅ Restored from: $LATEST_BACKUP"
        else
            echo "❌ No backup found"
        fi
        ;;
    status)
        echo "📊 DASHBOARD STATUS"
        echo "=================="
        echo "Original: $ORIGINAL ($(ls -lh $ORIGINAL 2>/dev/null | awk '{print $5}'))"
        echo "Enhanced: $ENHANCED ($(ls -lh $ENHANCED 2>/dev/null | awk '{print $5}'))"
        echo "Backup: $BACKUP_DIR"
        echo ""
        echo "Recent Backups:"
        ls -lt backups/ | head -5
        ;;
    *)
        echo "Usage: ./switch_dashboard.sh [original|enhanced|restore|status]"
        echo ""
        echo "Commands:"
        echo "  original  - Switch to original dashboard"
        echo "  enhanced  - Switch to enhanced dashboard"
        echo "  restore   - Restore from latest backup"
        echo "  status    - Show dashboard status"
        ;;
esac
