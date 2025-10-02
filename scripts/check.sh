#!/bin/bash

DOMAIN=$(grep 'Host(' docker-compose.yml | cut -d'`' -f2)

echo "🔍 Überprüfe Medical Document Translator..."
echo ""

# Container-Status
echo "📦 Container-Status:"
docker compose ps
echo ""

# Health-Checks
echo "💚 Gesundheitschecks:"
echo -n "Frontend: "
curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health && echo " ✅" || echo " ❌"

echo -n "Backend: "
curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/api/health && echo " ✅" || echo " ❌"

# Ollama removed - using OVH API only

echo ""

# Speicher-Nutzung
echo "💾 Speicher-Nutzung:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 