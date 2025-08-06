# Traefik Reverse Proxy für fra-la.de

Dieser Traefik Stack ist speziell für die Domain `fra-la.de` und alle Subdomains konfiguriert.

## Setup

### 1. Netcup API Credentials einrichten

1. Kopieren Sie die `.env.example` zu `.env`:
   ```bash
   cp .env.example .env
   ```

2. Bearbeiten Sie die `.env` Datei mit Ihren Netcup API Credentials:
   - `NETCUP_CUSTOMER_NUMBER`: Ihre Netcup Kundennummer
   - `NETCUP_API_KEY`: API Key aus dem Netcup CCP
   - `NETCUP_API_PASSWORD`: API Passwort aus dem Netcup CCP

3. (Optional) Ändern Sie die Traefik Dashboard Credentials:
   ```bash
   # Generieren Sie neue Credentials mit htpasswd:
   echo $(htpasswd -nB admin) | sed -e s/\\$/\\$\\$/g
   ```

### 2. Traefik starten

```bash
cd traefik
./start-traefik.sh
```

### 3. Doctranslator App mit Traefik starten

Aus dem Hauptverzeichnis:

```bash
# Traefik muss zuerst laufen!
cd traefik && ./start-traefik.sh && cd ..

# Dann die App mit Traefik-Integration starten:
docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
```

## URLs

Nach dem Start sind folgende URLs verfügbar:

- **Traefik Dashboard**: https://traefik.fra-la.de (Login erforderlich)
- **Medical Translator App**: https://medical.fra-la.de
- **API**: https://medical.fra-la.de/api

## Befehle

### Traefik verwalten

```bash
# Status prüfen
cd traefik
docker compose ps

# Logs anzeigen
docker compose logs -f

# Stoppen
docker compose down

# Neustarten
docker compose restart
```

### App ohne Traefik (lokale Entwicklung)

```bash
# Nur die App starten (ohne Traefik)
docker compose up -d

# App ist dann direkt erreichbar unter:
# - Frontend: http://localhost:9121
# - Backend: http://localhost:9122
# - Ollama: http://localhost:7869
```

### App mit Traefik (Produktion)

```bash
# Mit Traefik-Labels starten
docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d

# App ist dann über Traefik erreichbar:
# - https://medical.fra-la.de
```

## Troubleshooting

### DNS Probleme

Wenn die SSL-Zertifikate nicht erstellt werden:

1. Prüfen Sie die DNS-Einträge bei Netcup:
   - A-Record für `fra-la.de` → Server IP
   - A-Record für `*.fra-la.de` → Server IP

2. Warten Sie auf DNS-Propagation (kann bis zu 24h dauern)

3. Prüfen Sie die Traefik Logs:
   ```bash
   cd traefik
   docker compose logs -f | grep acme
   ```

### Netzwerk-Probleme

Wenn die Container sich nicht verbinden können:

```bash
# Prüfen ob das Netzwerk existiert
docker network ls | grep traefik-proxy

# Netzwerk neu erstellen falls nötig
docker network create traefik-proxy

# Container neu starten
docker compose -f docker-compose.yml -f docker-compose.traefik.yml restart
```

### Port-Konflikte

Wenn Ports bereits belegt sind:

```bash
# Prüfen welcher Prozess Port 80/443 belegt
sudo lsof -i :80
sudo lsof -i :443

# Alten Traefik stoppen falls vorhanden
docker stop traefik
docker rm traefik
```

## Sicherheit

- Traefik Dashboard ist passwortgeschützt
- Automatische SSL-Zertifikate via Let's Encrypt
- Security Headers sind konfiguriert
- HSTS ist aktiviert mit Preload
- Alle HTTP-Anfragen werden zu HTTPS umgeleitet

## Architektur

```
Internet
    ↓
[Traefik Reverse Proxy]
    ├── traefik.fra-la.de (Dashboard)
    └── medical.fra-la.de
        ├── / → Frontend Container (Port 9121)
        └── /api → Backend Container (Port 9122)
```