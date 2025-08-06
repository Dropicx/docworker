#!/bin/bash

# Umgebungsvariablen setzen
#export GIT_USERNAME='dein_username'
#export GIT_TOKEN='dein_token'

# Skript ausführbar machen und starten
#chmod +x deploy.sh
#./deploy.sh

# Konfiguration über Umgebungsvariablen
USERNAME="${GIT_USERNAME}"
TOKEN="${GIT_TOKEN}"
REPO_URL="https://github.com/Dropicx/doctranslator"
BRANCH="${1:-main}"  # Standard Branch ist 'main', kann als Parameter übergeben werden

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Prüfung der Umgebungsvariablen
if [ -z "$GIT_USERNAME" ] || [ -z "$GIT_TOKEN" ]; then
    echo -e "${RED}Error: GIT_USERNAME and GIT_TOKEN environment variables must be set${NC}"
    echo "Set them with:"
    echo "export GIT_USERNAME='your_username'"
    echo "export GIT_TOKEN='your_token'"
    exit 1
fi

echo -e "${YELLOW}Starting deployment process for branch: ${BRANCH}${NC}"

# Branch Selection - falls interaktive Auswahl gewünscht
if [ "$1" = "--interactive" ] || [ "$1" = "-i" ]; then
    echo -e "${YELLOW}Available branches:${NC}"
    sudo git branch -r --format="%(refname:short)" | grep -v HEAD | sed 's/origin\///'
    echo ""
    read -p "Enter branch name (default: main): " INPUT_BRANCH
    BRANCH="${INPUT_BRANCH:-main}"
    echo -e "${GREEN}Selected branch: ${BRANCH}${NC}"
fi

# Docker Compose Down
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker compose down

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Containers stopped successfully${NC}"
else
    echo -e "${YELLOW}No containers were running or docker compose down failed${NC}"
fi

# Git Pull mit Token
echo -e "${YELLOW}Switching to branch ${BRANCH} and pulling latest changes...${NC}"
sudo git checkout ${BRANCH}
sudo git pull https://${USERNAME}:${TOKEN}@${REPO_URL#https://} ${BRANCH}


if [ $? -eq 0 ]; then
    echo -e "${GREEN}Git pull successful${NC}"
else
    echo -e "${RED}Git pull failed!${NC}"
    exit 1
fi

# Docker Compose Build
echo -e "${YELLOW}Building Docker containers...${NC}"
docker compose build

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Docker build successful${NC}"
else
    echo -e "${RED}Docker build failed!${NC}"
    exit 1
fi

# Docker Compose Up
echo -e "${YELLOW}Starting containers...${NC}"
docker compose up -d

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Containers started successfully!${NC}"
    echo -e "${GREEN}Deployment completed!${NC}"
else
    echo -e "${RED}Failed to start containers!${NC}"
    exit 1
fi

# Optional: Status anzeigen
echo -e "${YELLOW}Container status:${NC}"
docker compose ps