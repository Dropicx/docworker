# Deployment Guide

## Railway Deployment (Recommended)

### Prerequisites
1. Railway account ([railway.app](https://railway.app))
2. OVH AI Endpoints access token
3. GitHub repository with code

### Step 1: Connect Repository

1. Log in to Railway Dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose repository and branch: `railwaywithovhapi`

### Step 2: Configure Environment Variables

Add these in Railway project settings:

```bash
# Required
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-ovh-token-here
OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
USE_OVH_ONLY=true
ENVIRONMENT=production

# AI Models (optional - defaults provided)
OVH_MAIN_MODEL=Meta-Llama-3_3-70B-Instruct
OVH_PREPROCESSING_MODEL=Mistral-Nemo-Instruct-2407
OVH_TRANSLATION_MODEL=Meta-Llama-3_3-70B-Instruct

# Logging (optional)
LOG_LEVEL=INFO

# Database (auto-configured by Railway if PostgreSQL added)
DATABASE_URL=postgresql://...  # Auto-provided by Railway
```

### Step 3: Add PostgreSQL Database

1. In Railway project, click "New Service"
2. Select "Database" → "PostgreSQL"
3. Railway auto-configures `DATABASE_URL`
4. Database tables created automatically on first run

### Step 4: Add PaddleOCR Microservice (Optional)

PaddleOCR provides fast CPU-based OCR as a separate microservice.

#### Deploy PaddleOCR Service

1. In Railway project, click "New Service"
2. Select "Empty Service"
3. Configure service:
   - **Name**: `paddleocr-service`
   - **Root Directory**: `/paddleocr_service`
   - **Dockerfile Path**: `/dockerfiles/Dockerfile.paddleocr`
   - **Port**: `9123`

#### Environment Variables for PaddleOCR

```bash
# Service port
PORT=9123

# Internal service URL (for backend to connect)
# Add this to the BACKEND service environment
PADDLEOCR_SERVICE_URL=http://paddleocr-service.railway.internal:9123
```

#### Service Configuration

Railway automatically:
- Builds the PaddleOCR Docker container
- Exposes internal service at `paddleocr-service.railway.internal:9123`
- Provides IPv6 networking for service-to-service communication
- Sets up health checks at `/health` endpoint

#### Verify PaddleOCR Service

1. Check health endpoint: `http://paddleocr-service.railway.internal:9123/health` (from backend)
2. Monitor service logs for successful startup: `✅ PaddleOCR initialized successfully`
3. Test OCR extraction via backend API

#### Connect Backend to PaddleOCR

The backend service needs the PaddleOCR service URL. Add to **backend service** environment variables:

```bash
PADDLEOCR_SERVICE_URL=http://paddleocr-service.railway.internal:9123
```

The backend will automatically:
- Detect PaddleOCR availability via health check
- Use PaddleOCR for PADDLEOCR engine selection
- Fallback to hybrid extraction if service unavailable

### Step 5: Deploy

Railway automatically:
- Detects `railway.json` configuration
- Uses `Dockerfile.railway` for build
- Builds backend and frontend
- Configures nginx reverse proxy
- Sets up health checks
- Provides HTTPS domain

### Step 6: Verify Deployment

1. Check health endpoint: `https://your-app.up.railway.app/health`
2. Access web interface: `https://your-app.up.railway.app/`
3. Monitor logs in Railway dashboard
4. Test document upload and processing
5. Verify PaddleOCR service (if deployed): Check OCR engines API shows PaddleOCR as available

## Docker Deployment (Self-Hosted)

### Using Docker Compose

```bash
# Clone repository
git clone <repository-url>
cd doctranslator

# Set environment variables
cp .env.example .env
# Edit .env with your OVH credentials

# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

### Using Dockerfile Directly

```bash
# Build image
docker build -f Dockerfile.railway -t doctranslator .

# Run container
docker run -d \
  -p 8080:8080 \
  -e OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token \
  -e OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1 \
  -e USE_OVH_ONLY=true \
  --name doctranslator \
  doctranslator

# Check logs
docker logs -f doctranslator
```

## Local Development

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download Tesseract OCR data (if not installed)
# On Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng

# Set environment variables
export OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token
export USE_OVH_ONLY=true

# Run server
python -m uvicorn app.main:app --reload --port 9122
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Database Setup (Local)

```bash
cd backend

# SQLite auto-configured for local development
# Optionally use PostgreSQL:

# 1. Install PostgreSQL
# 2. Create database
createdb doctranslator

# 3. Set environment variable
export DATABASE_URL=postgresql://localhost/doctranslator

# 4. Initialize database
python app/database/init_db.py

# 5. Seed data
python app/database/unified_seed.py
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OVH_AI_ENDPOINTS_ACCESS_TOKEN` | OVH API authentication token | `sk-...` |
| `USE_OVH_ONLY` | Use OVH cloud API | `true` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OVH_AI_BASE_URL` | OVH API endpoint | `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` |
| `OVH_MAIN_MODEL` | Main processing model | `Meta-Llama-3_3-70B-Instruct` |
| `OVH_PREPROCESSING_MODEL` | Preprocessing model | `Mistral-Nemo-Instruct-2407` |
| `OVH_TRANSLATION_MODEL` | Translation model | `Meta-Llama-3_3-70B-Instruct` |
| `ENVIRONMENT` | Deployment environment | `production` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `DATABASE_URL` | PostgreSQL connection string | Auto-configured |
| `DEBUG` | Enable debug mode | `false` |
| `PADDLEOCR_SERVICE_URL` | PaddleOCR microservice URL | `http://paddleocr-service.railway.internal:9123` |

## Health Monitoring

### Health Check Endpoints

```bash
# Simple health check (nginx)
curl https://your-app.up.railway.app/health

# Backend health check
curl https://your-app.up.railway.app/api/health

# Detailed diagnostics
curl https://your-app.up.railway.app/api/health/detailed

# PaddleOCR microservice health (from within Railway network)
curl http://paddleocr-service.railway.internal:9123/health

# Check available OCR engines
curl https://your-app.up.railway.app/api/pipeline/ocr-engines
```

### Expected Responses

**Healthy:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-02T...",
  "environment": "production",
  "ovh_configured": true
}
```

**Unhealthy:**
```json
{
  "status": "unhealthy",
  "error": "OVH API not configured"
}
```

## Troubleshooting

### Build Failures

**Symptom**: Railway build fails

**Solutions**:
1. Check all files are committed to git
2. Verify branch is `railwaywithovhapi`
3. Check Docker build logs for specific errors
4. Ensure `Dockerfile.railway` exists

### Application Errors

**Symptom**: 500 Internal Server Error

**Solutions**:
1. Check environment variables are set correctly
2. Verify OVH API token is valid
3. Check Railway logs for error details
4. Test OVH API endpoint separately

### Database Connection Issues

**Symptom**: Database connection errors

**Solutions**:
1. Verify PostgreSQL service is running in Railway
2. Check `DATABASE_URL` is set correctly
3. Ensure database user has proper permissions
4. Review database connection logs

### OCR Not Working

**Symptom**: OCR fails on image/scanned PDF

**Solutions**:
1. Check Tesseract is installed in container
2. Verify language data downloaded (deu, eng)
3. Check file is valid image format
4. Review OCR logs for specific errors

### PaddleOCR Service Issues

**Symptom**: PaddleOCR not available or connection errors

**Solutions**:
1. **Verify Service is Running**:
   - Check Railway dashboard for PaddleOCR service status
   - Review PaddleOCR service logs for startup errors
   - Look for `✅ PaddleOCR initialized successfully` in logs

2. **Check Service Configuration**:
   - Verify `PADDLEOCR_SERVICE_URL` in backend environment variables
   - Ensure correct internal URL: `http://paddleocr-service.railway.internal:9123`
   - Check Railway's IPv6 internal networking is working

3. **Debug Connection**:
   - From backend service, test health endpoint: `curl http://paddleocr-service.railway.internal:9123/health`
   - Check for DNS resolution issues in backend logs
   - Verify both services are in the same Railway project

4. **Model Download Issues**:
   - PaddleOCR downloads models on first startup (~300MB)
   - First startup may take 2-3 minutes
   - Check for disk space issues in Railway logs
   - Verify internet connectivity from Railway service

5. **Graceful Degradation**:
   - Backend automatically falls back to hybrid extraction if PaddleOCR unavailable
   - Check `/api/pipeline/ocr-engines` to see PaddleOCR availability status
   - System continues to work with Tesseract and Vision LLM even if PaddleOCR is down

### Performance Issues

**Symptom**: Slow processing times

**Solutions**:
1. Check OVH API rate limits
2. Monitor Railway resource usage
3. Review processing logs for bottlenecks
4. Consider upgrading Railway plan
5. Disable unnecessary pipeline steps

## Security Best Practices

### Production Checklist

- [ ] Use environment variables for secrets (never commit)
- [ ] Enable HTTPS only (automatic on Railway)
- [ ] Set strong PostgreSQL password
- [ ] Configure CORS allowed origins
- [ ] Enable rate limiting
- [ ] Review and minimize logged data
- [ ] Set up automated backups (database)
- [ ] Monitor error logs regularly
- [ ] Keep dependencies updated
- [ ] Use least-privilege database user

### Secrets Management

**Never commit:**
- `.env` files
- API tokens
- Database passwords
- Private keys

**Use:**
- Railway environment variables (encrypted)
- GitHub Secrets for CI/CD
- Vault/secret managers for production

## Backup & Recovery

### Database Backup

```bash
# Using Railway CLI
railway run pg_dump > backup.sql

# Restore
railway run psql < backup.sql
```

### Application State

No application state stored - documents processed in-memory only.

## Monitoring & Alerts

### Railway Dashboard

Monitor:
- CPU/Memory usage
- Request volume
- Error rates
- Build/deploy status

### Custom Monitoring

Set up alerts for:
- Health check failures
- High error rates
- Unusual processing times
- Database connection issues

### Log Analysis

```bash
# Railway CLI
railway logs --tail 100

# Filter errors
railway logs | grep ERROR

# Real-time monitoring
railway logs --tail -f
```

## Scaling

### Vertical Scaling (Railway)
Upgrade plan for more resources:
- More CPU/memory
- Higher request limits
- Better database performance

### Horizontal Scaling
Application is stateless and ready for:
- Multiple Railway instances
- Load balancer distribution
- Database connection pooling

### Cost Optimization

- Use Railway sleep for staging environments
- Monitor OVH token usage
- Implement caching for frequent operations
- Disable unused pipeline steps
- Optimize database queries

## Rollback Procedures

### Railway Rollback

```bash
# Via Railway CLI
railway rollback

# Or in Railway Dashboard
# Deployments → Select previous deployment → Redeploy
```

### Manual Rollback

```bash
# Revert to previous commit
git revert HEAD
git push

# Railway auto-deploys on push
```

## CI/CD with GitHub Actions

### Self-Hosted ARC Runners on Kubernetes

The project uses Actions Runner Controller (ARC) for CI/CD, running on a Kubernetes cluster.

#### Runner Requirements

- **Docker daemon access** - Required for PostgreSQL service containers in backend tests
- **Python 3.11+** - Backend quality checks and tests
- **Node.js 18+** - Frontend quality checks and builds
- **Network access** - For pulling dependencies and Docker images

#### ARC RunnerDeployment Configuration

```yaml
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: arc-runner-set
spec:
  replicas: 2
  template:
    spec:
      repository: your-org/doctranslator
      labels:
        - arc-runner-set
      dockerdWithinRunnerContainer: true
      # OR use host Docker socket:
      volumes:
        - name: docker-sock
          hostPath:
            path: /var/run/docker.sock
      volumeMounts:
        - name: docker-sock
          mountPath: /var/run/docker.sock
```

#### Workflow Jobs

Every push to `dev` or `main` triggers:

1. **Backend Quality Checks** - Ruff linting/formatting, MyPy, Bandit security scan
2. **Backend Tests** - pytest with PostgreSQL container
3. **Frontend Quality Checks** - ESLint, Prettier, TypeScript
4. **Frontend Build** - Production build verification
5. **Security Audit** - pip-audit and npm audit
6. **Quality Gate** - All must pass

#### Troubleshooting CI/CD

**Docker daemon not available:**
```bash
# Verify Docker socket access in runner pod
kubectl exec -it <runner-pod> -- docker ps

# Check ARC runner logs
kubectl logs -l app=arc-runner-set -f
```

**PostgreSQL container fails to start:**
- Ensure runner has privileged container support or Docker socket mounted
- Check runner has sufficient resources (memory, CPU)
- Verify network policies allow container-to-container communication

**Quality checks fail:**
```bash
# Run locally before pushing
cd backend
python -m ruff check app/
python -m ruff format app/ --check
pytest

cd ../frontend
npm run lint
npm run format:check
npm run type-check
npm run build
```

#### Monitoring CI/CD

```bash
# View recent workflow runs
gh run list --limit 10

# Watch current run
gh run watch

# View failed job logs
gh run view <run-id> --log-failed

# Re-run failed jobs
gh run rerun <run-id> --failed
```

## Support Resources

- **Railway**: [Railway Discord](https://discord.gg/railway)
- **OVH AI**: [Documentation](https://endpoints.ai.cloud.ovh.net/docs)
- **GitHub Actions**: [ARC Documentation](https://github.com/actions/actions-runner-controller)
- **Project Issues**: GitHub Issues
- **Logs**: Railway Dashboard, GitHub Actions logs
