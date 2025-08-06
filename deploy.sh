#!/bin/bash

set -e

echo "🚀 Starte Deployment der Medical Document Translator App..."

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funktionen
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Prüfe ob Docker läuft
if ! docker info >/dev/null 2>&1; then
    log_error "Docker ist nicht verfügbar oder läuft nicht!"
    exit 1
fi

# 2. Prüfe ob Traefik-Netzwerk existiert
if ! docker network ls | grep -q traefik; then
    log_warn "Traefik-Netzwerk nicht gefunden, erstelle es..."
    docker network create traefik
fi

# 3. Stoppe alte Container (falls vorhanden)
log_info "Stoppe alte Container..."
docker compose down 2>/dev/null || true

# 4. Baue neue Images
log_info "Baue neue Docker Images..."
docker compose build --no-cache

# 5. Starte Services
log_info "Starte Services..."
docker compose up -d

# 6. Warte auf Gesundheitscheck
log_info "Warte auf Gesundheitschecks..."
sleep 30

# 7. Prüfe Status
if docker compose ps | grep -q "Up (healthy)"; then
    log_info "✅ Backend ist gesund"
else
    log_warn "⚠️ Backend-Gesundheitscheck fehlgeschlagen"
fi

# 8. Überspringe Ollama-Modell Installation (entfernt)
log_info "Ollama-Integration wurde entfernt"

# 9. Zeige finale Informationen
echo ""
log_info "🎉 Deployment abgeschlossen!"
echo ""
echo "📋 Service-URLs:"
echo "   Frontend: https://$(grep 'Host(' docker-compose.yml | cut -d'`' -f2)"
echo "   Backend Health: https://$(grep 'Host(' docker-compose.yml | cut -d'`' -f2)/api/health"
echo ""
echo "📊 Container-Status:"
docker compose ps
echo ""
echo "📝 Logs verfolgen:"
echo "   docker compose logs -f"