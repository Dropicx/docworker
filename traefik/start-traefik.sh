#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🚀 Traefik Reverse Proxy Startup Script${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found!${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${RED}Please edit .env file with your Netcup API credentials!${NC}"
    echo "Edit the following values:"
    echo "  - NETCUP_CUSTOMER_NUMBER"
    echo "  - NETCUP_API_KEY"
    echo "  - NETCUP_API_PASSWORD"
    echo "  - TRAEFIK_DASHBOARD_CREDENTIALS (optional)"
    exit 1
fi

# Create acme.json with correct permissions
if [ ! -f data/acme.json ]; then
    echo "Creating acme.json file..."
    touch data/acme.json
    chmod 600 data/acme.json
    echo -e "${GREEN}✅ acme.json created with correct permissions${NC}"
fi

# Check if traefik network exists
if ! docker network ls | grep -q "traefik-proxy"; then
    echo "Creating traefik-proxy network..."
    docker network create traefik-proxy
    echo -e "${GREEN}✅ Network traefik-proxy created${NC}"
fi

# Stop old Traefik if running
echo "Checking for existing Traefik container..."
if docker ps -a | grep -q "traefik"; then
    echo "Stopping old Traefik container..."
    docker stop traefik 2>/dev/null || true
    docker rm traefik 2>/dev/null || true
fi

# Start Traefik
echo ""
echo -e "${BLUE}Starting Traefik...${NC}"
docker compose up -d

# Wait for Traefik to start
echo "Waiting for Traefik to initialize..."
sleep 5

# Check if Traefik is running
if docker ps | grep -q "traefik"; then
    echo -e "${GREEN}✅ Traefik is running!${NC}"
    echo ""
    echo "📝 Service URLs:"
    echo "   - Traefik Dashboard: https://traefik.fra-la.de (requires auth)"
    echo "   - Main Domain: https://fra-la.de"
    echo ""
    echo "📊 Check status with: docker compose ps"
    echo "📜 View logs with: docker compose logs -f"
    echo ""
    echo -e "${YELLOW}⚠️  Note: DNS propagation may take a few minutes${NC}"
    echo -e "${YELLOW}    If certificates fail, check DNS settings at Netcup${NC}"
else
    echo -e "${RED}❌ Traefik failed to start!${NC}"
    echo "Check logs with: docker compose logs"
    exit 1
fi