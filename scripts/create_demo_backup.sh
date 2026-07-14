#!/bin/bash
# ================================================================
# CREATE DEMO BACKUP - Screenshots and Video
# ================================================================

echo "📹 CREATING DEMO BACKUP"
echo "================================================"

# Create backup directory
BACKUP_DIR="demo_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# ================================================================
# STEP 1: Capture Screenshots
# ================================================================
echo ""
echo "📸 Capturing screenshots..."

# Dashboard screenshots
echo "   Capturing dashboard screenshots..."

# Using gnome-screenshot or import
if command -v gnome-screenshot &> /dev/null; then
    echo "   Using gnome-screenshot..."
    gnome-screenshot -w -f "$BACKUP_DIR/dashboard_home.png" 2>/dev/null || true
else
    echo "   ⚠️ gnome-screenshot not found - skipping"
fi

# Alternative using import (ImageMagick)
if command -v import &> /dev/null; then
    echo "   Using import (ImageMagick)..."
    import -window root "$BACKUP_DIR/dashboard_full.png" 2>/dev/null || true
fi

echo "   ✅ Screenshots saved to $BACKUP_DIR/"

# ================================================================
# STEP 2: Save HTML Snapshot
# ================================================================
echo ""
echo "📄 Saving HTML snapshot..."

# Save dashboard HTML
echo "   Saving dashboard HTML..."
curl -s http://localhost:8501 > "$BACKUP_DIR/dashboard.html" 2>/dev/null || echo "   ⚠️ Dashboard not running"

# ================================================================
# STEP 3: Create Readme
# ================================================================
echo ""
echo "📋 Creating README..."

cat > "$BACKUP_DIR/README.txt" << 'EOF'
CIVICFLOOD AI - DEMO BACKUP
=============================

This backup contains pre-captured demo materials for the Ghana AI Innovation Challenge 2026.

FILES INCLUDED:
- dashboard_home.png: Home page screenshot
- dashboard_full.png: Full dashboard screenshot
- dashboard.html: HTML snapshot of dashboard

USE THIS BACKUP:
1. If the live demo fails
2. As presentation materials
3. For poster/print materials

LIVE DEMO:
- API: http://localhost:8000
- Dashboard: http://localhost:8501
- Offline Dashboard: http://localhost:8501?offline=true

CREATED: $(date)

CivicFlood AI - National Flood Intelligence Platform
