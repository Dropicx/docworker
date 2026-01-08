"""
PII Service Client

HTTP client for calling external SpaCy PII removal service at Hetzner.
Falls back to local AdvancedPrivacyFilter if external service unavailable.

Environment Variables:
    EXTERNAL_PII_URL: URL of PII service (e.g., https://pii.fra-la.de)
    EXTERNAL_PII_API_KEY: API key for authentication
    USE_EXTERNAL_PII: Set to 'true' to use external service

Usage:
    >>> client = PIIServiceClient()
    >>> cleaned, metadata = await client.remove_pii("Patient: Max Mustermann", "de")
"""

import json
import logging
import os
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

# Configuration from environment
EXTERNAL_PII_URL = os.getenv("EXTERNAL_PII_URL", "")
EXTERNAL_PII_API_KEY = os.getenv("EXTERNAL_PII_API_KEY", "")
USE_EXTERNAL_PII = os.getenv("USE_EXTERNAL_PII", "false").lower() == "true"


class PIIServiceClient:
    """
    Client for external SpaCy PII removal service.

    Features:
    - HTTPS communication with API key authentication
    - Automatic fallback to local filter if service unavailable
    - Configurable timeout for large documents
    - Health check support
    - Syncs custom protection terms from database with each request
    """

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        timeout: float = 60.0
    ):
        """
        Initialize PII service client.

        Args:
            url: Override EXTERNAL_PII_URL from environment
            api_key: Override EXTERNAL_PII_API_KEY from environment
            timeout: Request timeout in seconds (default 60s for large documents)
        """
        self.url = url or EXTERNAL_PII_URL
        self.api_key = api_key or EXTERNAL_PII_API_KEY
        self.timeout = timeout
        self._local_filter = None
        self._custom_terms_cache: list[str] | None = None
        self._custom_terms_cache_time: float = 0

        if self.url:
            logger.info(f"PII Service Client initialized - URL: {self.url}")
        else:
            logger.info("PII Service Client initialized - No external URL configured")

    def _load_custom_terms_from_db(self) -> list[str]:
        """
        Load custom protection terms from database.

        Loads terms from system_settings table:
        - privacy_filter.custom_medical_terms
        - privacy_filter.custom_drug_names
        - privacy_filter.custom_eponyms

        Returns:
            Combined list of all custom protection terms
        """
        import time

        # Cache for 60 seconds to avoid DB hits on every request
        if self._custom_terms_cache is not None:
            if time.time() - self._custom_terms_cache_time < 60:
                return self._custom_terms_cache

        all_terms: list[str] = []

        try:
            from app.database.connection import get_db_session
            from app.database.models import SystemSettingsDB

            with get_db_session() as db:
                # Load all custom term settings
                settings_keys = [
                    "privacy_filter.custom_medical_terms",
                    "privacy_filter.custom_drug_names",
                    "privacy_filter.custom_eponyms",
                ]

                for key in settings_keys:
                    setting = db.query(SystemSettingsDB).filter(
                        SystemSettingsDB.key == key
                    ).first()

                    if setting and setting.value:
                        try:
                            terms = json.loads(setting.value)
                            if isinstance(terms, list):
                                all_terms.extend(terms)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in {key}")

            # Update cache
            self._custom_terms_cache = all_terms
            self._custom_terms_cache_time = time.time()
            logger.debug(f"Loaded {len(all_terms)} custom protection terms from database")

        except Exception as e:
            logger.warning(f"Could not load custom terms from database: {e}")

        return all_terms

    @property
    def is_external_enabled(self) -> bool:
        """Check if external PII service is configured."""
        return bool(self.url) and USE_EXTERNAL_PII

    def _get_local_filter(self):
        """Lazy-load local privacy filter as fallback."""
        if self._local_filter is None:
            from app.services.privacy_filter_advanced import AdvancedPrivacyFilter
            self._local_filter = AdvancedPrivacyFilter(load_custom_terms=False)
        return self._local_filter

    async def remove_pii(
        self,
        text: str,
        language: Literal["de", "en"] = "de",
        include_metadata: bool = True
    ) -> tuple[str, dict]:
        """
        Remove PII from text using external service or local fallback.

        Args:
            text: Text to process
            language: Language code ('de' or 'en')
            include_metadata: Include detection metadata in response

        Returns:
            Tuple of (cleaned_text, metadata_dict)

        Raises:
            Exception: If both external service and local fallback fail
        """
        # Use external service if configured
        if self.is_external_enabled:
            try:
                return await self._call_external_service(text, language, include_metadata)
            except Exception as e:
                logger.warning(f"External PII service failed, falling back to local: {e}")

        # Fallback to local filter
        logger.debug("Using local privacy filter")
        local_filter = self._get_local_filter()
        return local_filter.remove_pii(text)

    async def _call_external_service(
        self,
        text: str,
        language: str,
        include_metadata: bool
    ) -> tuple[str, dict]:
        """Call external PII service API with custom protection terms."""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        headers["Content-Type"] = "application/json"

        # Load custom terms from database to sync with external service
        custom_terms = self._load_custom_terms_from_db()

        payload = {
            "text": text,
            "language": language,
            "include_metadata": include_metadata,
            "custom_protection_terms": custom_terms if custom_terms else None
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.url}/remove-pii",
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                result = response.json()
                metadata = result.get("metadata", {})
                metadata["custom_terms_synced"] = len(custom_terms) if custom_terms else 0
                return result["cleaned_text"], metadata

            elif response.status_code in (401, 403):
                logger.error(f"PII service authentication failed: {response.status_code}")
                raise Exception(f"PII service authentication failed: {response.status_code}")

            elif response.status_code == 503:
                logger.error("PII service unavailable")
                raise Exception("PII service unavailable")

            else:
                logger.error(f"PII service error: {response.status_code} - {response.text}")
                raise Exception(f"PII service error: {response.status_code}")

    async def check_health(self) -> dict:
        """
        Check health of external PII service.

        Returns:
            Health status dict or error info
        """
        if not self.url:
            return {"status": "not_configured", "external_url": None}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.url}/health")

                if response.status_code == 200:
                    health = response.json()
                    health["external_url"] = self.url
                    return health
                else:
                    return {
                        "status": "error",
                        "external_url": self.url,
                        "error": f"HTTP {response.status_code}"
                    }

        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "external_url": self.url,
                "error": "Connection timeout"
            }

        except httpx.ConnectError as e:
            return {
                "status": "unreachable",
                "external_url": self.url,
                "error": str(e)
            }

        except Exception as e:
            return {
                "status": "error",
                "external_url": self.url,
                "error": str(e)
            }

    async def remove_pii_batch(
        self,
        texts: list[str],
        language: Literal["de", "en"] = "de",
        batch_size: int = 32
    ) -> list[tuple[str, dict]]:
        """
        Remove PII from multiple texts.

        Args:
            texts: List of texts to process
            language: Language code
            batch_size: Batch size for external service

        Returns:
            List of (cleaned_text, metadata) tuples
        """
        if self.is_external_enabled:
            try:
                return await self._call_external_batch(texts, language, batch_size)
            except Exception as e:
                logger.warning(f"External batch PII failed, falling back to local: {e}")

        # Fallback to local filter
        local_filter = self._get_local_filter()
        return [local_filter.remove_pii(text) for text in texts]

    async def _call_external_batch(
        self,
        texts: list[str],
        language: str,
        batch_size: int
    ) -> list[tuple[str, dict]]:
        """Call external batch PII service API with custom protection terms."""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        headers["Content-Type"] = "application/json"

        # Load custom terms from database to sync with external service
        custom_terms = self._load_custom_terms_from_db()

        payload = {
            "texts": texts,
            "language": language,
            "batch_size": batch_size,
            "custom_protection_terms": custom_terms if custom_terms else None
        }

        async with httpx.AsyncClient(timeout=self.timeout * 2) as client:
            response = await client.post(
                f"{self.url}/remove-pii/batch",
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                result = response.json()
                return [
                    (item["cleaned_text"], item.get("metadata", {}))
                    for item in result["results"]
                ]
            else:
                raise Exception(f"Batch PII service error: {response.status_code}")


# Convenience function for simple usage
async def remove_pii_external(
    text: str,
    language: Literal["de", "en"] = "de"
) -> tuple[str, dict]:
    """
    Convenience function to remove PII using external service.

    Args:
        text: Text to process
        language: Language code

    Returns:
        Tuple of (cleaned_text, metadata)
    """
    client = PIIServiceClient()
    return await client.remove_pii(text, language)
