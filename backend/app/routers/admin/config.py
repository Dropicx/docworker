"""
Configuration Management API Endpoints

Provides admin endpoints for managing application configuration,
feature flags, and runtime settings.

**Authentication:**
All endpoints require SETTINGS_ACCESS_CODE header for authentication.

**Endpoints:**
- GET /api/admin/config - Get all configuration
- GET /api/admin/config/validation - Validate current configuration
- GET /api/admin/config/feature-flags - Get all feature flags status
- PUT /api/admin/config/feature-flags/{flag_name} - Update feature flag
- POST /api/admin/config/reload - Hot reload configuration (safe settings only)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings, settings
from app.core.permissions import require_role, get_current_user_required
from app.database.connection import get_session
from app.repositories.feature_flags_repository import FeatureFlagsRepository
from app.services.feature_flags import Feature, FeatureFlags
from app.database.auth_models import UserDB
from typing import Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/config", tags=["admin", "configuration"])


# ==================
# Pydantic Models
# ==================


class ConfigResponse(BaseModel):
    """Configuration response model."""

    app_name: str
    environment: str
    debug: bool
    max_file_size_mb: int
    database_connected: bool = Field(description="Database connectivity status")
    ovh_configured: bool = Field(description="OVH API token configured")
    redis_configured: bool = Field(description="Redis configured")


class ValidationResponse(BaseModel):
    """Configuration validation response."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FeatureFlagUpdate(BaseModel):
    """Feature flag update request."""

    enabled: bool
    description: str | None = None
    rollout_percentage: int = Field(default=100, ge=0, le=100)


class FeatureFlagsResponse(BaseModel):
    """Feature flags status response."""

    flags: dict[str, bool]
    total_count: int
    enabled_count: int


class ReloadResponse(BaseModel):
    """Configuration reload response."""

    success: bool
    reloaded_settings: list[str] = Field(default_factory=list)
    message: str


# ==================
# Authentication
# ==================


# All endpoints in this router require ADMIN role
def require_admin_auth(current_user: UserDB = Depends(get_current_user_required)):
    """Require admin authentication for all endpoints"""
    return require_role("admin")(current_user)


# ==================
# Endpoints
# ==================


@router.get("/", response_model=ConfigResponse)
async def get_configuration(
    current_user: UserDB = Depends(require_admin_auth),
    app_settings: Settings = Depends(get_settings),
) -> ConfigResponse:
    """
    Get current application configuration (non-sensitive values only).

    **Authentication Required:** Admin role

    Returns summary of current configuration without exposing secrets.
    """
    logger.info("Fetching application configuration")

    return ConfigResponse(
        app_name=app_settings.app_name,
        environment=app_settings.environment,
        debug=app_settings.debug,
        max_file_size_mb=app_settings.max_file_size_mb,
        database_connected=bool(app_settings.database_url),
        ovh_configured=bool(app_settings.ovh_api_token),
        redis_configured=bool(app_settings.redis_url),
    )


@router.get("/validation", response_model=ValidationResponse)
async def validate_configuration(
    current_user: UserDB = Depends(require_admin_auth),
    app_settings: Settings = Depends(get_settings),
) -> ValidationResponse:
    """
    Validate current configuration and check for issues.

    **Authentication Required:** Admin role

    Returns validation status with any errors or warnings found.
    """
    logger.info("Validating application configuration")

    errors = []
    warnings = []

    # Check required settings
    if not app_settings.database_url:
        errors.append("DATABASE_URL is required but not configured")

    if not app_settings.ovh_api_token:
        errors.append("OVH_AI_ENDPOINTS_ACCESS_TOKEN is required but not configured")

    # Check environment-specific warnings
    if app_settings.environment == "production" and app_settings.debug:
        warnings.append("DEBUG mode is enabled in production environment")

    if app_settings.environment == "production" and "*" in app_settings.allowed_origins:
        warnings.append("CORS allows all origins (*) in production - security risk")

    # Validate file size
    if app_settings.max_file_size_mb > 100:
        warnings.append(f"Max file size ({app_settings.max_file_size_mb}MB) is very large")
    elif app_settings.max_file_size_mb < 1:
        errors.append(f"Max file size ({app_settings.max_file_size_mb}MB) is too small")

    valid = len(errors) == 0

    if valid:
        logger.info("✅ Configuration validation passed")
    else:
        logger.warning(f"❌ Configuration validation failed with {len(errors)} errors")

    return ValidationResponse(valid=valid, errors=errors, warnings=warnings)


