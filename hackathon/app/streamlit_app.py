"""
CivicFlood AI - Diagnostic Entry Point
Shows exactly where the error occurs.
"""

import streamlit as st
import sys
import traceback
from pathlib import Path

# ============================================================
# DIAGNOSTIC: Show Python path
# ============================================================
st.write("## 🔍 Diagnostic Information")

# Show current working directory
import os
st.write(f"**Working Directory:** `{os.getcwd()}`")

# Show Python path
st.write("**Python Path:**")
for p in sys.path:
    st.write(f"  - `{p}`")

# ============================================================
# DIAGNOSTIC: Try importing the dashboard
# ============================================================
st.write("---")
st.write("## 🔍 Import Test")

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Try to find the file
pages_dir = Path(__file__).parent / "pages"
st.write(f"**pages directory exists:** `{pages_dir.exists()}`")
if pages_dir.exists():
    st.write(f"**Files in pages:** `{list(pages_dir.glob('*.py'))}`")

try:
    st.write("**Attempting import:** `from hackathon.app.pages.dashboard import main`")
    from hackathon.app.pages.dashboard import main
    st.success("✅ Import successful!")
    
    # Try to call main
    st.write("**Attempting:** `main()`")
    main()
    
except Exception as e:
    st.error(f"❌ Error: {type(e).__name__}: {e}")
    st.code(traceback.format_exc())
