# Deployment Documentation - DocTranslator

## Table of Contents
1. [Deployment Overview](#deployment-overview)
2. [Production Deployment](#production-deployment)
3. [Docker Configuration](#docker-configuration)
4. [Environment Configuration](#environment-configuration)
5. [SSL/TLS Setup](#ssltls-setup)
6. [Monitoring & Logging](#monitoring--logging)
7. [Backup & Recovery](#backup--recovery)
8. [Scaling & Performance](#scaling--performance)
9. [Troubleshooting](#troubleshooting)
10. [Security Hardening](#security-hardening)

## Deployment Overview

DocTranslator is designed for containerized deployment using Docker and Docker Compose. The application consists of three main services that can be deployed together or separately.

### Deployment Options

1. **Single Server**: All services on one machine (recommended for small-medium deployments)
2. **Distributed**: Services on separate machines (for high availability)
3. **Kubernetes**: Container orchestration for enterprise deployments
4. **Cloud Platforms**: AWS, Azure, GCP deployments

### System Requirements

#### Minimum Requirements
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Storage**: 50 GB SSD
- **OS**: Ubuntu 20.04+ / Debian 11+
- **Docker**: 24.0+
- **Network**: 100 Mbps

#### Recommended Requirements
- **CPU**: 8+ cores
- **RAM**: 16 GB
- **Storage**: 100 GB NVMe SSD
- **OS**: Ubuntu 22.04 LTS
- **Docker**: Latest stable
- **Network**: 1 Gbps

#### For GPU Acceleration (Optional)
- **GPU**: NVIDIA GPU with 8GB+ VRAM
- **Driver**: NVIDIA Driver 525+
- **CUDA**: 12.0+
- **Docker**: NVIDIA Container Toolkit

## Production Deployment

### Step-by-Step Deployment Guide

#### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    curl \
    git \
    wget \
    gnupg \
    lsb-release \
    ca-certificates \
    apt-transport-https \
    software-properties-common

# Set timezone
sudo timedatectl set-timezone Europe/Berlin

# Configure firewall
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable
```

#### 2. Install Docker

```bash
# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (optional)
sudo usermod -aG docker $USER
```

#### 3. Clone and Configure Application

```bash
# Create application directory
sudo mkdir -p /opt/doctranslator
cd /opt

# Clone repository
sudo git clone <repository-url> doctranslator
cd doctranslator

# Set permissions
sudo chown -R $USER:$USER /opt/doctranslator

# Create required directories
mkdir -p logs
mkdir -p data
```

#### 4. Configure Environment

```bash
# Copy environment template
cp .env.example .env.production

# Edit production configuration
nano .env.production
```

**Production Environment Variables:**
```env
# Application
ENVIRONMENT=production
APP_NAME=HealthLingo
APP_URL=https://medical.your-domain.de

# Security
SECRET_KEY=<generate-strong-secret>
ALLOWED_HOSTS=medical.your-domain.de

# Ollama
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=mistral-nemo:latest

# Rate Limiting
RATE_LIMIT_ENABLED=true
UPLOAD_RATE_LIMIT=5/minute
PROCESS_RATE_LIMIT=3/minute

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
```

#### 5. Update Docker Compose for Production

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    container_name: medical-translator-backend
    restart: always
    environment:
      - ENVIRONMENT=production
      - PYTHONPATH=/app
    volumes:
      - ./logs:/app/logs:rw
      - /tmp/medical-translator:/tmp:rw
    networks:
      - medical-network
      - ollama-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9122/api/health/simple"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  frontend:
    build: 
      context: ./frontend
      dockerfile: Dockerfile
    container_name: medical-translator-frontend
    restart: always
    depends_on:
      backend:
        condition: service_healthy
    environment:
      - REACT_APP_API_URL=/api
    networks:
      - proxy-network
      - medical-network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M

  ollama:
    image: ollama/ollama:latest
    container_name: medical-translator-ollama
    restart: always
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - ollama-network
    ports:
      - "11434:11434"
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G

networks:
  medical-network:
    driver: bridge
  ollama-network:
    driver: bridge
  proxy-network:
    external: true

volumes:
  ollama_data:
    driver: local
```

#### 6. Deploy Application

```bash
# Pull and build images
docker-compose -f docker-compose.production.yml pull
docker-compose -f docker-compose.production.yml build

# Start services
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f
```

#### 7. Initialize Ollama Models

```bash
# Pull required models
docker exec -it medical-translator-ollama ollama pull mistral-nemo:latest
docker exec -it medical-translator-ollama ollama pull llama3.2:latest

# Verify models
docker exec -it medical-translator-ollama ollama list
```

## Docker Configuration

### Dockerfile Optimization

#### Backend Dockerfile
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app

USER appuser
WORKDIR /app

# Copy application
COPY --chown=appuser:appuser . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9122/api/health/simple || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9122"]
```

#### Frontend Dockerfile
```dockerfile
# frontend/Dockerfile
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:9121/ || exit 1

EXPOSE 9121

CMD ["nginx", "-g", "daemon off;"]
```

### Docker Compose Best Practices

```yaml
# Best practices implemented
version: '3.8'

services:
  app:
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
    
    # Health checks
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      retries: 3
    
    # Restart policy
    restart: unless-stopped
    
    # Logging configuration
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    
    # Security options
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
```

## Environment Configuration

### Environment-Specific Settings

#### Production (.env.production)
```env
# Core Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Security
SECRET_KEY=${SECRET_KEY}
CORS_ORIGINS=https://medical.your-domain.de
TRUSTED_HOSTS=medical.your-domain.de

# Database (if needed)
DATABASE_URL=postgresql://user:pass@db:5432/medical

# Redis (for caching/queuing)
REDIS_URL=redis://redis:6379/0

# Monitoring
SENTRY_DSN=${SENTRY_DSN}
PROMETHEUS_ENABLED=true
```

#### Staging (.env.staging)
```env
ENVIRONMENT=staging
DEBUG=true
LOG_LEVEL=DEBUG
# Similar to production but with test endpoints
```

#### Development (.env.development)
```env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
CORS_ORIGINS=*
```

### Configuration Management

```bash
# Use environment-specific compose files
docker-compose -f docker-compose.yml -f docker-compose.production.yml up

# Override with environment variables
ENVIRONMENT=production docker-compose up

# Use .env files
docker-compose --env-file .env.production up
```

## SSL/TLS Setup

### Using Traefik

```yaml
# docker-compose.traefik.yml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    container_name: traefik
    restart: always
    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@your-domain.de"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./letsencrypt:/letsencrypt
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - proxy-network

  frontend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.medical-app.rule=Host(`medical.your-domain.de`)"
      - "traefik.http.routers.medical-app.entrypoints=websecure"
      - "traefik.http.routers.medical-app.tls.certresolver=letsencrypt"
      - "traefik.http.services.medical-app.loadbalancer.server.port=9121"
      # Redirect HTTP to HTTPS
      - "traefik.http.routers.medical-app-http.rule=Host(`medical.your-domain.de`)"
      - "traefik.http.routers.medical-app-http.entrypoints=web"
      - "traefik.http.routers.medical-app-http.middlewares=redirect-to-https"
      - "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https"
```

### Using Nginx with Certbot

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d medical.your-domain.de

# Auto-renewal
sudo certbot renew --dry-run
```

## Monitoring & Logging

### Logging Strategy

#### Application Logs
```python
# Structured logging configuration
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler('/app/logs/app.log'),
        logging.StreamHandler()
    ]
)
```

#### Log Aggregation with ELK Stack

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    volumes:
      - es_data:/usr/share/elasticsearch/data
    networks:
      - monitoring

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
      - ./logs:/logs:ro
    networks:
      - monitoring

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    networks:
      - monitoring

volumes:
  es_data:

networks:
  monitoring:
```

### Monitoring with Prometheus & Grafana

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'medical-translator'
    static_configs:
      - targets: ['backend:9090']
        labels:
          app: 'medical-translator'
          
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    ports:
      - "3000:3000"
    networks:
      - monitoring

  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    networks:
      - monitoring
```

### Health Monitoring

```bash
# Health check script
#!/bin/bash
# check_health.sh

#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 DocTranslator Health Check"
echo "=============================="

# Check Docker services
echo -n "Docker Services: "
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Some services are down${NC}"
    docker-compose ps
fi

# Check API health
echo -n "Backend API: "
if curl -sf http://localhost:9122/api/health > /dev/null; then
    echo -e "${GREEN}✓ Healthy${NC}"
else
    echo -e "${RED}✗ Unhealthy${NC}"
fi

# Check Ollama
echo -n "Ollama Service: "
if curl -sf http://localhost:11434/api/version > /dev/null; then
    echo -e "${GREEN}✓ Connected${NC}"
else
    echo -e "${YELLOW}⚠ Not accessible${NC}"
fi

# Check disk space
echo -n "Disk Space: "
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    echo -e "${GREEN}✓ ${DISK_USAGE}% used${NC}"
else
    echo -e "${YELLOW}⚠ ${DISK_USAGE}% used${NC}"
fi

# Check memory
echo -n "Memory Usage: "
MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
if [ "$MEM_USAGE" -lt 80 ]; then
    echo -e "${GREEN}✓ ${MEM_USAGE}% used${NC}"
else
    echo -e "${YELLOW}⚠ ${MEM_USAGE}% used${NC}"
fi
```

## Backup & Recovery

### Backup Strategy

#### Automated Backup Script
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/doctranslator"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${DATE}"

# Create backup directory
mkdir -p ${BACKUP_DIR}/${BACKUP_NAME}

# Backup Docker volumes
docker run --rm \
    -v doctranslator_ollama_data:/data \
    -v ${BACKUP_DIR}/${BACKUP_NAME}:/backup \
    alpine tar czf /backup/ollama_data.tar.gz -C /data .

# Backup configuration
cp -r /opt/doctranslator/.env* ${BACKUP_DIR}/${BACKUP_NAME}/
cp -r /opt/doctranslator/docker-compose*.yml ${BACKUP_DIR}/${BACKUP_NAME}/

# Backup logs
tar czf ${BACKUP_DIR}/${BACKUP_NAME}/logs.tar.gz /opt/doctranslator/logs/

# Clean old backups (keep last 7 days)
find ${BACKUP_DIR} -type d -mtime +7 -exec rm -rf {} \;

echo "Backup completed: ${BACKUP_DIR}/${BACKUP_NAME}"
```

#### Automated Backup with Cron
```bash
# Add to crontab
0 2 * * * /opt/doctranslator/scripts/backup.sh >> /var/log/backup.log 2>&1
```

### Recovery Procedure

```bash
#!/bin/bash
# restore.sh

BACKUP_PATH=$1

if [ -z "$BACKUP_PATH" ]; then
    echo "Usage: ./restore.sh <backup_path>"
    exit 1
fi

# Stop services
docker-compose down

# Restore volumes
docker run --rm \
    -v doctranslator_ollama_data:/data \
    -v ${BACKUP_PATH}:/backup \
    alpine tar xzf /backup/ollama_data.tar.gz -C /data

# Restore configuration
cp ${BACKUP_PATH}/.env* /opt/doctranslator/
cp ${BACKUP_PATH}/docker-compose*.yml /opt/doctranslator/

# Start services
docker-compose up -d

echo "Restore completed from: ${BACKUP_PATH}"
```

## Scaling & Performance

### Horizontal Scaling

#### Load Balancer Configuration
```nginx
# nginx load balancer
upstream backend_servers {
    least_conn;
    server backend1:9122 weight=1;
    server backend2:9122 weight=1;
    server backend3:9122 weight=1;
}

server {
    listen 80;
    server_name medical.your-domain.de;
    
    location /api {
        proxy_pass http://backend_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Docker Swarm Deployment
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.swarm.yml medical

# Scale service
docker service scale medical_backend=3
```

### Performance Tuning

#### System Tuning
```bash
# /etc/sysctl.conf
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
fs.file-max = 100000

# Apply settings
sudo sysctl -p
```

#### Docker Optimization
```json
// /etc/docker/daemon.json
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-ulimits": {
    "nofile": {
      "Hard": 65535,
      "Soft": 65535
    }
  }
}
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: Container Won't Start
```bash
# Check logs
docker-compose logs backend

# Common solutions:
# 1. Check port conflicts
sudo netstat -tlnp | grep -E '9121|9122|11434'

# 2. Check permissions
sudo chown -R 1000:1000 /opt/doctranslator

# 3. Rebuild container
docker-compose build --no-cache backend
docker-compose up -d backend
```

#### Issue: Ollama Connection Failed
```bash
# Check Ollama status
docker exec -it ollama curl http://localhost:11434/api/version

# Check network connectivity
docker network inspect doctranslator_ollama-network

# Restart Ollama
docker-compose restart ollama

# Re-pull models
docker exec -it ollama ollama pull mistral-nemo:latest
```

#### Issue: High Memory Usage
```bash
# Check container stats
docker stats --no-stream

# Limit memory usage
docker-compose down
# Edit docker-compose.yml to add memory limits
docker-compose up -d

# Clear Docker cache
docker system prune -a
```

#### Issue: Slow Processing
```bash
# Check CPU usage
htop

# Check I/O wait
iostat -x 1

# Optimize Ollama
docker exec -it ollama bash
# Inside container:
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_MAX_LOADED_MODELS=1
```

### Debug Commands

```bash
# Container inspection
docker inspect medical-translator-backend

# Network debugging
docker network ls
docker network inspect medical-network

# Volume inspection
docker volume ls
docker volume inspect doctranslator_ollama_data

# Process monitoring
docker exec -it backend ps aux
docker exec -it backend netstat -tulpn

# Log analysis
docker-compose logs --tail=100 backend
docker-compose logs --since=1h frontend

# Resource usage
docker system df
docker ps --size
```

## Security Hardening

### Security Checklist

#### System Level
- [ ] Regular system updates
- [ ] Firewall configured (UFW/iptables)
- [ ] SSH hardened (key-only, non-root)
- [ ] Fail2ban installed
- [ ] SELinux/AppArmor enabled

#### Docker Security
- [ ] Latest Docker version
- [ ] User namespaces enabled
- [ ] Read-only containers where possible
- [ ] Secrets management (not in env vars)
- [ ] Security scanning (Trivy, Clair)

#### Application Security
- [ ] HTTPS enforced
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Input validation comprehensive
- [ ] No sensitive data in logs

### Security Configuration

```yaml
# docker-compose.security.yml
services:
  backend:
    security_opt:
      - no-new-privileges:true
      - seccomp:unconfined
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp
      - /run
    user: "1000:1000"
```

### Regular Security Tasks

```bash
# Weekly security updates
#!/bin/bash
apt update && apt upgrade -y
docker system prune -a
docker pull ollama/ollama:latest

# Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image medical-translator-backend:latest

# Check for secrets in code
docker run --rm -v $(pwd):/code \
    zricethezav/gitleaks:latest detect --source /code
```

---

*Deployment Documentation Version: 1.0.0 | Last Updated: January 2025*