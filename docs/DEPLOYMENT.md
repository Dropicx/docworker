# Deployment Guide

DocTranslator uses a multi-cloud deployment architecture:

- **Railway** (Frankfurt, EU) - Main application (Backend, Frontend, Worker, Database, Redis)
- **Hetzner** (Germany, EU) - External services (PII removal, OCR fallback)
- **OVH AI Endpoints** (EU) - LLM translation services
- **Mistral AI** (France, EU) - Primary OCR and feedback analysis

---

## Table of Contents

1. [Railway Deployment](#railway-deployment)
2. [Hetzner Services](#hetzner-services)
3. [Local Development](#local-development)
4. [Environment Variables](#environment-variables)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Monitoring & Troubleshooting](#monitoring--troubleshooting)

---

## Railway Deployment

### Prerequisites

- Railway account ([railway.app](https://railway.app))
- GitHub repository connected
- OVH AI Endpoints access token
- Mistral AI API key from [console.mistral.ai](https://console.mistral.ai)

### Architecture on Railway

```
Railway Project
├── Frontend (nginx + React)     Port 80
├── Backend (FastAPI)            Port 9122
├── Worker (Celery)              Background
├── Beat (Celery scheduler)      Background
├── PostgreSQL                   Managed
└── Redis                        Managed
```

### Step 1: Create Project

1. Log in to Railway Dashboard
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway auto-detects services from `railway.json`

### Step 2: Configure Services

Railway should auto-configure these services from `railway.json`:

**Frontend:**
- Root: `/frontend`
- Builder: Dockerfile
- Port: 80

**Backend:**
- Root: `/backend`
- Builder: Dockerfile
- Port: 9122

**Worker:**
- Root: `/worker`
- Builder: Dockerfile
- No port (background service)

**Beat:**
- Root: `/worker`
- Builder: Dockerfile
- Command: `celery -A worker.worker beat --loglevel=info`

### Step 3: Add PostgreSQL

1. In Railway project, click "+ New"
2. Select "Database" → "PostgreSQL"
3. Railway auto-configures `DATABASE_URL`

### Step 4: Add Redis

1. Click "+ New"
2. Select "Database" → "Redis"
3. Railway auto-configures `REDIS_URL`

### Step 5: Set Environment Variables

Add these to all services (shared variables):

```bash
# Required
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-ovh-token
MISTRAL_API_KEY=your-mistral-api-key
USE_OVH_ONLY=true
ENVIRONMENT=production

# Hetzner PII Service
EXTERNAL_PII_URL=https://pii.your-domain.de
EXTERNAL_PII_API_KEY=your-pii-api-key
USE_EXTERNAL_PII=true

# Hetzner OCR Service (optional)
PADDLEOCR_SERVICE_URL=https://ocr.your-domain.de

# Security
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars
ENCRYPTION_KEY=your-fernet-encryption-key

# Optional
LOG_LEVEL=INFO
DEBUG=false
```

### Step 6: Configure Environments

Railway supports multiple environments. Set up:

**Development (dev branch):**
- Lower resources
- Debug logging
- Test API keys

**Production (main branch):**
- Higher resources
- INFO logging
- Production API keys

### Step 7: Deploy

Push to your branch - Railway auto-deploys:

```bash
git push origin dev      # Deploy to dev
git push origin main     # Deploy to production
```

### Step 8: Verify Deployment

```bash
# Health checks
curl https://your-app.railway.app/health
curl https://your-app.railway.app/api/health/detailed

# Test upload
curl -X POST https://your-app.railway.app/api/upload \
  -F "file=@test.pdf"
```

---

## Hetzner Services

### PII Service Deployment

**Infrastructure**: 2x CPX32 (4 vCPU, 8GB RAM), Load Balancer, Managed SSL

#### Using Terraform

```bash
cd external_deployment/hetzner_pii/terraform

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
hcloud_token = "your-hetzner-api-token"
dns_zone = "your-domain.de"
dns_subdomain = "pii"
github_repo = "your-org/doctranslator"
github_branch = "dev"
github_token = "your-github-token"  # For private repos
EOF

# Initialize and apply
terraform init
terraform apply
```

#### Terraform Resources Created

- 2x Hetzner CPX32 servers
- Private network (10.1.0.0/16)
- Load balancer with managed SSL certificate
- DNS A record for subdomain
- Firewall rules
- Auto-deployment via cloud-init

#### Get Credentials

```bash
# API key (for Railway backend)
terraform output -raw api_key

# Server passwords (for console access)
terraform output -json server_root_passwords

# Service URL
terraform output api_endpoint
```

#### Verify PII Service

```bash
# Health check
curl https://pii.your-domain.de/health

# Expected response
{
  "status": "healthy",
  "german_model_loaded": true,
  "english_model_loaded": true,
  "presidio_available": true
}
```

### OCR Service Deployment

**Infrastructure**: 2x CPX41 (8 vCPU, 16GB RAM), Load Balancer, Managed SSL

```bash
cd external_deployment/hetzner_paddleocr/terraform

# Create terraform.tfvars (similar to PII)
terraform init
terraform apply
```

#### Verify OCR Service

```bash
curl https://ocr.your-domain.de/health

# Expected response
{
  "status": "healthy",
  "paddleocr_available": true
}
```

### Connecting Railway to Hetzner

Add to Railway environment variables:

```bash
# PII Service
EXTERNAL_PII_URL=https://pii.your-domain.de
EXTERNAL_PII_API_KEY=<from terraform output>
USE_EXTERNAL_PII=true

# OCR Service
PADDLEOCR_SERVICE_URL=https://ocr.your-domain.de
```

---

## Local Development

### Quick Start with Docker

```bash
# Clone repository
git clone https://github.com/your-org/doctranslator.git
cd doctranslator

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Setup

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Tesseract (Ubuntu/Debian)
sudo apt-get install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng

# Set environment variables
export OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token
export USE_OVH_ONLY=true
export DATABASE_URL=sqlite:///./dev.db

# Initialize database
python app/database/init_db.py
python app/database/unified_seed.py

# Run server
python -m uvicorn app.main:app --reload --port 9122
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

#### Worker (optional)

```bash
cd worker

# Start Celery worker
celery -A worker.worker worker --loglevel=info

# Start Beat scheduler (separate terminal)
celery -A worker.worker beat --loglevel=info
```

#### Redis (for local worker)

```bash
# Using Docker
docker run -d --name redis -p 6379:6379 redis:7

# Set environment
export REDIS_URL=redis://localhost:6379
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OVH_AI_ENDPOINTS_ACCESS_TOKEN` | OVH API token | `sk-xxx` |
| `MISTRAL_API_KEY` | Mistral AI API key (OCR + feedback) | `sk-xxx` |
| `USE_OVH_ONLY` | Enable OVH cloud | `true` |
| `DATABASE_URL` | PostgreSQL connection | Auto from Railway |
| `REDIS_URL` | Redis connection | Auto from Railway |
| `JWT_SECRET_KEY` | JWT signing key (32+ chars) | Random string |

### Hetzner Integration

| Variable | Description | Example |
|----------|-------------|---------|
| `EXTERNAL_PII_URL` | Hetzner PII service URL | `https://pii.domain.de` |
| `EXTERNAL_PII_API_KEY` | PII service API key | From Terraform |
| `USE_EXTERNAL_PII` | Enable external PII | `true` |
| `PADDLEOCR_SERVICE_URL` | Hetzner OCR URL | `https://ocr.domain.de` |

### Mistral AI (France)

| Variable | Description | Example |
|----------|-------------|---------|
| `MISTRAL_API_KEY` | API key from console.mistral.ai | `sk-xxx` |

**Services Used**:
- Primary OCR (`mistral-ocr-latest`)
- Feedback analysis (`mistral-large-latest`)

### OVH AI Models

| Variable | Description | Default |
|----------|-------------|---------|
| `OVH_MAIN_MODEL` | Main LLM | `Meta-Llama-3.3-70B-Instruct` |
| `OVH_PREPROCESSING_MODEL` | Fast LLM | `Mistral-Nemo-Instruct-2407` |
| `OVH_VISION_MODEL` | Vision LLM | `Qwen2.5-VL-72B-Instruct` |
| `OVH_AI_BASE_URL` | OVH endpoint | `https://oai.endpoints...` |

### Security

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `15` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | `7` |
| `ENCRYPTION_KEY` | Fernet key for file encryption | Auto-generated |
| `CORS_ORIGINS` | Allowed origins | `*` |

### Operations

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment name | `production` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DEBUG` | Debug mode | `false` |
| `WORKER_CONCURRENCY` | Celery workers | `2` |
| `DATA_RETENTION_HOURS` | Job retention | `24` |

---

## CI/CD Pipeline

### GitHub Actions Workflow

The project uses GitHub Actions with self-hosted runners (ARC on Kubernetes).

#### Workflow Triggers

- Push to `dev` → Run all checks
- Push to `main` → Run all checks + deploy
- Pull request → Run all checks

#### Jobs

1. **Backend Quality**
   - Ruff linting and formatting
   - MyPy type checking
   - Bandit security scan

2. **Backend Tests**
   - pytest with PostgreSQL container
   - Coverage report

3. **Frontend Quality**
   - ESLint
   - Prettier formatting
   - TypeScript type checking

4. **Frontend Build**
   - Production build verification

5. **Security Audit**
   - pip-audit (Python)
   - npm audit (Node.js)

6. **Quality Gate**
   - All jobs must pass

### Running Checks Locally

```bash
# Backend
cd backend
ruff check app/
ruff format app/ --check
mypy app/
bandit -r app/
pytest

# Frontend
cd frontend
npm run lint
npm run format:check
npm run type-check
npm run build
```

### ARC Runner Requirements

For self-hosted runners:

- Docker daemon access (for PostgreSQL containers)
- Python 3.11+
- Node.js 18+
- 4GB+ RAM

---

## Monitoring & Troubleshooting

### Health Endpoints

```bash
# Backend
curl https://app.railway.app/health
curl https://app.railway.app/api/health/detailed

# PII Service
curl https://pii.your-domain.de/health

# OCR Service
curl https://ocr.your-domain.de/health
```

### Railway Logs

```bash
# Using Railway CLI
railway logs --tail 100
railway logs -f  # Real-time

# Filter by service
railway logs -s backend
railway logs -s worker
```

### Hetzner Server Access

```bash
# Get server password
terraform output -json server_root_passwords

# SSH to server
ssh root@<server-ip>

# View service logs
journalctl -u pii -f
docker compose logs -f
```

### Common Issues

#### PII Service Not Responding

```bash
# Check server status
ssh root@<pii-server>
systemctl status pii
docker compose ps

# Restart service
systemctl restart pii

# Check logs
journalctl -u pii -n 100
```

#### Worker Not Processing Tasks

```bash
# Check worker status in Railway
railway logs -s worker

# Check Redis connection
railway run redis-cli ping

# Check queue length
railway run redis-cli llen celery
```

#### Database Connection Issues

```bash
# Test connection
railway run psql -c "SELECT 1"

# Check connection pool
railway logs -s backend | grep "pool"
```

#### OCR Failures

```bash
# Check OCR service health
curl https://ocr.your-domain.de/health

# Check worker OCR logs
railway logs -s worker | grep "OCR"

# Verify fallback is working
curl https://app.railway.app/api/pipeline/ocr-engines
```

### Performance Monitoring

#### Railway Dashboard

- CPU/Memory usage per service
- Request latency
- Error rates
- Deploy history

#### Cost Monitoring

```bash
# Check AI token usage
curl https://app.railway.app/api/cost/summary \
  -H "Authorization: Bearer $TOKEN"
```

---

## Scaling

### Railway Scaling

```yaml
# In railway.json
{
  "services": {
    "worker": {
      "replicas": 2  # Add more workers
    }
  }
}
```

Or via Railway Dashboard:
- Settings → Replicas → Increase count

### Hetzner Scaling

```hcl
# In terraform.tfvars
server_count = 3  # Add more servers

# Apply changes
terraform apply
```

### Worker Concurrency

```bash
# Increase workers per instance
WORKER_CONCURRENCY=4  # Default is 2
```

---

## Backup & Recovery

### Database Backup

```bash
# Manual backup
railway run pg_dump > backup_$(date +%Y%m%d).sql

# Restore
railway run psql < backup.sql
```

### Automated Backups

Railway PostgreSQL includes daily automated backups. Access via Railway Dashboard → Database → Backups.

### Rollback

```bash
# Via Railway CLI
railway rollback

# Via Dashboard
# Deployments → Select previous → Redeploy

# Via Git
git revert HEAD
git push
```

---

## Security Checklist

- [ ] OVH token stored in Railway environment variables (not in code)
- [ ] Mistral API key stored in Railway environment variables (not in code)
- [ ] JWT secret key is 32+ characters
- [ ] HTTPS enabled (automatic on Railway)
- [ ] Hetzner services use managed SSL
- [ ] API keys for Hetzner services are unique per environment
- [ ] Database has strong password
- [ ] CORS origins restricted in production
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] Data retention configured (24 hours default)

---

*Last Updated: January 2026*
