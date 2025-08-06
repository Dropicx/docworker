#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🚀 Starting Doctranslator with Traefik${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if Traefik is running
echo "Checking if Traefik is running..."
if ! docker ps | grep -q "traefik"; then
    echo -e "${YELLOW}⚠️  Traefik is not running!${NC}"
    echo "Starting Traefik first..."
    
    cd traefik
    if [ -f start-traefik.sh ]; then
        ./start-traefik.sh
        cd ..
        echo "Waiting for Traefik to initialize..."
        sleep 10
    else
        echo -e "${RED}❌ Traefik start script not found!${NC}"
        echo "Please start Traefik manually:"
        echo "  cd traefik && ./start-traefik.sh"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Traefik is already running${NC}"
fi

# Check if traefik-proxy network exists
if ! docker network ls | grep -q "traefik-proxy"; then
    echo "Creating traefik-proxy network..."
    docker network create traefik-proxy
    echo -e "${GREEN}✅ Network created${NC}"
fi

# Stop old containers if running
echo ""
echo "Stopping old containers if running..."
docker compose down 2>/dev/null || true

# Start services with Traefik integration
echo ""
echo -e "${BLUE}Starting Doctranslator with Traefik integration...${NC}"
docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d --build

# Wait for services to be ready
echo ""
echo "Waiting for services to be ready..."
sleep 15

# Check service status
echo ""
echo -e "${BLUE}Service Status:${NC}"
docker compose ps

# Health checks
echo ""
echo -e "${BLUE}Health Checks:${NC}"

# Check backend
echo -n "Backend API: "
if curl -s http://localhost:9122/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Starting up...${NC}"
fi

# Check frontend
echo -n "Frontend: "
if curl -s http://localhost:9121 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Starting up...${NC}"
fi

# Check Ollama
echo -n "Ollama: "
if docker exec ollama ollama list > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${YELLOW}⚠️  Starting up...${NC}"
fi

# Show final information
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✨ Services are starting!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "📝 Access URLs:"
echo "   - Public URL: https://medical.fra-la.de"
echo "   - Local Frontend: http://localhost:9121"
echo "   - Local Backend: http://localhost:9122"
echo "   - Traefik Dashboard: https://traefik.fra-la.de"
echo ""
echo "📊 Commands:"
echo "   - View logs: docker compose logs -f"
echo "   - Stop services: docker compose down"
echo "   - Restart: docker compose restart"
echo ""
echo -e "${YELLOW}Note: SSL certificates may take a few minutes to generate${NC}"
echo -e "${YELLOW}      Check Traefik logs if HTTPS doesn't work immediately${NC}"