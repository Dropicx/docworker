"""
OCR Engine Manager

Worker-ready service for managing OCR engine selection and configuration.
Supports multiple OCR engines based on database configuration.
"""

import json
import logging
import os
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import OCRConfigurationDB, OCREngineEnum
from app.repositories.ocr_configuration_repository import OCRConfigurationRepository
from app.services.hybrid_text_extractor import HybridTextExtractor

logger = logging.getLogger(__name__)


def _normalize_paddleocr_url(url: str) -> str:
    """
    Normalize PaddleOCR service URL to handle IPv6 and missing scheme.

    Railway provides IPv6 addresses that need brackets in URLs.
    Also ensures http:// prefix is present and removes trailing slashes.
    """
    if not url:
        return "http://paddleocr.railway.internal:9123"

    # Remove trailing slashes to prevent double slashes in paths
    url = url.rstrip("/")

    # Add http:// if missing
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"

    # Check if we have a bare IPv6 address (contains : but not wrapped in [])
    # Format: http://ipv6:port needs to become http://[ipv6]:port
    if url.startswith("http://") and ":" in url:
        # Extract the part after http://
        rest = url[7:]  # Remove 'http://'

        # Check if it's IPv6 (multiple colons and not already bracketed)
        if rest.count(":") > 1 and not rest.startswith("["):
            # Split on last colon to separate address from port
            parts = rest.rsplit(":", 1)
            if len(parts) == 2:
                ipv6_addr, port = parts
                # Rebuild with brackets around IPv6
                url = f"http://[{ipv6_addr}]:{port}"
                logger.info(f"🔧 Normalized IPv6 URL to: {url}")

    return url


# PaddleOCR microservice URL (Railway internal networking)
_raw_url = os.getenv("PADDLEOCR_SERVICE_URL", "http://paddleocr.railway.internal:9123")

# Debug: Log raw environment variable value
logger.info(f"🔍 Raw PADDLEOCR_SERVICE_URL env var: {repr(_raw_url)}")

PADDLEOCR_SERVICE_URL = _normalize_paddleocr_url(_raw_url)

# Log the URL being used at startup
logger.info(f"🔗 PaddleOCR service URL (after normalization): {PADDLEOCR_SERVICE_URL}")

# External PaddleOCR service configuration (for Hetzner/external deployments)
EXTERNAL_OCR_URL = os.getenv("EXTERNAL_OCR_URL", "")
EXTERNAL_API_KEY = os.getenv("EXTERNAL_API_KEY", "")
USE_EXTERNAL_OCR = os.getenv("USE_EXTERNAL_OCR", "false").lower() == "true"

if EXTERNAL_OCR_URL:
    logger.info(f"🌐 External OCR URL configured: {EXTERNAL_OCR_URL}")
    logger.info(f"🔑 External OCR API key: {'configured' if EXTERNAL_API_KEY else 'not set'}")
    logger.info(f"🔧 Use external OCR: {USE_EXTERNAL_OCR}")


