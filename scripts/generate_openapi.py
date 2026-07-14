#!/usr/bin/env python
"""Generate OpenAPI schema from FastAPI app."""

import json
from pathlib import Path

from src.api.main import app


def generate_openapi():
    """Generate and save OpenAPI schema."""
    schema = app.openapi()
    output_path = Path(__file__).parent.parent / "openapi.json"

    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)

    print(f"✅ OpenAPI schema saved to {output_path}")


if __name__ == "__main__":
    generate_openapi()
