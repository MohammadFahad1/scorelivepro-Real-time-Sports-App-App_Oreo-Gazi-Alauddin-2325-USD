#!/bin/bash
set -e

echo "=================================================="
echo "🚀 DEPLOYMENT SCRIPT STARTING ON PRODUCTION VPS"
echo "=================================================="

cd /home/wasik/app

echo "📦 Extracting source files..."
if [ -f backend.tar.gz ]; then
    tar -xzf backend.tar.gz
    rm -f backend.tar.gz
    echo "✅ Extraction complete."
else
    echo "⚠️ backend.tar.gz not found, skipping extraction."
fi

echo "🔑 Setting proper permissions..."
chown -R wasik:wasik /home/wasik/app

echo "🏗️ Rebuilding Docker Image locally on VPS..."
docker build -t itzwasik/scorelivepro-web:latest .

echo "🛑 Stopping existing services..."
docker compose -f docker-compose.prod.yml down

echo "⚡ Starting updated services in daemon mode..."
docker compose -f docker-compose.prod.yml up -d

echo "📊 Docker Container Status:"
docker ps -a

echo "=================================================="
echo "✅ DEPLOYMENT SUCCESSFULLY COMPLETED!"
echo "=================================================="
