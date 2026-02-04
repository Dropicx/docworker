"""
Centralized configuration management for DocTranslator.

All application settings, environment variables, and configuration options
are defined here using Pydantic for type safety and validation.
"""

import logging
import os

from pydantic import Field, SecretStr, field_validator
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
        default="development", description="Environment: development, staging, production"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    port: int = Field(default=9122, description="Server port")

    # ==================
    # Database Settings
    # ==================
    database_url: str = Field(
        ...,  # Required
        description="PostgreSQL connection string",
    )
    db_pool_size: int = Field(default=20, description="Database connection pool size")
    db_max_overflow: int = Field(default=40, description="Maximum overflow connections")
    db_pool_timeout: int = Field(default=30, description="Connection pool timeout in seconds")

    # ==================
    # Redis Settings (for Celery)
    # ==================
    redis_url: str | None = Field(default=None, description="Redis connection string for Celery")
    redis_max_connections: int = Field(default=50, description="Maximum Redis connections")

    # ==================
    # Cache Settings
    # ==================
    cache_enabled: bool = Field(
        default=True, description="Enable Redis caching for configuration data"
    )
    cache_default_ttl_seconds: int = Field(
        default=300, description="Default cache TTL in seconds (5 minutes)"
    )
    cache_pipeline_ttl_seconds: int = Field(
        default=600, description="Pipeline/model config cache TTL in seconds (10 minutes)"
    )
    cache_key_prefix: str = Field(default="doctranslator", description="Redis cache key prefix")

    # ==================
    # OVH AI Endpoints
    # ==================
    ovh_ai_endpoints_access_token: SecretStr = Field(
        ...,  # Required
        description="OVH AI Endpoints access token",
    )
    ovh_ai_base_url: str = Field(
        default="https://oai.endpoints.kepler.ai.cloud.ovh.net/v1", description="OVH AI base URL"
    )
    ovh_main_model: str = Field(
        default="Meta-Llama-3_3-70B-Instruct", description="Main LLM model for processing"
    )
    ovh_preprocessing_model: str = Field(
        default="Mistral-Nemo-Instruct-2407", description="Fast model for preprocessing tasks"
    )
    ovh_translation_model: str = Field(
        default="Meta-Llama-3_3-70B-Instruct", description="Model for translation tasks"
    )
    use_ovh_only: bool = Field(
        default=True, description="Use only OVH AI endpoints (disable fallbacks)"
    )

    # ==================
    # Security Settings
    # ==================
    secret_key: SecretStr | None = Field(
        default=None, description="Secret key for session encryption"
    )
    admin_access_code: str = Field(
        default="admin123",
        description="Access code for settings UI",
        validation_alias="SETTINGS_ACCESS_CODE",  # Keep backward compatibility with Railway env var
    )
    allowed_origins: str | list[str] | None = Field(
        default=None, description="CORS allowed origins (comma-separated string or list)"
    )
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["*"], description="Trusted host headers"
    )
    csrf_header_name: str = Field(default="X-Requested-With")
    csrf_header_value: str = Field(default="XMLHttpRequest")
    csrf_protection_enabled: bool = Field(default=True)
    csrf_exempt_paths: list[str] = Field(
        default_factory=lambda: ["/api/feedback/cleanup/", "/api/feedback/clear/"]
    )

    # ==================
    # JWT Configuration
    # ==================
    jwt_secret_key: SecretStr = Field(
        ...,  # Required
        description="Secret key for JWT signing",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=15, description="Access token expiration in minutes"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )

    # ==================
    # API Key Configuration
    # ==================
    api_key_length: int = Field(default=32, description="Length of generated API keys")
    api_key_default_expiry_days: int = Field(
        default=90, description="Default API key expiration in days"
    )

    # ==================
    # Password Security
    # ==================
    bcrypt_rounds: int = Field(default=12, ge=10, le=14, description="Bcrypt cost factor (10-14)")
    password_min_length: int = Field(default=8, ge=8, description="Minimum password length")

    # ==================
    # Account Lockout (Brute Force Prevention)
    # ==================
    max_login_attempts: int = Field(
        default=5, ge=3, le=10, description="Maximum failed login attempts before lockout"
    )
    account_lockout_minutes: int = Field(
        default=15, ge=5, le=60, description="Account lockout duration in minutes"
    )

    # ==================
    # Audit Logging
    # ==================
    enable_audit_logging: bool = Field(
        default=True, description="Enable audit logging for security events"
    )
    audit_admin_actions_only: bool = Field(
        default=True, description="Only log admin/user actions (not public uploads)"
    )

    # ==================
    # Public Access Configuration
    # ==================
    allow_public_upload: bool = Field(
        default=True, description="Allow public document uploads without authentication"
    )
    require_auth_for_results: bool = Field(
        default=False, description="Require authentication to view processing results"
    )

    # ==================
    # CORS Configuration
    # ==================
    cors_allow_credentials: bool = Field(
        default=True, description="Allow credentials in CORS requests"
    )
    cors_max_age: int = Field(default=3600, description="CORS preflight cache duration in seconds")

    # ==================
    # File Processing Settings
    # ==================
    max_file_size_mb: int = Field(default=50, description="Maximum upload file size in MB")
    allowed_file_types: list[str] = Field(
        default_factory=lambda: [".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png"],
        description="Allowed file extensions",
    )
    temp_dir: str = Field(
        default=os.getenv("TEMP_DIR", "/tmp"),  # nosec
        description="Temporary file storage directory",
    )

    # ==================
    # Feature Flags
    # ==================
    enable_ocr: bool = Field(default=True, description="Enable OCR text extraction")
    enable_privacy_filter: bool = Field(default=True, description="Enable PII privacy filtering")
    enable_multi_file: bool = Field(default=True, description="Enable multi-file processing")

    # ==================
    # AI Processing Settings
    # ==================
    ai_timeout_seconds: int = Field(default=300, description="AI request timeout in seconds")
    ai_max_retries: int = Field(default=3, description="Maximum AI request retries")
    ai_request_delay_ms: int = Field(
        default=100, description="Delay between AI requests in milliseconds"
    )

    # ==================
    # Logging Settings
    # ==================
    log_level: str = Field(
        default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    log_format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        description="Log message format",
    )

    # ==================
    # Railway Settings
    # ==================
    railway_environment: str | None = Field(default=None, description="Railway environment name")
    railway_project_id: str | None = Field(default=None, description="Railway project ID")

    # ==================
    # Rate Limiting
    # ==================
    rate_limit_per_minute: int = Field(default=60, description="API rate limit per minute")

    # ==================
    # Chat Rate Limiting
    # ==================
    chat_rate_limit_enabled: bool = Field(
        default=True, description="Enable rate limiting for chat endpoints"
    )
    chat_rate_limit_per_minute: int = Field(
        default=10, description="Chat messages allowed per minute"
    )
    chat_rate_limit_per_hour: int = Field(default=50, description="Chat messages allowed per hour")
    chat_rate_limit_per_day: int = Field(default=200, description="Chat messages allowed per day")
    chat_apps_rate_limit: str = Field(
        default="20/minute", description="Rate limit for /chat/apps endpoint"
    )
    chat_health_rate_limit: str = Field(
        default="30/minute", description="Rate limit for /chat/health endpoint"
    )

    # ==================
    # Pydantic Configuration
    # ==================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
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
                f"Invalid environment '{v}', must be one of {allowed}. Defaulting to 'development'."
            )
            return "development"
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v:
            raise ValueError("DATABASE_URL is required")

        # Allow SQLite for testing/development environments
        if v.startswith("sqlite://"):
            env = os.getenv("ENVIRONMENT", "development")
            if env in ["development", "testing", "test"]:
                logger.info(f"✅ Allowing SQLite DATABASE_URL in {env} environment")
                return v
            raise ValueError(
                "SQLite DATABASE_URL is only allowed in development/testing environments"
            )

        # Production must use PostgreSQL
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string (postgresql:// or postgres://) "
                "or SQLite (sqlite://) for development/testing"
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
                f"Invalid log level '{v}', must be one of {allowed}. Defaulting to 'INFO'."
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

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v) -> list[str]:
        """
        Parse CORS allowed origins from environment variable.

        Handles comma-separated strings, empty values, and lists gracefully.
        Always returns a list of strings.
        """
        # Default origins for development
        default_origins = [
            "http://localhost:5173",
            "http://localhost:9122",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:9122",
        ]

        # If it's already a list, return it
        if isinstance(v, list):
            return v if v else default_origins

        # Handle None or empty string - return default
        if v is None or v == "" or v == "null":
            return default_origins

        # If it's a string, split by comma
        if isinstance(v, str):
            # Remove any quotes that might have been added
            v = v.strip().strip('"').strip("'")

            # Split and strip whitespace
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
            return origins if origins else default_origins

        # Fallback to default
        return default_origins

    @field_validator("allowed_origins")
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        """
        Validate CORS allowed origins.

        In production, wildcard "*" is not allowed for security reasons.
        """
        env = os.getenv("ENVIRONMENT", "development")

        if env == "production":
            if "*" in v:
                raise ValueError(
                    "CORS wildcard '*' is not allowed in production environment. "
                    "Please specify explicit origins in ALLOWED_ORIGINS environment variable. "
                    "Example: ALLOWED_ORIGINS='https://healthlingo.de,https://app.healthlingo.de'"
                )
            logger.info(f"✅ Production CORS origins validated: {v}")
        else:
            if "*" in v:
                logger.warning(
                    f"⚠️ CORS wildcard '*' detected in {env} environment. "
                    "This is acceptable for development but must be changed for production."
                )

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
settings: Settings
try:
    settings = Settings()
    logger.info("✅ Settings loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load settings: {e}")
    raise  # Fail hard - all services MUST have proper environment variables


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
