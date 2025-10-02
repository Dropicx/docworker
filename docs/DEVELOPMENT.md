# Local Development Quick Start Guide

Get up and running with DocTranslator local development in under 10 minutes.

## Prerequisites

- Python 3.11+ installed
- Node.js 18+ and npm installed
- Git configured
- OVH AI Endpoints access token ([Get one here](https://endpoints.ai.cloud.ovh.net/))
- Railway dev environment with PostgreSQL (see [RAILWAY_DEV_SETUP.md](./RAILWAY_DEV_SETUP.md))

## Quick Start (5 Steps)

### Step 1: Clone and Navigate

```bash
git clone https://github.com/Dropicx/doctranslator.git
cd doctranslator

# Checkout dev branch for development
git checkout dev
```

### Step 2: Configure Environment

```bash
# Copy environment template
cd backend
cp .env.example .env.development

# Edit with your Railway DATABASE_URL and OVH token
nano .env.development  # or use your favorite editor
```

**Required values in `.env.development`:**
```env
DATABASE_URL=postgresql://postgres:xxx@containers-us-west-XX.railway.app:XXXXX/railway
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token-here
```

### Step 3: Setup Backend

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Load environment and start
export $(cat .env.development | xargs)
python -m uvicorn app.main:app --reload --port 9122
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:9122
INFO:     Application startup complete.
```

### Step 4: Setup Frontend (New Terminal)

```bash
cd frontend
npm install
npm run dev
```

**Expected output:**
```
VITE v6.0.6  ready in XXX ms
➜  Local:   http://localhost:5173/
```

### Step 5: Test It Works

Open http://localhost:5173 in your browser.

You should see the DocTranslator interface. Try:
1. Upload a test PDF
2. Select document type
3. Process document
4. View results

## Branch Structure

### Development Workflow

```
dev branch (development)    →    Railway dev environment
    ↓ (when stable)
main branch (production)    →    Railway production environment
```

**Important:**
- ✅ Do all development on `dev` branch
- ✅ Test thoroughly in Railway dev environment
- ✅ Merge to `main` when ready for production
- ✅ Railway auto-deploys on push to respective branches

### Working on Features

```bash
# Start from dev branch
git checkout dev
git pull origin dev

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "Add: your feature description"

# Push to GitHub
git push origin feature/your-feature-name

# Create Pull Request to dev branch (not main!)
```

## Project Structure

```
doctranslator/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Business logic
│   │   ├── database/       # DB models & connection
│   │   └── main.py         # App entry point
│   ├── requirements.txt    # Python dependencies
│   ├── .env.development    # Your local config (gitignored)
│   └── .env.example        # Template
├── frontend/               # React + TypeScript
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── services/      # API clients
│   │   └── App.tsx        # Main app
│   └── package.json       # Node dependencies
├── docs/                  # All documentation
├── railway/               # Railway deployment scripts
└── README.md             # Project overview
```

## Common Development Tasks

### Run Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Check Code Quality

```bash
# Python linting
cd backend
flake8 app/

# TypeScript checking
cd frontend
npm run build  # Checks types during build
```

### Database Operations

```bash
# View current prompts
curl http://localhost:9122/api/settings/universal-prompts | jq

# Reset database (re-run init)
python backend/app/database/init_db.py drop
python backend/app/database/init_db.py
```

### Update Dependencies

```bash
# Backend
cd backend
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt

# Frontend
cd frontend
npm update
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `DATABASE_URL` | Railway PostgreSQL connection | Railway Dashboard → PostgreSQL → Connect → Public URL |
| `OVH_AI_ENDPOINTS_ACCESS_TOKEN` | OVH API authentication | https://endpoints.ai.cloud.ovh.net/ |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OVH_AI_BASE_URL` | https://oai.endpoints.kepler.ai.cloud.ovh.net/v1 | OVH API endpoint |
| `USE_OVH_ONLY` | true | Use OVH exclusively (no local AI) |
| `ENVIRONMENT` | development | Environment name |
| `LOG_LEVEL` | DEBUG | Logging verbosity |
| `OVH_MAIN_MODEL` | Meta-Llama-3_3-70B-Instruct | Main AI model |
| `OVH_PREPROCESSING_MODEL` | Mistral-Nemo-Instruct-2407 | Preprocessing model |

## Development Workflow

### Daily Routine

```bash
# Morning: Start development servers
cd backend
source venv/bin/activate
export $(cat .env.development | xargs)
python -m uvicorn app.main:app --reload --port 9122 &

cd ../frontend
npm run dev &

# Work on features...

# Evening: Commit and push
git add .
git commit -m "Update: what you changed"
git push origin dev
```

### Testing Changes

1. **Backend changes:** Auto-reloads (--reload flag)
2. **Frontend changes:** Auto-reloads (Vite HMR)
3. **Database changes:** Need manual re-init
4. **Environment changes:** Restart backend

### Debugging

**Backend debugging:**
```bash
# Increase log verbosity
export LOG_LEVEL=DEBUG

# View SQL queries
# Edit backend/app/database/connection.py:
# Set echo=True in create_engine()

# Use Python debugger
import pdb; pdb.set_trace()
```

**Frontend debugging:**
- Open browser DevTools (F12)
- Check Console tab for errors
- Check Network tab for API calls
- Use React DevTools extension

## Common Issues

### Backend won't start

**Problem:** `ModuleNotFoundError` or import errors

**Solution:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$PWD
```

### Database connection fails

**Problem:** Can't connect to Railway PostgreSQL

**Solution:**
```bash
# Test connection
psql "$DATABASE_URL" -c "SELECT 1;"

# Verify environment loaded
echo $DATABASE_URL

# Re-export if needed
export $(cat .env.development | xargs)
```

### Frontend API calls fail

**Problem:** 404 or CORS errors

**Solution:**
```bash
# Verify backend is running
curl http://localhost:9122/api/health

# Check frontend proxy config
cat frontend/vite.config.ts | grep proxy
```

### OVH API errors

**Problem:** "API token not configured" or 401 errors

**Solution:**
```bash
# Verify token is set
echo $OVH_AI_ENDPOINTS_ACCESS_TOKEN

# Test token directly
curl https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/models \
  -H "Authorization: Bearer $OVH_AI_ENDPOINTS_ACCESS_TOKEN"
```

## Best Practices

### Code Style

- **Python:** Follow PEP 8, use type hints
- **TypeScript:** Use strict mode, define interfaces
- **Commits:** Use conventional commits (feat:, fix:, docs:)
- **Documentation:** Update docs when changing features

### Security

- ✅ Never commit `.env.*` files
- ✅ Use environment variables for secrets
- ✅ Keep dependencies updated
- ✅ Review security advisories
- ❌ Never hardcode API keys
- ❌ Never log sensitive data

### Performance

- Use async/await for I/O operations
- Implement caching where appropriate
- Monitor database query performance
- Optimize frontend bundle size

## Next Steps

After local setup:

1. ✅ Read [RAILWAY_DEV_SETUP.md](./RAILWAY_DEV_SETUP.md) for Railway configuration
2. ✅ Review [ARCHITECTURE.md](./ARCHITECTURE.md) to understand system design
3. ✅ Check [API.md](./API.md) for API documentation
4. ✅ See [DATABASE.md](./DATABASE.md) for database schema
5. ✅ Follow [DEPLOYMENT.md](./DEPLOYMENT.md) when ready to deploy

## Getting Help

- **Documentation:** Check `/docs` folder
- **Issues:** Create GitHub issue
- **Railway:** [Railway Discord](https://discord.gg/railway)
- **OVH:** [OVH AI Endpoints Docs](https://endpoints.ai.cloud.ovh.net/docs)

## Quick Reference Commands

```bash
# Backend
cd backend && source venv/bin/activate
export $(cat .env.development | xargs)
python -m uvicorn app.main:app --reload --port 9122

# Frontend
cd frontend && npm run dev

# Tests
pytest                    # Backend
npm test                  # Frontend

# Database
python app/database/init_db.py        # Initialize
python app/database/init_db.py drop   # Reset

# Git
git checkout dev          # Switch to dev branch
git pull origin dev       # Get latest changes
git push origin dev       # Push your changes
```

---

**Happy coding! 🚀**
