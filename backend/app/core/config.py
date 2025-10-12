"""
Centralized configuration management for DocTranslator.

All application settings, environment variables, and configuration options
are defined here using Pydantic for type safety and validation.
"""

import os
import logging
from typing import List, Optional
from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings with type-safe configuration.

    All settings are loaded from environment variables with sensible defaults.
    Required settings will raise an error if not provided.
    """

    # ==================
    # Application Settings
    # ==================
    app_name: str = Field(default="DocTranslator", description="Application name")
    environment: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    port: int = Field(default=9122, description="Server port")

    # ==================
    # Database Settings
    # ==================
    database_url: str = Field(
        ...,  # Required
        description="PostgreSQL connection string"
    )
    db_pool_size: int = Field(
        default=20,
        description="Database connection pool size"
    )
    db_max_overflow: int = Field(
        default=40,
        description="Maximum overflow connections"
    )
    db_pool_timeout: int = Field(
        default=30,
        description="Connection pool timeout in seconds"
    )

    # ==================
    # Redis Settings (for Celery)
    # ==================
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection string for Celery"
    )
    redis_max_connections: int = Field(
        default=50,
        description="Maximum Redis connections"
    )

    # ==================
    # OVH AI Endpoints
    # ==================
    ovh_ai_endpoints_access_token: SecretStr = Field(
        ...,  # Required
        description="OVH AI Endpoints access token"
    )
    ovh_ai_base_url: str = Field(
        default="https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
        description="OVH AI base URL"
    )
    ovh_main_model: str = Field(
        default="Meta-Llama-3_3-70B-Instruct",
        description="Main LLM model for processing"
    )
    ovh_preprocessing_model: str = Field(
        default="Mistral-Nemo-Instruct-2407",
        description="Fast model for preprocessing tasks"
    )
    ovh_translation_model: str = Field(
        default="Meta-Llama-3_3-70B-Instruct",
        description="Model for translation tasks"
    )
    ovh_vision_model: str = Field(
        default="Qwen2.5-VL-72B-Instruct",
        description="Vision model for OCR tasks"
    )
    ovh_vision_base_url: str = Field(
        default="https://qwen-2-5-vl-72b-instruct.endpoints.kepler.ai.cloud.ovh.net",
        description="OVH Vision model base URL"
    )
    use_ovh_only: bool = Field(
        default=True,
        description="Use only OVH AI endpoints (disable fallbacks)"
    )

    # ==================
    # Security Settings
    # ==================
    secret_key: Optional[SecretStr] = Field(
        default=None,
        description="Secret key for session encryption"
    )
    admin_access_code: str = Field(
        default="admin123",
        description="Access code for settings UI",
        validation_alias="SETTINGS_ACCESS_CODE"  # Keep backward compatibility with Railway env var
    )
    allowed_origins: List[str] = Field(
        default_factory=lambda: ["*"],
        description="CORS allowed origins"
    )
    trusted_hosts: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Trusted host headers"
    )

    # ==================
    # File Processing Settings
    # ==================
    max_file_size_mb: int = Field(
        default=50,
        description="Maximum upload file size in MB"
    )
    allowed_file_types: List[str] = Field(
        default_factory=lambda: [".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png"],
        description="Allowed file extensions"
    )
    temp_dir: str = Field(
        default="/tmp",
        description="Temporary file storage directory"
    )

    # ==================
    # Feature Flags
    # ==================
    enable_ocr: bool = Field(
        default=True,
        description="Enable OCR text extraction"
    )
    enable_privacy_filter: bool = Field(
        default=True,
        description="Enable PII privacy filtering"
    )
    enable_multi_file: bool = Field(
        default=True,
        description="Enable multi-file processing"
    )

    # ==================
    # AI Processing Settings
    # ==================
    ai_timeout_seconds: int = Field(
        default=300,
        description="AI request timeout in seconds"
    )
    ai_max_retries: int = Field(
        default=3,
        description="Maximum AI request retries"
    )
    ai_request_delay_ms: int = Field(
        default=100,
        description="Delay between AI requests in milliseconds"
    )

    # ==================
    # Logging Settings
    # ==================
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    log_format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        description="Log message format"
    )

    # ==================
    # Railway Settings
    # ==================
    railway_environment: Optional[str] = Field(
        default=None,
        description="Railway environment name"
    )
    railway_project_id: Optional[str] = Field(
        default=None,
        description="Railway project ID"
    )

    # ==================
    # Rate Limiting
    # ==================
    rate_limit_per_minute: int = Field(
        default=60,
        description="API rate limit per minute"
    )

    # ==================
    # Pydantic Configuration
    # ==================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables
    )

    # ==================
    # Validators
    # ==================

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of the allowed values."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            logger.warning(
                f"Invalid environment '{v}', must be one of {allowed}. "
                f"Defaulting to 'development'."
            )
            return "development"
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v:
            raise ValueError("DATABASE_URL is required")
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string "
                "(postgresql:// or postgres://)"
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            logger.warning(
                f"Invalid log level '{v}', must be one of {allowed}. "
                f"Defaulting to 'INFO'."
            )
            return "INFO"
        return v_upper

    @field_validator("max_file_size_mb")
    @classmethod
    def validate_max_file_size(cls, v: int) -> int:
        """Validate max file size is reasonable."""
        if v < 1 or v > 100:
            raise ValueError("max_file_size_mb must be between 1 and 100 MB")
        return v

    # ==================
    # Computed Properties
    # ==================

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    @property
    def ovh_api_token(self) -> str:
        """Get OVH API token as plain string."""
        return self.ovh_ai_endpoints_access_token.get_secret_value()

    def validate_on_startup(self) -> bool:
        """
        Validate configuration on application startup.

        Returns:
            True if all validations pass, raises exception otherwise.
        """
        logger.info("🔍 Validating application configuration...")

        # Check OVH token is set
        if not self.ovh_api_token:
            raise ValueError(
                "OVH_AI_ENDPOINTS_ACCESS_TOKEN is required. "
                "Please set it in your environment or .env file."
            )

        logger.info(f"✅ Environment: {self.environment}")
        logger.info(f"✅ Database: {self.database_url.split('@')[-1]}")  # Hide credentials
        logger.info(f"✅ OVH API Token: {'*' * 20} (configured)")
        logger.info(f"✅ Main Model: {self.ovh_main_model}")
        logger.info(f"✅ Max File Size: {self.max_file_size_mb} MB")
        logger.info(f"✅ OCR Enabled: {self.enable_ocr}")
        logger.info(f"✅ Privacy Filter Enabled: {self.enable_privacy_filter}")

        logger.info("✅ Configuration validation passed")
        return True


# ==================
# Global Settings Instance
# ==================

# Create a single global instance
# This will be imported throughout the application
try:
    settings = Settings()
    logger.info("✅ Settings loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load settings: {e}")
    raise


# ==================
# Helper Functions
# ==================

def get_settings() -> Settings:
    """
    Dependency injection helper for FastAPI.

    Usage in routers:
        @app.get("/endpoint")
        async def endpoint(settings: Settings = Depends(get_settings)):
            return settings.app_name
    """
    return settings
