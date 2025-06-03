# 1. Erforderliche Ordner erstellen
mkdir -p logs backups

# 2. Domain in der docker-compose.yml anpassen
sed -i 's/medical.ihre-domain.de/medical.ihre-echte-domain.de/g' docker-compose.yml

# 3. Traefik-Netzwerk erstellen (falls nicht vorhanden)
docker network create traefik 2>/dev/null || echo "Traefik-Netzwerk existiert bereits"

# 4. Container bauen und starten
docker-compose up -d --build

# 5. Status überprüfen
docker-compose ps 