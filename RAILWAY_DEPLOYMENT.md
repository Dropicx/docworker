# Railway Deployment Guide for DocTranslator

This guide explains how to deploy the DocTranslator application to Railway.app using OVH AI Endpoints for all AI processing.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **OVH AI Endpoints Access**: Get your API token from [OVH AI Endpoints](https://endpoints.ai.cloud.ovh.net/)
3. **GitHub Repository**: This code should be in a GitHub repository

## Deployment Steps

### 1. Connect GitHub Repository

1. Log in to Railway Dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository and select the `railwaywithovhapi` branch

### 2. Configure Environment Variables

In the Railway dashboard, add these environment variables:

```env
# Required Environment Variables
ENVIRONMENT=production
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-ovh-token-here
OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
OVH_MAIN_MODEL=Meta-Llama-3_3-70B-Instruct
OVH_PREPROCESSING_MODEL=Mistral-Nemo-Instruct-2407
OVH_TRANSLATION_MODEL=Meta-Llama-3_3-70B-Instruct
USE_OVH_ONLY=true
LOG_LEVEL=INFO
```

### 3. Deploy Configuration

Railway will automatically detect the `railway.json` configuration and use the custom Dockerfile (`Dockerfile.railway`).

The deployment includes:
- **Backend API**: Python FastAPI server on port 9122 (internal)
- **Frontend**: React application served by nginx
- **Reverse Proxy**: nginx routing `/api` to backend and `/` to frontend
- **Health Checks**: Automatic health monitoring at `/health`

### 4. Domain Setup

Railway will provide you with a domain like:
```
your-app.up.railway.app
```

You can also configure a custom domain in the Railway settings.

## Architecture

```
Internet
    ↓
Railway Load Balancer (PORT 8080)
    ↓
nginx (Port 8080)
    ├── / → React Frontend (static files)
    └── /api → FastAPI Backend (Port 9122)
           ↓
      OVH AI Endpoints
```

## Features

- **No GPU Required**: All AI processing happens on OVH cloud
- **Auto-scaling**: Railway handles scaling automatically
- **SSL/TLS**: Railway provides automatic HTTPS
- **Health Monitoring**: Built-in health checks for reliability
- **Zero-downtime Deploys**: Railway supports rolling deployments

## Environment Variables Reference

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `ENVIRONMENT` | Yes | Deployment environment | production |
| `OVH_AI_ENDPOINTS_ACCESS_TOKEN` | Yes | Your OVH API token | - |
| `OVH_AI_BASE_URL` | No | OVH API endpoint | https://oai.endpoints.kepler.ai.cloud.ovh.net/v1 |
| `OVH_MAIN_MODEL` | No | Main processing model | Meta-Llama-3_3-70B-Instruct |
| `OVH_PREPROCESSING_MODEL` | No | Preprocessing model | Mistral-Nemo-Instruct-2407 |
| `OVH_TRANSLATION_MODEL` | No | Translation model | Meta-Llama-3_3-70B-Instruct |
| `USE_OVH_ONLY` | No | Use only OVH (no Ollama) | true |
| `LOG_LEVEL` | No | Logging level | INFO |

## Monitoring

### Health Endpoints

- `/health` - Simple health check
- `/api/health` - Backend health status
- `/api/health/detailed` - Detailed system information

### Logs

View logs in Railway dashboard:
```bash
railway logs
```

Or use Railway CLI:
```bash
npm install -g @railway/cli
railway login
railway logs --tail
```

## Troubleshooting

### Build Fails

1. Check that all files are committed to git
2. Verify the branch is `railwaywithovhapi`
3. Check Railway build logs for specific errors

### Application Errors

1. Check environment variables are set correctly
2. Verify OVH API token is valid
3. Check application logs in Railway dashboard

### Performance Issues

1. Railway automatically scales, but you can upgrade your plan for more resources
2. OVH API has rate limits - check their documentation
3. Consider implementing caching for frequently processed documents

## Cost Optimization

- **Railway**: Uses usage-based pricing, scales to zero when not in use
- **OVH AI Endpoints**: Pay-per-token pricing
- **Tips**:
  - Use Railway's sleep feature for staging environments
  - Monitor token usage in OVH dashboard
  - Implement result caching to reduce API calls

## Security

- All environment variables are encrypted in Railway
- HTTPS is enforced by default
- No medical data is stored permanently
- All processing happens in memory
- Temporary files are automatically cleaned up

## Support

- **Railway Support**: [Railway Discord](https://discord.gg/railway)
- **OVH Support**: [OVH AI Endpoints Documentation](https://endpoints.ai.cloud.ovh.net/docs)
- **Application Issues**: Check the logs and this documentation

## Next Steps

After deployment:
1. Test the health endpoint: `https://your-app.up.railway.app/health`
2. Upload a test document through the web interface
3. Monitor logs and metrics in Railway dashboard
4. Set up alerts for errors or high usage