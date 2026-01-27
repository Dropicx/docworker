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

import asyncio
import json
import logging
import os
import re
from typing import Literal

import httpx

logger = logging.getLogger(__name__)


def _post_process_pii_cleanup(text: str) -> str:
    """
    Post-process cleaned text to catch PII patterns missed by external service.

    This catches edge cases where the external SpaCy/Presidio service fails:
    1. Email local parts that look like names (firstname.lastname@)
    2. German insurance IDs and status codes
    3. Partial phone numbers and extensions
    4. Leaked names before @[EMAIL_DOMAIN]

    Args:
        text: Text already processed by external PII service

    Returns:
        Text with additional PII patterns removed
    """
    if not text:
        return text

    original_length = len(text)

    # 1. Clean email local parts that look like names before @[EMAIL_DOMAIN]
    # Pattern: firstname.lastname@ or firstname-lastname@ or firstname_lastname@
    # Also handles compound names like silvia.jacquemin-fink
    # These should be replaced with [EMAIL] entirely
    text = re.sub(
        r'[a-zA-ZäöüÄÖÜß]+(?:[.\-_][a-zA-ZäöüÄÖÜß]+)+\s*\n?\s*@\[EMAIL_DOMAIN\]',
        '[EMAIL]',
        text,
        flags=re.IGNORECASE
    )

    # Also catch standalone name patterns before @ (with newline between)
    text = re.sub(
        r'[a-zA-ZäöüÄÖÜß]+(?:[.\-_][a-zA-ZäöüÄÖÜß]+)+\s*\n\s*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        '[EMAIL]',
        text,
        flags=re.IGNORECASE
    )

    # Catch email local parts before @ without [EMAIL_DOMAIN] placeholder
    text = re.sub(
        r'[a-zA-ZäöüÄÖÜß]+(?:[.\-_][a-zA-ZäöüÄÖÜß]+)+\s*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        '[EMAIL]',
        text,
        flags=re.IGNORECASE
    )

    # 2. Clean German insurance IDs (Versichertennummer)
    # Format: Letter + 9 digits (e.g., O598926034) or just 9-10 digit numbers
    text = re.sub(
        r'\b[A-Z]\d{9,10}\b',
        '[INSURANCE_ID]',
        text
    )

    # 3. Clean insurance status patterns (e.g., "Status M", "Status P", "Status F")
    text = re.sub(
        r',?\s*Status\s+[A-Z]\b',
        '',
        text,
        flags=re.IGNORECASE
    )

    # 4. Clean partial phone extensions (e.g., "/- 2764", "/ -2764", "/-2764")
    # These appear when the main number was anonymized but extension leaked
    text = re.sub(
        r'\s*/\s*-?\s*\d{2,5}\b',
        '',
        text
    )

    # 5. Clean orphaned phone patterns after [PHONE] placeholder
    text = re.sub(
        r'\[PHONE\]\s*/?\s*-?\s*\d{2,5}',
        '[PHONE]',
        text
    )

    # 6. Clean Fallnummer (case number) patterns
    text = re.sub(
        r'Fallnummer:?\s*\d{8,12}',
        'Fallnummer: [CASE_ID]',
        text,
        flags=re.IGNORECASE
    )

    # 7. Clean any remaining German city/insurance combo (e.g., "/Hamburg")
    # Pattern: slash followed by German city name in header context
    text = re.sub(
        r'/[A-ZÄÖÜ][a-zäöüß]+(?=,|\s|$)',
        '',
        text
    )

    # 8. Clean street addresses without common suffixes (e.g., "Rhedung 18 b")
    # Pattern: StreetName + Number + optional letter, followed by PLZ
    # Replaces the street+number part, keeps the PLZ handling to other patterns
    text = re.sub(
        r'([A-ZÄÖÜ][a-zäöüß-]+)\s+(\d{1,4}\s*[a-zA-Z]?)\s*,\s*(?=\d{5}\s|\[PLZ)',
        '[ADDRESS], ',
        text,
        flags=re.IGNORECASE
    )

    # 9. Fix IP_ADDRESS false positives in lab reference ranges
    # Pattern: "[IP_ADDRESS]" appearing inside parentheses followed by lab units
    # E.g., "Haptoglobin 0.93 ([IP_ADDRESS] g/l)" should be restored to show the range format
    # Since we can't restore the original value, we replace with a generic range indicator
    text = re.sub(
        r'\(\[IP_ADDRESS\]\s*(g/l|mg/dl|mmol/l|µmol/l|u/l|iu/l|%|/µl|/ml)\)',
        r'([REF_RANGE] \1)',
        text,
        flags=re.IGNORECASE
    )

    # Log if we made changes
    if len(text) != original_length:
        logger.debug(f"PII post-processing removed {original_length - len(text)} chars")

    return text

# Configuration from environment
# Primary: Hetzner PII service (production)
EXTERNAL_PII_URL = os.getenv("EXTERNAL_PII_URL", "")
EXTERNAL_PII_API_KEY = os.getenv("EXTERNAL_PII_API_KEY", "")
USE_EXTERNAL_PII = os.getenv("USE_EXTERNAL_PII", "false").lower() == "true"

