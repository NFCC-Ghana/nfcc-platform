"""Check imports for hydrological intelligence."""

import sys

print(f"Python path: {sys.path}")

# Check src imports
try:
    from src.hydrology.rainfall_history import rainfall_history

    print("✅ src.hydrology.rainfall_history")
except ImportError as e:
    print(f"❌ src.hydrology.rainfall_history: {e}")

try:
    from src.hydrology.unified_intelligence import unified_intelligence

    print("✅ src.hydrology.unified_intelligence")
except ImportError as e:
    print(f"❌ src.hydrology.unified_intelligence: {e}")

# Check hackathon imports
try:
    from hackathon.ai.hydrological_intelligence import civicflood_hydrological

    print("✅ hackathon.ai.hydrological_intelligence")
except ImportError as e:
    print(f"❌ hackathon.ai.hydrological_intelligence: {e}")

print("\nAll checks complete.")
