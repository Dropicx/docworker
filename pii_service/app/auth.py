"""
API Key Authentication for PII Service

Simple API key authentication using X-API-Key header.
If API_SECRET_KEY is not set, authentication is disabled (for local development).
"""

import os
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# Get API key from environment
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")

# Header-based API key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> None:
    """
    Verify API key from X-API-Key header.

    - If API_SECRET_KEY is not set (empty), authentication is disabled.
    - If API_SECRET_KEY is set, the provided key must match.
    """
    # Skip authentication if no API key is configured
    if not API_SECRET_KEY:
        return

    # Require API key if configured
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    if api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
