#!/usr/bin/env python
"""Safe test for map functionality"""

import sys
import os

sys.path.insert(0, ".")

print("🧪 Testing map imports...")
try:
    from hackathon.app.modules.v4.situation_map import (
        render_situation_map,
        render_minimal_map,
    )

    print("✅ Import successful!")
    print(f"   render_situation_map: {render_situation_map}")
    print(f"   render_minimal_map: {render_minimal_map}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    print("💡 Run: pip install streamlit-folium folium")
