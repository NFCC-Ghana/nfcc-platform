#!/bin/bash
# Optional Redis setup - SKIP if you don't want Redis

echo "=== Optional Redis Setup ==="
echo "This is OPTIONAL. Your system works without Redis."
echo "Redis provides distributed cooldown across multiple workers."
echo ""

read -p "Do you want to install Redis? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing Redis..."
    sudo apt update
    sudo apt install redis-server -y
    sudo systemctl enable redis
    sudo systemctl start redis
    redis-cli ping && echo "✅ Redis is running"
    
    # Add Redis URL to .env.production
    if ! grep -q "REDIS_URL" .env.production; then
        echo "REDIS_URL=redis://localhost:6379/0" >> .env.production
        echo "✅ Added REDIS_URL to .env.production"
    fi
else
    echo "Skipping Redis installation. System will use memory cooldown."
fi
