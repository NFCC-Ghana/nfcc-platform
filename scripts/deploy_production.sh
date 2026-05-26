#!/bin/bash
# Full production deployment script

set -e

echo "🚀 Deploying NFCC Platform to Production"
echo "========================================"

# Step 1: Resave model in modern format
echo "📦 Step 1: Converting model to modern format..."
python scripts/resave_model.py

# Step 2: Validate environment
echo ""
echo "🔍 Step 2: Validating environment..."
python scripts/validate_env.py

# Step 3: Run tests
echo ""
echo "🧪 Step 3: Running test suite..."
pytest tests/ -v --tb=short -k "not providers"

# Step 4: Generate SSL certificates (if not exists)
if [ ! -f ssl/cert.pem ]; then
    echo ""
    echo "🔒 Step 4: Generating SSL certificates..."
    ./scripts/generate_ssl.sh
fi

# Step 5: Build and start Docker containers
echo ""
echo "🐳 Step 5: Starting Docker containers..."
docker-compose -f docker-compose.prod.yml up -d --build

# Step 6: Initialize database
echo ""
echo "🗄️ Step 6: Initializing database..."
sleep 5  # Wait for database to be ready
docker exec nfcc-flood-alert python -c "from src.database import init_db; init_db()"

# Step 7: Check health
echo ""
echo "🏥 Step 7: Checking health..."
sleep 3
curl -s http://localhost:8000/health | python -m json.tool

echo ""
echo "✅ Production deployment complete!"
echo ""
echo "Services running:"
echo "  - API: https://localhost:8000"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo ""
echo "Monitor with: docker-compose -f docker-compose.prod.yml logs -f"
