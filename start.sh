#!/bin/bash

# Quick Start Script for Multi-Tenant AI Chatbot

set -e

echo "=========================================="
echo "Multi-Tenant AI Chatbot - Quick Start"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your GEMINI_API_KEY"
    echo "   Get your API key from: https://makersuite.google.com/app/apikey"
    echo ""
    read -p "Press Enter after you've updated the .env file..."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo ""
echo "Starting services with Docker Compose..."
docker-compose up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "Checking service status..."
docker-compose ps

echo ""
echo "Testing API health..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ API is healthy!"
        break
    fi
    retry_count=$((retry_count + 1))
    echo "Waiting for API to be ready... ($retry_count/$max_retries)"
    sleep 2
done

if [ $retry_count -eq $max_retries ]; then
    echo "❌ API failed to start. Check logs with: docker-compose logs api"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ All services are running!"
echo "=========================================="
echo ""
echo "API Documentation:"
echo "  - Swagger UI: http://localhost:8000/docs"
echo "  - ReDoc:      http://localhost:8000/redoc"
echo ""
echo "Service Ports:"
echo "  - API:        http://localhost:8000"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis:      localhost:6379"
echo ""
echo "Useful Commands:"
echo "  - View logs:        docker-compose logs -f"
echo "  - Stop services:    docker-compose down"
echo "  - Restart services: docker-compose restart"
echo "  - Run tests:        python test_api.py"
echo ""
echo "Next Steps:"
echo "  1. Visit http://localhost:8000/docs to explore the API"
echo "  2. Create a client using POST /clients"
echo "  3. Create a user using POST /users"
echo "  4. Login using POST /login to get a token"
echo "  5. Upload documents using POST /upload"
echo "  6. Start chatting using POST /chat"
echo ""
echo "=========================================="
