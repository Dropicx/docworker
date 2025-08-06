# DocTranslator - Medical Document Translator

Eine DSGVO-konforme Anwendung zur Übersetzung medizinischer Dokumente mit lokaler KI-Verarbeitung.

## 📋 Übersicht

DocTranslator ist eine webbasierte Anwendung, die es ermöglicht, medizinische Dokumente sicher und datenschutzkonform zu übersetzen. Die gesamte Verarbeitung erfolgt lokal auf dem Server, ohne dass Daten an externe Dienste übertragen werden.

### Funktionen

- 🏥 **Medizinische Fachübersetzungen** - Speziell trainiert für medizinische Terminologie
- 🔒 **DSGVO-konform** - Keine Datenübertragung an externe Dienste
- 📄 **Mehrere Dateiformate** - Unterstützung für PDF, TXT und Bilddateien
- 🤖 **Lokale KI** - Verwendet Ollama für lokale Sprachmodelle
- 🎨 **Moderne Benutzeroberfläche** - React-basiertes Frontend mit Tailwind CSS
- ⚡ **Schnelle API** - FastAPI-Backend für optimale Performance

### 🔬 Spezialisierter Medizinischer Systemprompt

Der DocTranslator verwendet einen hochspezialisierten Systemprompt für maximale medizinische Genauigkeit:

#### Kernfeatures:
- **⚕️ Absolute Sicherheitsregeln**: Verhindert das Hinzufügen, Weglassen oder Verändern von Diagnosen
- **📋 Strukturiertes Ausgabeformat**: Klare Gliederung mit Zusammenfassung, Befunden, Diagnosen und Wörterbuch
- **🎯 4-Stufen-Verarbeitungsprozess**:
  1. **Analyse**: Dokumenttyp-Erkennung und Strukturanalyse
  2. **Extraktion**: Systematische Erfassung aller medizinischen Informationen
  3. **Übersetzung**: Schrittweise Übersetzung in verständliche Sprache
  4. **Validierung**: Qualitätskontrolle und Vollständigkeitsprüfung

#### Dokumenttyp-Spezialisierung:
- **🩺 Arztbriefe**: Fokus auf Diagnosen und Therapieempfehlungen
- **🧪 Laborbefunde**: Detaillierte Werteerklärungen mit Normalbereich-Vergleichen
- **📷 Radiologie-Befunde**: Bildgebungserklärungen und anatomische Strukturen
- **🔬 Pathologie-Befunde**: Sensitive Kommunikation von Gewebeveränderungen
- **🏠 Entlassungsbriefe**: Nachsorgehinweise und Verhaltensempfehlungen

#### Sprachliche Qualität:
- **💬 Patientenfreundliche Sprache**: Kurze Hauptsätze, aktive Formulierungen
- **📚 Fachbegriff-Wörterbuch**: Alphabetische Erklärung aller medizinischen Begriffe
- **🛡️ Sicherheitsmechanismen**: Markierung von Unsicherheiten mit [?] und Arzt-Rücksprache-Hinweisen
- **⚖️ Rechtlicher Hinweis**: Klare Abgrenzung zur medizinischen Beratung

### Technischer Stack

- **Frontend**: React 18 mit TypeScript und Tailwind CSS
- **Backend**: FastAPI (Python)
- **KI-Engine**: Ollama mit lokalen Sprachmodellen
- **Containerisierung**: Docker & Docker Compose
- **Reverse Proxy**: Traefik (für Produktion)
- **OCR**: Tesseract für Texterkennung in Bildern

### Projektstruktur

```
doctranslator/
├── backend/            # FastAPI Backend-Anwendung
│   ├── app/           # Hauptanwendung
│   └── tests/         # Test-Dateien
├── frontend/          # React Frontend-Anwendung
│   ├── src/          # React-Quellcode
│   └── public/       # Statische Dateien
├── docs/             # Projektdokumentation
│   ├── api/          # API-Dokumentation
│   ├── architecture/ # Architektur-Dokumentation
│   ├── deployment/   # Deployment-Anleitungen
│   └── user-guide/   # Benutzerhandbuch
├── scripts/          # Utility-Skripte
│   └── claude-flow/  # Claude-Flow Integration
├── ollama/           # Ollama-Konfiguration
├── traefik/          # Traefik-Konfiguration
├── memory/           # Claude-Flow Speicher
├── docker-compose.yml        # Docker-Compose Hauptkonfiguration
├── docker-compose.traefik.yml # Traefik-spezifische Konfiguration
├── start.sh          # Hauptstart-Skript
└── start-with-traefik.sh # Start-Skript mit Traefik
```

## 🚀 Installation auf Ubuntu Server

### Voraussetzungen

- Ubuntu Server 20.04 oder höher
- Mindestens 8 GB RAM (16 GB empfohlen für bessere KI-Performance)
- Mindestens 50 GB freier Speicherplatz
- Root- oder sudo-Berechtigungen

### 1. System aktualisieren

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Docker installieren

