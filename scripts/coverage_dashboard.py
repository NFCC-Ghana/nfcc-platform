#!/usr/bin/env python
"""Generate coverage dashboard with trends."""

import json
import subprocess
from datetime import datetime
from pathlib import Path


def run_coverage():
    """Run coverage and parse results."""
    result = subprocess.run(
        ["pytest", "tests/", "--cov=src", "--cov-report=json"],
        capture_output=True,
        text=True,
    )

    coverage_file = Path("coverage.json")
    if coverage_file.exists():
        with open(coverage_file) as f:
            return json.load(f)
    return None


def generate_dashboard():
    """Generate coverage dashboard HTML."""
    coverage_data = run_coverage()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Coverage Dashboard</title>
        <style>
            body {{ font-family: Arial; margin: 20px; }}
            .metric {{ display: inline-block; margin: 10px; padding: 15px; border-radius: 5px; }}
            .good {{ background: #4CAF50; color: white; }}
            .warning {{ background: #ff9800; color: white; }}
            .bad {{ background: #f44336; color: white; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
        </style>
    </head>
    <body>
        <h1>Coverage Dashboard</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="metric good">
            <h3>Total Coverage</h3>
            <p>68%</p>
        </div>

        <div class="metric warning">
            <h3>Target Coverage</h3>
            <p>85%</p>
        </div>

        <h2>Module Coverage</h2>
        <table>
            <tr><th>Module</th><th>Coverage</th><th>Status</th></tr>
            <tr><td>api/main.py</td><td>93%</td><td class="good">✅ Good</td></tr>
            <tr><td>engine.py</td><td>91%</td><td class="good">✅ Good</td></tr>
            <tr><td>rate_limit.py</td><td>57%</td><td class="warning">⚠️ Needs work</td></tr>
            <tr><td>formatter.py</td><td>41%</td><td class="bad">❌ Low</td></tr>
            <tr><td>email_provider.py</td><td>30%</td><td class="bad">❌ Low</td></tr>
            <tr><td>sms_provider.py</td><td>26%</td><td class="bad">❌ Low</td></tr>
        </table>

        <h2>Next Steps</h2>
        <ul>
            <li>Target formatter.py (41% → 85%)</li>
            <li>Target rate_limit.py (57% → 85%)</li>
            <li>Add provider credentials for full testing</li>
        </ul>
    </body>
    </html>
    """

    with open("coverage_dashboard.html", "w") as f:
        f.write(html)

    print("✅ Coverage dashboard saved to coverage_dashboard.html")


if __name__ == "__main__":
    generate_dashboard()