class OCREngineManager:
    """Database-driven OCR engine manager with intelligent strategy selection.

    Orchestrates multiple OCR engines based on database configuration, providing
    fallback mechanisms and automatic quality-based routing. Supports three engines:
    PaddleOCR (fast microservice), Vision LLM (high accuracy), and Hybrid (intelligent).

    The manager loads configuration from the database and automatically selects
    the appropriate OCR strategy. Each engine has distinct characteristics:

    **Supported Engines**:
        - PADDLEOCR: CPU-based microservice, 2-5s/page, excellent accuracy, free
        - VISION_LLM: Qwen 2.5 VL model, ~2 min/page, excellent accuracy, OVH cost
        - HYBRID: Intelligent router, variable speed, optimal accuracy, variable cost

    **Fallback Strategy**:
        All engines fall back to HYBRID on failure, ensuring processing always completes.
        The system prioritizes reliability over strict engine adherence.

    Attributes:
        session (Session): SQLAlchemy database session for config loading
        hybrid_extractor (HybridTextExtractor): Fallback extractor instance

    Example:
        >>> manager = OCREngineManager(db_session)
        >>> text, confidence = await manager.extract_text(
        ...     file_content=pdf_bytes,
        ...     file_type="pdf",
        ...     filename="medical_report.pdf"
        ... )
        >>> print(f"Extracted {len(text)} chars with {confidence:.0%} confidence")

    Note:
        Configuration is loaded fresh on each extraction to allow runtime changes
        without service restarts.
    """

    def __init__(
        self, session: Session, config_repository: OCRConfigurationRepository | None = None
    ) -> None:
        """Initialize OCR Engine Manager with database session.

        Args:
            session: SQLAlchemy session (kept for backward compatibility)
            config_repository: OCR configuration repository (injected for clean architecture)
        """
        self.session = session
        self.config_repository = config_repository or OCRConfigurationRepository(session)
        self.hybrid_extractor = HybridTextExtractor()

    # ==================== CONFIGURATION ====================

    def load_ocr_config(self) -> OCRConfigurationDB | None:
        """
        Load OCR configuration from database using repository pattern.

        Returns:
            OCR configuration or None if not found
        """
        try:
            config = self.config_repository.get_config()
            if config:
                logger.info(f"🔍 Loaded OCR config: {config.selected_engine}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load OCR config: {e}")
            return None

    def get_engine_config(self, engine: OCREngineEnum) -> dict[str, Any]:
        """
        Get configuration for specific OCR engine.

        Args:
            engine: OCR engine enum value

        Returns:
            Engine-specific configuration dict
        """
        config = self.load_ocr_config()
        if not config:
            return {}

        config_map = {
            OCREngineEnum.PADDLEOCR: config.paddleocr_config,
            OCREngineEnum.VISION_LLM: config.vision_llm_config,
            OCREngineEnum.HYBRID: config.hybrid_config,
        }

        engine_config = config_map.get(engine)

        # Parse JSON if stored as string
        if isinstance(engine_config, str):
            try:
                return json.loads(engine_config)
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Failed to parse config for {engine}, using default")
                return {}

        return engine_config or {}

    # ==================== OCR EXECUTION ====================

    async def extract_text(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        override_engine: OCREngineEnum | None = None,
    ) -> tuple[str, float]:
        """Extract text from document using database-configured OCR engine.

        Loads OCR configuration from database and dispatches to the appropriate
        engine. Automatically falls back to HYBRID on errors. Supports engine
        override for testing specific OCR strategies.

        Args:
            file_content: Document content as raw bytes
            file_type: File extension/type ('pdf', 'jpg', 'png', etc.)
            filename: Original filename for logging and debugging
            override_engine: Optional engine override for testing. If provided,
                ignores database configuration. Default None.

        Returns:
            tuple[str, float]: A tuple containing:
                - str: Extracted text with preserved formatting
                - float: Confidence score (0.0-1.0) based on OCR quality

        Raises:
            Returns error message as text with 0.0 confidence instead of raising.
            Logs detailed error information for debugging.

        Example:
            >>> manager = OCREngineManager(db_session)
            >>> # Use database-configured engine
            >>> text, conf = await manager.extract_text(
            ...     file_content=pdf_bytes,
            ...     file_type="pdf",
            ...     filename="report.pdf"
            ... )
            >>> print(f"Confidence: {conf:.0%}")
            >>>
            >>> # Override for testing
            >>> text, conf = await manager.extract_text(
            ...     file_content=pdf_bytes,
            ...     file_type="pdf",
            ...     filename="report.pdf",
            ...     override_engine=OCREngineEnum.VISION_LLM
            ... )

        Note:
            **Engine Selection Priority**:
            1. override_engine (if provided)
            2. Database configuration (ocr_configuration.selected_engine)
            3. Default to HYBRID if database config missing

            **Fallback Behavior**:
            - PADDLEOCR failure → HYBRID
            - VISION_LLM failure → HYBRID
            - HYBRID cannot fail (uses multiple strategies internally)
        """
        # Determine which engine to use
        config = self.load_ocr_config()
        selected_engine = override_engine or (
            config.selected_engine if config else OCREngineEnum.HYBRID
        )

        logger.info(f"🔍 Starting OCR with engine: {selected_engine}")

        try:
            if selected_engine == OCREngineEnum.HYBRID:
                # Use hybrid extractor (current production system)
                return await self._extract_with_hybrid(file_content, file_type, filename)

            if selected_engine == OCREngineEnum.VISION_LLM:
                # Force Vision LLM
                return await self._extract_with_vision_llm(file_content, file_type, filename)

            if selected_engine == OCREngineEnum.PADDLEOCR:
                # PaddleOCR (future implementation)
                return await self._extract_with_paddleocr(file_content, file_type, filename)

            logger.warning(f"⚠️ Unknown engine {selected_engine}, falling back to HYBRID")
            return await self._extract_with_hybrid(file_content, file_type, filename)

        except Exception as e:
            logger.error(f"❌ OCR extraction failed: {e}")
            return f"OCR extraction error: {str(e)}", 0.0

    # ==================== ENGINE-SPECIFIC EXTRACTION ====================

    async def _extract_with_hybrid(
        self, file_content: bytes, file_type: str, filename: str
    ) -> tuple[str, float]:
        """
        Extract text using hybrid strategy (intelligent routing).

        This is the current production system that automatically selects
        the best OCR method based on document quality analysis.
        """
        logger.info("🎯 Using HYBRID extraction (intelligent routing)")
        return await self.hybrid_extractor.extract_text(file_content, file_type, filename)

    async def _extract_with_vision_llm(
        self, file_content: bytes, file_type: str, filename: str
    ) -> tuple[str, float]:
        """
        Extract text using Vision Language Model (Qwen 2.5 VL).

        Slow (~2 minutes/page) but very accurate for complex documents.
        """
        logger.info("🤖 Using VISION_LLM extraction")

        # Get Vision LLM configuration
        vision_config = self.get_engine_config(OCREngineEnum.VISION_LLM)

        try:
            return await self.hybrid_extractor._extract_with_vision_llm(
                file_content, file_type, vision_config
            )
        except Exception as e:
            logger.error(f"❌ Vision LLM extraction failed: {e}")
            logger.info("🔄 Falling back to hybrid extraction")
            return await self._extract_with_hybrid(file_content, file_type, filename)

    async def _extract_with_paddleocr(
        self, file_content: bytes, file_type: str, filename: str
    ) -> tuple[str, float]:
        """
        Extract text using PaddleOCR microservice (PP-StructureV3).

        Tries external OCR service first if USE_EXTERNAL_OCR=true and EXTERNAL_OCR_URL is set.
        Falls back to internal Railway PaddleOCR service, then to hybrid extraction.

        Calls the PaddleOCR service via HTTP with structured mode for Markdown/JSON output.
        Prefers markdown output when available for better table and layout preservation.
        """
        # Try external OCR first if configured
        if USE_EXTERNAL_OCR and EXTERNAL_OCR_URL:
            try:
                logger.info(f"🌐 Trying external OCR at {EXTERNAL_OCR_URL}")
                return await self._extract_with_external_paddleocr(
                    file_content, file_type, filename
                )
            except Exception as e:
                logger.warning(f"⚠️ External OCR failed: {e}, trying internal service")

        # Fall back to internal Railway PaddleOCR service
        return await self._extract_with_internal_paddleocr(file_content, file_type, filename)

    async def _extract_with_external_paddleocr(
        self, file_content: bytes, file_type: str, filename: str
    ) -> tuple[str, float]:
        """
        Extract text using external PaddleOCR service (Hetzner/external deployment).

        Uses API key authentication via X-API-Key header.
        Raises exception on failure to allow fallback to internal service.
        """
        logger.info(f"🌐 Calling external PaddleOCR at {EXTERNAL_OCR_URL}")
        logger.info(f"📄 File: {filename}, Type: {file_type}, Size: {len(file_content)} bytes")

        # Extended timeout for external service (may be slower due to network)
        async with httpx.AsyncClient(timeout=180.0) as client:
            # Prepare multipart form data with correct MIME type
            mime_type = "application/pdf" if file_type.lower() == "pdf" else f"image/{file_type}"
            files = {"file": (filename, file_content, mime_type)}

            # Request structured mode for Markdown output
            params = {"mode": "structured"}

            # Prepare headers with API key
            headers = {}
            if EXTERNAL_API_KEY:
                headers["X-API-Key"] = EXTERNAL_API_KEY

            # Call external PaddleOCR service
            response = await client.post(
                f"{EXTERNAL_OCR_URL}/extract",
                files=files,
                params=params,
                headers=headers
            )

            if response.status_code == 200:
                result = response.json()

                # Prefer markdown output for structured content (tables, etc.)
                extracted_text = result.get("markdown") or result.get("text", "")
                confidence = result.get("confidence", 0.0)
                processing_time = result.get("processing_time", 0.0)
                engine = result.get("engine", "PaddleOCR")
                mode = result.get("mode", "text")

                logger.info(f"✅ External {engine} extraction completed in {processing_time:.2f}s (mode: {mode})")
                logger.info(f"📊 Confidence: {confidence:.2%}, Length: {len(extracted_text)} chars")

                if result.get("markdown"):
                    logger.info("📝 Using Markdown output (structured)")

                return extracted_text, confidence

            elif response.status_code in (401, 403):
                logger.error(f"❌ External OCR authentication failed: {response.status_code}")
                raise Exception(f"External OCR authentication failed: {response.status_code}")
            else:
                logger.error(f"❌ External OCR service error: {response.status_code}")
                raise Exception(f"External OCR service returned {response.status_code}")

    async def _extract_with_internal_paddleocr(
        self, file_content: bytes, file_type: str, filename: str
    ) -> tuple[str, float]:
        """
        Extract text using internal PaddleOCR microservice (Railway deployment).

        Falls back to hybrid extraction on failure.
        """
        logger.info(f"🤖 Calling internal PaddleOCR at {PADDLEOCR_SERVICE_URL}")
        logger.info(f"📄 File: {filename}, Type: {file_type}, Size: {len(file_content)} bytes")

        try:
            # Extended timeout for PP-StructureV3 (first request may trigger model downloads)
            # PP-StructureV3 can take 2-3 minutes on first request while loading models
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Prepare multipart form data with correct MIME type
                mime_type = "application/pdf" if file_type.lower() == "pdf" else f"image/{file_type}"
                files = {"file": (filename, file_content, mime_type)}

                # Request structured mode for Markdown output
                params = {"mode": "structured"}

                # Call PaddleOCR microservice
                response = await client.post(
                    f"{PADDLEOCR_SERVICE_URL}/extract",
                    files=files,
                    params=params
                )

                if response.status_code == 200:
                    result = response.json()

                    # Prefer markdown output for structured content (tables, etc.)
                    extracted_text = result.get("markdown") or result.get("text", "")
                    confidence = result.get("confidence", 0.0)
                    processing_time = result.get("processing_time", 0.0)
                    engine = result.get("engine", "PaddleOCR")
                    mode = result.get("mode", "text")

                    logger.info(f"✅ {engine} extraction completed in {processing_time:.2f}s (mode: {mode})")
                    logger.info(
                        f"📊 Confidence: {confidence:.2%}, Length: {len(extracted_text)} chars"
                    )

                    # Log if we got markdown output
                    if result.get("markdown"):
                        logger.info("📝 Using Markdown output (structured)")

                    return extracted_text, confidence

                logger.error(f"❌ PaddleOCR service error: {response.status_code}")
                raise Exception(f"PaddleOCR service returned {response.status_code}")

        except httpx.TimeoutException:
            logger.error("❌ PaddleOCR service timeout (300s) - PP-StructureV3 may be loading models")
            logger.info("🔄 Falling back to hybrid extraction")
            return await self._extract_with_hybrid(file_content, file_type, filename)

        except httpx.ConnectError as e:
            logger.error(f"❌ Could not connect to PaddleOCR service: {e}")
            logger.info("🔄 Falling back to hybrid extraction")
            return await self._extract_with_hybrid(file_content, file_type, filename)

        except Exception as e:
            logger.error(f"❌ PaddleOCR extraction failed: {e}")
            logger.info("🔄 Falling back to hybrid extraction")
            return await self._extract_with_hybrid(file_content, file_type, filename)

    # ==================== UTILITY METHODS ====================

    async def check_paddleocr_health(self) -> bool:
        """
        Check if PaddleOCR microservice is available (async version).

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{PADDLEOCR_SERVICE_URL}/health")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("paddleocr_available", False)
        except Exception as e:
            logger.debug(f"PaddleOCR health check failed: {e}")
        return False

    def _check_paddleocr_health_sync(self) -> bool:
        """
        Check if PaddleOCR microservice is available (synchronous version).

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            logger.info(f"🔍 Checking PaddleOCR service at: {PADDLEOCR_SERVICE_URL}")

            # More detailed connection attempt with longer timeout
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                logger.info(f"📡 Attempting HTTP GET to {PADDLEOCR_SERVICE_URL}/health")
                response = client.get(f"{PADDLEOCR_SERVICE_URL}/health")

                logger.info(f"📊 Response status: {response.status_code}")
                logger.info(f"📊 Response headers: {dict(response.headers)}")

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"📊 Response body: {data}")

                    is_available = data.get("paddleocr_available", False)
                    if is_available:
                        logger.info("✅ PaddleOCR service is available and ready")
                    else:
                        logger.warning(
                            "⚠️ PaddleOCR service responded but paddleocr_available=False"
                        )
                    return is_available
                logger.warning(f"⚠️ PaddleOCR service returned status {response.status_code}")
                logger.warning(f"⚠️ Response content: {response.text[:200]}")
                return False

        except httpx.ConnectError as e:
            logger.error(f"❌ Cannot connect to PaddleOCR service: {str(e)}")
            logger.error(f"❌ Connection error type: {type(e).__name__}")
            logger.error(f"❌ Full error details: {repr(e)}")
        except httpx.TimeoutException:
            logger.error("❌ PaddleOCR service timeout (10s)")
        except Exception as e:
            logger.error(f"❌ PaddleOCR health check failed: {str(e)}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            logger.error(f"❌ Full error details: {repr(e)}")
        return False

    def get_available_engines(self) -> dict[str, dict[str, Any]]:
        """Get comprehensive information about all OCR engines and their availability.

        Checks real-time availability of each engine by testing connections
        (PaddleOCR microservice health check, Vision LLM client validation).
        Returns detailed specifications including speed, accuracy, and cost.

        Returns:
            dict[str, dict[str, Any]]: Dictionary mapping engine names to capabilities:
                - engine (str): Engine enum value
                - name (str): Human-readable name
                - description (str): Detailed description
                - speed (str): Performance characteristics
                - accuracy (str): Quality level (Excellent, Good)
                - available (bool): Real-time availability status
                - cost (str): Pricing information
                - configuration (Dict): Current engine-specific settings

        Example:
            >>> manager = OCREngineManager(db_session)
            >>> engines = manager.get_available_engines()
            >>> for name, info in engines.items():
            ...     print(f"{name}: {'✅' if info['available'] else '❌'}")
            ...     print(f"  Speed: {info['speed']}")
            ...     print(f"  Cost: {info['cost']}")
            PADDLEOCR: ✅
              Speed: Fast (~2-5s per page)
              Cost: Free (CPU-based microservice)
            VISION_LLM: ✅
              Speed: Slow (~2 minutes per page)
              Cost: OVH AI Endpoints pricing
            HYBRID: ✅
              Speed: Variable
              Cost: Variable

        Note:
            Availability checks are synchronous and may add latency. Use sparingly
            in request paths. Consider caching results for frequent queries.
        """
        # Safely check Vision LLM availability
        vision_available = False
        try:
            vision_available = (
                hasattr(self.hybrid_extractor, "ovh_client")
                and self.hybrid_extractor.ovh_client is not None
                and hasattr(self.hybrid_extractor.ovh_client, "vision_client")
                and self.hybrid_extractor.ovh_client.vision_client is not None
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not check Vision LLM availability: {e}")
            vision_available = False

        # Check PaddleOCR service availability (synchronous check)
        paddleocr_available = self._check_paddleocr_health_sync()

        return {
            "PADDLEOCR": {
                "engine": "PADDLEOCR",
                "name": "PP-StructureV3",
                "description": "Document parsing with table/chart recognition, Markdown output",
                "speed": "Fast (~3-10s per page)",
                "accuracy": "Excellent",
                "available": paddleocr_available,
                "cost": "Free (CPU-based microservice)",
                "configuration": self.get_engine_config(OCREngineEnum.PADDLEOCR),
            },
            "VISION_LLM": {
                "engine": "VISION_LLM",
                "name": "Qwen 2.5 VL (Vision LLM)",
                "description": "AI-powered OCR for highly complex documents",
                "speed": "Slow (~2 minutes per page)",
                "accuracy": "Excellent",
                "available": vision_available,
                "cost": "OVH AI Endpoints pricing",
                "configuration": self.get_engine_config(OCREngineEnum.VISION_LLM),
            },
            "HYBRID": {
                "engine": "HYBRID",
                "name": "Hybrid (Intelligent Routing)",
                "description": "Automatically selects best OCR based on document quality",
                "speed": "Variable",
                "accuracy": "Optimal",
                "available": True,
                "cost": "Variable",
                "configuration": self.get_engine_config(OCREngineEnum.HYBRID),
            },
        }

    def get_engine_status(self, engine: OCREngineEnum) -> dict[str, Any]:
        """
        Get detailed status of a specific OCR engine.

        Args:
            engine: OCR engine to check

        Returns:
            Dict with engine status information
        """
        engines_info = self.get_available_engines()
        engine_info = engines_info.get(engine.value, {})

        config = self.get_engine_config(engine)

        return {
            "engine": engine.value,
            "available": engine_info.get("available", False),
            "description": engine_info.get("description", ""),
            "speed": engine_info.get("speed", "Unknown"),
            "accuracy": engine_info.get("accuracy", "Unknown"),
            "cost": engine_info.get("cost", "Unknown"),
            "configuration": config,
        }