```bash
# Docker Repository hinzufügen
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker installieren
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Docker-Dienst starten und aktivieren
sudo systemctl start docker
sudo systemctl enable docker

# Benutzer zur Docker-Gruppe hinzufügen (optional)
sudo usermod -aG docker $USER
```

**Wichtig**: Nach dem Hinzufügen zur Docker-Gruppe müssen Sie sich ab- und wieder anmelden.

### 3. Docker Compose installieren

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 4. Zusätzliche Abhängigkeiten installieren

```bash
# Tesseract für OCR
sudo apt install -y tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng

# Git (falls noch nicht installiert)
sudo apt install -y git curl

# Für die Gesundheitschecks
sudo apt install -y curl
```

### 5. Projekt klonen und konfigurieren

```bash
# Projekt klonen
git clone <repository-url> /opt/doctranslator
cd /opt/doctranslator

# Berechtigungen setzen
sudo chown -R $USER:$USER /opt/doctranslator
chmod +x start.sh start-with-traefik.sh scripts/*.sh
```

### 6. Konfiguration anpassen

Bearbeiten Sie die `docker-compose.yml` Datei und passen Sie folgende Einstellungen an:

```bash
nano docker-compose.yml
```

**Wichtige Anpassungen:**
- Zeile 35: `Host(\`medical.ihre-domain.de\`)` - Ersetzen Sie `ihre-domain.de` durch Ihre Domain
- Traefik-Konfiguration (falls Sie bereits Traefik verwenden)

### 7. Traefik-Netzwerk erstellen (für Produktion)

```bash
# Traefik-Netzwerk erstellen
docker network create traefik
```

**Hinweis**: Wenn Sie noch kein Traefik haben, können Sie die Traefik-Labels in der docker-compose.yml auskommentieren und einen direkten Port-Zugang konfigurieren.

### 8. Anwendung starten

```bash
# Anwendung im Hintergrund starten
docker-compose up -d

# Logs verfolgen (optional)
docker-compose logs -f
```

### 9. Gesundheitscheck durchführen

```bash
# Integrierten Check verwenden
./scripts/check.sh

# Oder manuell prüfen
docker-compose ps
```

## 🔧 Konfiguration

### Umgebungsvariablen

Die wichtigsten Konfigurationsoptionen können in der `docker-compose.yml` angepasst werden:

- `REACT_APP_API_URL`: Frontend-API-URL (Standard: `/api`)
- `ENVIRONMENT`: Backend-Umgebung (Standard: `production`)
- `PYTHONPATH`: Python-Pfad für das Backend

### Ollama-Modelle

Nach dem ersten Start müssen Sie die gewünschten Sprachmodelle herunterladen:

```bash
# Ins Ollama-Container verbinden
docker-compose exec ollama bash

# Standard-Modell für medizinische Übersetzungen
ollama pull mistral-nemo:latest

# Zusätzliche empfohlene Modelle
ollama pull llama3.2:latest
ollama pull meditron:7b
```

### Logs und Monitoring

```bash
# Alle Service-Logs anzeigen
docker-compose logs

# Spezifisches Service-Log
docker-compose logs backend
docker-compose logs frontend
docker-compose logs ollama

# Live-Logs verfolgen
docker-compose logs -f backend
```

## 🔍 Fehlerbehebung

### Häufige Probleme

1. **Container starten nicht**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

2. **Speicherplatz-Probleme**:
   ```bash
   # Docker-System bereinigen
   docker system prune -a
   ```

3. **Ollama-Modelle nicht verfügbar**:
   ```bash
   docker-compose exec ollama ollama list
   docker-compose exec ollama ollama pull mistral-nemo:latest
   ```

### Performance-Optimierung

- **Für bessere KI-Performance**: Mindestens 16 GB RAM
- **SSD-Speicher**: Empfohlen für bessere I/O-Performance
- **GPU-Unterstützung**: Ollama unterstützt NVIDIA GPUs (zusätzliche Konfiguration erforderlich)

## 🛡️ Sicherheit

- Alle Verarbeitungen erfolgen lokal
- Keine Datenübertragung an externe Dienste
- HTTPS-Verschlüsselung durch Traefik
- Sicherheits-Header werden automatisch gesetzt

## 📝 Wartung

### Backup

```bash
# Docker-Volumes sichern
docker-compose down
sudo tar -czf doctranslator-backup-$(date +%Y%m%d).tar.gz /var/lib/docker/volumes/doctranslator_ollama_data
```

### Updates

```bash
# Code aktualisieren
git pull

# Container neu bauen und starten
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 📞 Support

Bei Problemen oder Fragen:

1. Überprüfen Sie die Logs: `docker-compose logs`
2. Führen Sie den Gesundheitscheck aus: `./scripts/check.sh`
3. Dokumentation im `docs/` Ordner konsultieren
4. Technische Dokumentation der verwendeten Frameworks prüfen

## 📄 Lizenz

[Lizenzinformationen hier einfügen]