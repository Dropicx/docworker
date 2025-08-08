#!/bin/bash

# Railway Deployment Script for DocTranslator
# This script prepares and pushes the railwaywithovhapi branch for deployment

echo "🚀 Preparing Railway deployment..."

# Ensure we're on the right branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "railwaywithovhapi" ]; then
    echo "⚠️  Switching to railwaywithovhapi branch..."
    git checkout railwaywithovhapi
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 Uncommitted changes detected. Committing..."
    git add .
    git commit -m "Update for Railway deployment - $(date +%Y-%m-%d)"
fi

# Push to origin
echo "📤 Pushing to GitHub..."
git push origin railwaywithovhapi

echo "✅ Deployment preparation complete!"
echo ""
echo "Next steps:"
echo "1. Go to your Railway dashboard"
echo "2. The deployment should start automatically"
echo "3. Check the build logs for any issues"
echo "4. Once deployed, configure environment variables:"
echo "   - OVH_AI_ENDPOINTS_ACCESS_TOKEN"
echo "   - Other variables as listed in RAILWAY_DEPLOYMENT.md"
echo ""
echo "🌐 Your app will be available at: https://[your-app].up.railway.app"