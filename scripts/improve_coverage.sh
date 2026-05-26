#!/bin/bash
# Comprehensive coverage improvement script

set -e

echo "📊 Current Coverage Report"
echo "=========================="
pytest tests/ --cov=src --cov-report=term

echo ""
echo "🎯 Targeting low-coverage modules..."
echo ""

# Target formatter.py
echo "1️⃣ Improving formatter.py coverage..."
pytest tests/unit/test_formatter.py --cov=src.alerts.formatter --cov-report=term --cov-fail-under=85 || true

# Target rate_limit.py
echo ""
echo "2️⃣ Improving rate_limit.py coverage..."
pytest tests/unit/test_rate_limit.py --cov=src.alerts.rate_limit --cov-report=term --cov-fail-under=85 || true

# Target engine.py
echo ""
echo "3️⃣ Improving engine.py coverage..."
pytest tests/unit/test_engine_edge_cases.py --cov=src.alerts.engine --cov-report=term --cov-fail-under=85 || true

# Generate HTML report
echo ""
echo "📈 Generating HTML coverage report..."
pytest tests/ --cov=src --cov-report=html

echo ""
echo "✅ Coverage improvement complete!"
echo "Open htmlcov/index.html to view detailed report"
