#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Load environment variables from .env.development (skip comments and empty lines)
set -a
source <(grep -v '^#' .env.development | grep -v '^$')
set +a

# Start uvicorn
python -m uvicorn app.main:app --reload --port 9122