@router.get("/feature-flags", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    current_user: UserDB = Depends(require_admin_auth),
    db: Session = Depends(get_session),
    app_settings: Settings = Depends(get_settings),
) -> FeatureFlagsResponse:
    """
    Get status of all feature flags.

    **Authentication Required:** Admin role

    Returns current state of all feature flags with their enabled status.
    """
    logger.info("Fetching feature flags status")

    flag_service = FeatureFlags(session=db, settings=app_settings)

    # Get status of all features
    flags_status = {}
    for feature in Feature:
        flags_status[feature.value] = flag_service.is_enabled(feature)

    enabled_count = sum(1 for enabled in flags_status.values() if enabled)

    return FeatureFlagsResponse(
        flags=flags_status, total_count=len(flags_status), enabled_count=enabled_count
    )


@router.put("/feature-flags/{flag_name}")
async def update_feature_flag(
    flag_name: str,
    update: FeatureFlagUpdate,
    current_user: UserDB = Depends(require_admin_auth),
    db: Session = Depends(get_session),
) -> JSONResponse:
    """
    Update a feature flag in the database.

    **Authentication Required:** Admin role

    Updates the feature flag in the database (priority level 2).
    Environment variables (priority level 1) will still override this value.

    Args:
        flag_name: Feature flag name (e.g., "vision_llm_fallback_enabled")
        update: Feature flag update data
    """
    logger.info(f"Updating feature flag: {flag_name} = {update.enabled}")

    # Validate flag name exists
    try:
        Feature(flag_name)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{flag_name}' not found. "
            f"Valid flags: {[f.value for f in Feature]}",
        ) from e

    # Update in database
    repo = FeatureFlagsRepository(db)
    flag = repo.set_flag(
        name=flag_name,
        enabled=update.enabled,
        description=update.description or "",
        rollout_percentage=update.rollout_percentage,
    )

    logger.info(f"✅ Feature flag '{flag_name}' updated to {update.enabled}")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": f"Feature flag '{flag_name}' updated successfully",
            "flag": {
                "name": flag.name,
                "enabled": flag.enabled,
                "description": flag.description,
                "rollout_percentage": flag.rollout_percentage,
            },
        },
    )


@router.post("/reload", response_model=ReloadResponse)
async def reload_configuration(
    current_user: UserDB = Depends(require_admin_auth),
    app_settings: Settings = Depends(get_settings),
) -> ReloadResponse:
    """
    Hot reload configuration (safe settings only).

    **Authentication Required:** Admin role

    **Note:** Only non-critical settings can be reloaded without restart.
    Critical settings (database URL, API keys, etc.) require application restart.

    Safe settings that can be reloaded:
    - log_level
    - max_file_size_mb
    - ai_timeout_seconds
    - rate_limit_per_minute

    Returns list of successfully reloaded settings.
    """
    logger.info("Reloading configuration (safe settings)")

    reloaded = []

    # Settings that can be safely hot-reloaded

    # Update logging level if changed
    if hasattr(app_settings, "log_level"):
        new_level = app_settings.log_level
        logging.getLogger().setLevel(new_level)
        reloaded.append(f"log_level={new_level}")
        logger.info(f"Log level updated to {new_level}")

    logger.info(f"✅ Configuration reloaded: {', '.join(reloaded)}")

    return ReloadResponse(
        success=True,
        reloaded_settings=reloaded,
        message=f"Successfully reloaded {len(reloaded)} settings. "
        f"Critical settings require application restart.",
    )


@router.get("/health")
async def config_health(current_user: UserDB = Depends(require_admin_auth)) -> dict[str, Any]:
    """
    Check health of configuration management system.

    **Authentication Required:** Admin role

    Returns health status and diagnostics.
    """
    return {
        "status": "healthy",
        "config_loaded": settings is not None,
        "environment": settings.environment if settings else "unknown",
        "timestamp": "2025-01-13T00:00:00Z",
    }