# Fallback: Railway PII service (backup, usually in sleep mode)
FALLBACK_PII_URL = os.getenv("FALLBACK_PII_URL", "")
FALLBACK_PII_API_KEY = os.getenv("FALLBACK_PII_API_KEY", "")


class PIIServiceClient:
    """
    Client for external SpaCy PII removal service.

    Features:
    - HTTPS communication with API key authentication
    - Automatic fallback to Railway service if Hetzner unavailable
    - Configurable timeout for large documents
    - Health check support
    - Syncs custom protection terms from database with each request
    """

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        fallback_url: str | None = None,
        fallback_api_key: str | None = None,
        timeout: float = 60.0,
        fallback_timeout: float = 180.0
    ):
        """
        Initialize PII service client.

        Args:
            url: Override EXTERNAL_PII_URL from environment (Hetzner primary)
            api_key: Override EXTERNAL_PII_API_KEY from environment
            fallback_url: Override FALLBACK_PII_URL from environment (Railway backup)
            fallback_api_key: Override FALLBACK_PII_API_KEY from environment
            timeout: Request timeout in seconds (default 60s for large documents)
            fallback_timeout: Timeout for fallback service (default 180s - Railway may need to wake up and load models)
        """
        # Primary: Hetzner
        self.url = url or EXTERNAL_PII_URL
        self.api_key = api_key or EXTERNAL_PII_API_KEY

        # Fallback: Railway
        self.fallback_url = fallback_url or FALLBACK_PII_URL
        self.fallback_api_key = fallback_api_key or FALLBACK_PII_API_KEY

        self.timeout = timeout
        self.fallback_timeout = fallback_timeout
        self._custom_terms_cache: list[str] | None = None
        self._custom_terms_cache_time: float = 0

        if self.url:
            logger.info(f"PII Service Client initialized - Primary: {self.url}")
        if self.fallback_url:
            logger.info(f"PII Service Client fallback configured - Fallback: {self.fallback_url}")
        if not self.url and not self.fallback_url:
            logger.warning("PII Service Client: No PII service URL configured!")

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
            from app.database.connection import get_session
            from app.database.models import SystemSettingsDB

            with next(get_session()) as db:
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

    @property
    def has_fallback(self) -> bool:
        """Check if fallback PII service is configured."""
        return bool(self.fallback_url)

    async def _wake_up_fallback_service(
        self,
        max_attempts: int = 10,
        initial_delay: float = 3.0,
        max_delay: float = 15.0
    ) -> bool:
        """
        Wake up the Railway fallback service from sleep mode.

        Railway services go to sleep after inactivity. The first request triggers
        wake-up, but the service needs time to start the container and load SpaCy models.

        Args:
            max_attempts: Maximum number of health check attempts
            initial_delay: Initial delay between attempts in seconds
            max_delay: Maximum delay between attempts (with backoff)

        Returns:
            True if service became healthy, False otherwise
        """
        if not self.fallback_url:
            return False

        logger.info(f"Waking up Railway PII service at {self.fallback_url}...")

        delay = initial_delay
        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{self.fallback_url}/health")

                    if response.status_code == 200:
                        health = response.json()
                        status = health.get("status", "unknown")

                        if status == "healthy":
                            logger.info(f"Railway PII service is healthy after {attempt} attempt(s)")
                            return True
                        elif status == "degraded":
                            # Service is up but not all models loaded yet
                            logger.info(f"Railway PII service is degraded, waiting for models... (attempt {attempt}/{max_attempts})")
                        else:
                            logger.info(f"Railway PII service status: {status} (attempt {attempt}/{max_attempts})")
                    else:
                        logger.debug(f"Health check returned {response.status_code} (attempt {attempt}/{max_attempts})")

            except httpx.ConnectError:
                logger.debug(f"Railway PII service not yet reachable (attempt {attempt}/{max_attempts})")
            except httpx.TimeoutException:
                logger.debug(f"Railway PII service health check timeout (attempt {attempt}/{max_attempts})")
            except Exception as e:
                logger.debug(f"Health check error: {e} (attempt {attempt}/{max_attempts})")

            if attempt < max_attempts:
                logger.info(f"Waiting {delay:.1f}s before next wake-up attempt...")
                await asyncio.sleep(delay)
                # Increase delay with backoff, but cap at max_delay
                delay = min(delay * 1.5, max_delay)

        logger.warning(f"Railway PII service did not become healthy after {max_attempts} attempts")
        return False

    async def remove_pii(
        self,
        text: str,
        language: Literal["de", "en"] = "de",
        include_metadata: bool = True
    ) -> tuple[str, dict]:
        """
        Remove PII from text using external service with Railway fallback.

        Priority:
        1. Hetzner PII service (primary, EXTERNAL_PII_URL)
        2. Railway PII service (fallback, FALLBACK_PII_URL)

        Args:
            text: Text to process
            language: Language code ('de' or 'en')
            include_metadata: Include detection metadata in response

        Returns:
            Tuple of (cleaned_text, metadata_dict)

        Raises:
            Exception: If both primary and fallback services fail
        """
        primary_error = None
        fallback_error = None

        # Try primary service (Hetzner)
        if self.is_external_enabled:
            try:
                logger.debug(f"Calling primary PII service: {self.url}")
                result = await self._call_service(
                    self.url, self.api_key, text, language, include_metadata,
                    timeout=self.timeout
                )
                result[1]["service_used"] = "primary"
                return result
            except Exception as e:
                primary_error = str(e)
                logger.warning(f"Primary PII service failed: {e}")

        # Try fallback service (Railway) - wake up first, then call with longer timeout
        if self.has_fallback:
            try:
                # Wake up the sleeping Railway service first
                is_ready = await self._wake_up_fallback_service()
                if not is_ready:
                    logger.warning("Railway PII service wake-up failed, attempting request anyway...")

                logger.info(f"Calling fallback PII service: {self.fallback_url}")
                result = await self._call_service(
                    self.fallback_url, self.fallback_api_key, text, language, include_metadata,
                    timeout=self.fallback_timeout
                )
                result[1]["service_used"] = "fallback"
                return result
            except Exception as e:
                fallback_error = str(e)
                logger.error(f"Fallback PII service also failed: {e}")

        # Both failed - raise error
        error_msg = f"All PII services failed. Primary: {primary_error}, Fallback: {fallback_error}"
        logger.error(error_msg)
        raise Exception(error_msg)

    async def _call_service(
        self,
        url: str,
        api_key: str,
        text: str,
        language: str,
        include_metadata: bool,
        timeout: float | None = None
    ) -> tuple[str, dict]:
        """Call a PII service API with custom protection terms."""
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key

        # Load custom terms from database to sync with external service
        custom_terms = self._load_custom_terms_from_db()

        payload = {
            "text": text,
            "language": language,
            "include_metadata": include_metadata,
            "custom_protection_terms": custom_terms if custom_terms else None
        }

        request_timeout = timeout or self.timeout
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(
                f"{url}/remove-pii",
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                result = response.json()
                cleaned_text = result["cleaned_text"]

                # Apply post-processing to catch missed PII patterns
                cleaned_text = _post_process_pii_cleanup(cleaned_text)

                metadata = result.get("metadata", {})
                metadata["custom_terms_synced"] = len(custom_terms) if custom_terms else 0
                metadata["post_processed"] = True
                return cleaned_text, metadata

            elif response.status_code in (401, 403):
                raise Exception(f"PII service authentication failed: {response.status_code}")

            elif response.status_code == 503:
                raise Exception("PII service unavailable (503)")

            else:
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
        Remove PII from multiple texts with fallback support.

        Args:
            texts: List of texts to process
            language: Language code
            batch_size: Batch size for external service

        Returns:
            List of (cleaned_text, metadata) tuples
        """
        primary_error = None
        fallback_error = None

        # Try primary service (Hetzner)
        if self.is_external_enabled:
            try:
                return await self._call_batch_service(
                    self.url, self.api_key, texts, language, batch_size,
                    timeout=self.timeout * 2
                )
            except Exception as e:
                primary_error = str(e)
                logger.warning(f"Primary batch PII failed: {e}")

        # Try fallback service (Railway) - wake up first, then call with longer timeout
        if self.has_fallback:
            try:
                # Wake up the sleeping Railway service first
                is_ready = await self._wake_up_fallback_service()
                if not is_ready:
                    logger.warning("Railway PII service wake-up failed, attempting batch request anyway...")

                return await self._call_batch_service(
                    self.fallback_url, self.fallback_api_key, texts, language, batch_size,
                    timeout=self.fallback_timeout * 2
                )
            except Exception as e:
                fallback_error = str(e)
                logger.error(f"Fallback batch PII also failed: {e}")

        # Both failed
        error_msg = f"All batch PII services failed. Primary: {primary_error}, Fallback: {fallback_error}"
        raise Exception(error_msg)

    async def _call_batch_service(
        self,
        url: str,
        api_key: str,
        texts: list[str],
        language: str,
        batch_size: int,
        timeout: float | None = None
    ) -> list[tuple[str, dict]]:
        """Call a batch PII service API with custom protection terms."""
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key

        # Load custom terms from database to sync with external service
        custom_terms = self._load_custom_terms_from_db()

        payload = {
            "texts": texts,
            "language": language,
            "batch_size": batch_size,
            "custom_protection_terms": custom_terms if custom_terms else None
        }

        request_timeout = timeout or (self.timeout * 2)
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(
                f"{url}/remove-pii/batch",
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                result = response.json()
                # Apply post-processing to each result
                processed_results = []
                for item in result["results"]:
                    cleaned_text = _post_process_pii_cleanup(item["cleaned_text"])
                    metadata = item.get("metadata", {})
                    metadata["post_processed"] = True
                    processed_results.append((cleaned_text, metadata))
                return processed_results
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
