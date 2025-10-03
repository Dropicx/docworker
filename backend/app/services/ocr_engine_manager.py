"""
OCR Engine Manager

Worker-ready service for managing OCR engine selection and configuration.
Supports multiple OCR engines based on database configuration.
"""

import logging
import json
import os
import httpx
from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import OCRConfigurationDB, OCREngineEnum
from app.services.hybrid_text_extractor import HybridTextExtractor

logger = logging.getLogger(__name__)


def _normalize_paddleocr_url(url: str) -> str:
    """
    Normalize PaddleOCR service URL to handle IPv6 and missing scheme.

    Railway provides IPv6 addresses that need brackets in URLs.
    Also ensures http:// prefix is present.
    """
    if not url:
        return "http://paddleocr.railway.internal:9123"

    # Add http:// if missing
    if not url.startswith(('http://', 'https://')):
        url = f"http://{url}"

    # Check if we have a bare IPv6 address (contains : but not wrapped in [])
    # Format: http://ipv6:port needs to become http://[ipv6]:port
    if url.startswith('http://') and ':' in url:
        # Extract the part after http://
        rest = url[7:]  # Remove 'http://'

        # Check if it's IPv6 (multiple colons and not already bracketed)
        if rest.count(':') > 1 and not rest.startswith('['):
            # Split on last colon to separate address from port
            parts = rest.rsplit(':', 1)
            if len(parts) == 2:
                ipv6_addr, port = parts
                # Rebuild with brackets around IPv6
                url = f"http://[{ipv6_addr}]:{port}"
                logger.info(f"🔧 Normalized IPv6 URL to: {url}")

    return url


# PaddleOCR microservice URL (Railway internal networking)
_raw_url = os.getenv(
    "PADDLEOCR_SERVICE_URL",
    "http://paddleocr.railway.internal:9123"
)
PADDLEOCR_SERVICE_URL = _normalize_paddleocr_url(_raw_url)

# Log the URL being used at startup
logger.info(f"🔗 PaddleOCR service URL: {PADDLEOCR_SERVICE_URL}")


class OCREngineManager:
    """
    Manages OCR engine selection and execution based on database configuration.

    Supported Engines:
    - TESSERACT: Local Tesseract OCR (fast, good for clean documents)
    - PADDLEOCR: GPU-based OCR (future: 30x faster than Vision LLM)
    - VISION_LLM: Qwen 2.5 VL (slow but accurate for complex documents)
    - HYBRID: Intelligent routing based on document quality
    """

    def __init__(self, session: Session):
        """
        Initialize OCR Engine Manager.

        Args:
            session: SQLAlchemy session for database access
        """
        self.session = session
        self.hybrid_extractor = HybridTextExtractor()

    # ==================== CONFIGURATION ====================

    def load_ocr_config(self) -> Optional[OCRConfigurationDB]:
        """
        Load OCR configuration from database.

        Returns:
            OCR configuration or None if not found
        """
        try:
            config = self.session.query(OCRConfigurationDB).first()
            if config:
                logger.info(f"🔍 Loaded OCR config: {config.selected_engine}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load OCR config: {e}")
            return None

    def get_engine_config(self, engine: OCREngineEnum) -> Dict[str, Any]:
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
            OCREngineEnum.TESSERACT: config.tesseract_config,
            OCREngineEnum.PADDLEOCR: config.paddleocr_config,
            OCREngineEnum.VISION_LLM: config.vision_llm_config,
            OCREngineEnum.HYBRID: config.hybrid_config
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
        override_engine: Optional[OCREngineEnum] = None
    ) -> Tuple[str, float]:
        """
        Extract text from document using configured OCR engine.

        Args:
            file_content: File content as bytes
            file_type: File type ('pdf', 'jpg', 'png', etc.)
            filename: Original filename
            override_engine: Optional engine override (for testing)

        Returns:
            Tuple of (extracted_text: str, confidence: float)
        """
        # Determine which engine to use
        config = self.load_ocr_config()
        selected_engine = override_engine or (config.selected_engine if config else OCREngineEnum.HYBRID)

        logger.info(f"🔍 Starting OCR with engine: {selected_engine}")

        try:
            if selected_engine == OCREngineEnum.HYBRID:
                # Use hybrid extractor (current production system)
                return await self._extract_with_hybrid(file_content, file_type, filename)

            elif selected_engine == OCREngineEnum.TESSERACT:
                # Force Tesseract OCR
                return await self._extract_with_tesseract(file_content, file_type, filename)

            elif selected_engine == OCREngineEnum.VISION_LLM:
                # Force Vision LLM
                return await self._extract_with_vision_llm(file_content, file_type, filename)

            elif selected_engine == OCREngineEnum.PADDLEOCR:
                # PaddleOCR (future implementation)
                return await self._extract_with_paddleocr(file_content, file_type, filename)

            else:
                logger.warning(f"⚠️ Unknown engine {selected_engine}, falling back to HYBRID")
                return await self._extract_with_hybrid(file_content, file_type, filename)

        except Exception as e:
            logger.error(f"❌ OCR extraction failed: {e}")
            return f"OCR extraction error: {str(e)}", 0.0

    # ==================== ENGINE-SPECIFIC EXTRACTION ====================

    async def _extract_with_hybrid(
        self,
        file_content: bytes,
        file_type: str,
        filename: str
    ) -> Tuple[str, float]:
        """
        Extract text using hybrid strategy (intelligent routing).

        This is the current production system that automatically selects
        the best OCR method based on document quality analysis.
        """
        logger.info("🎯 Using HYBRID extraction (intelligent routing)")
        return await self.hybrid_extractor.extract_text(file_content, file_type, filename)

    async def _extract_with_tesseract(
        self,
        file_content: bytes,
        file_type: str,
        filename: str
    ) -> Tuple[str, float]:
        """
        Extract text using Tesseract OCR.

        Fast and good for clean, simple documents.
        """
        logger.info("📝 Using TESSERACT extraction")

        # Get Tesseract configuration
        tesseract_config = self.get_engine_config(OCREngineEnum.TESSERACT)

        # Use hybrid extractor's local OCR method
        if not self.hybrid_extractor.local_ocr_available:
            logger.warning("⚠️ Tesseract not available, falling back to hybrid")
            return await self._extract_with_hybrid(file_content, file_type, filename)

        try:
            return await self.hybrid_extractor._extract_with_local_ocr(
                file_content, file_type, tesseract_config
            )
        except Exception as e:
            logger.error(f"❌ Tesseract extraction failed: {e}")
            logger.info("🔄 Falling back to hybrid extraction")
            return await self._extract_with_hybrid(file_content, file_type, filename)

    async def _extract_with_vision_llm(
        self,
        file_content: bytes,
        file_type: str,
        filename: str
    ) -> Tuple[str, float]:
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
        self,
        file_content: bytes,
        file_type: str,
        filename: str
    ) -> Tuple[str, float]:
        """
        Extract text using PaddleOCR microservice.

        Calls the separate PaddleOCR service via HTTP.
        Falls back to hybrid extraction on failure.
        """
        logger.info(f"🤖 Calling PaddleOCR microservice at {PADDLEOCR_SERVICE_URL}")

        try:
            # Check if PaddleOCR service is available
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Prepare multipart form data
                files = {
                    'file': (filename, file_content, f'image/{file_type}')
                }

                # Call PaddleOCR microservice
                response = await client.post(
                    f"{PADDLEOCR_SERVICE_URL}/extract",
                    files=files
                )

                if response.status_code == 200:
                    result = response.json()
                    extracted_text = result.get('text', '')
                    confidence = result.get('confidence', 0.0)
                    processing_time = result.get('processing_time', 0.0)

                    logger.info(f"✅ PaddleOCR extraction completed in {processing_time:.2f}s")
                    logger.info(f"📊 Confidence: {confidence:.2%}, Length: {len(extracted_text)} chars")

                    return extracted_text, confidence

                else:
                    logger.error(f"❌ PaddleOCR service error: {response.status_code}")
                    raise Exception(f"PaddleOCR service returned {response.status_code}")

        except httpx.TimeoutException:
            logger.error("❌ PaddleOCR service timeout (60s)")
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
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{PADDLEOCR_SERVICE_URL}/health")
                if response.status_code == 200:
                    data = response.json()
                    is_available = data.get("paddleocr_available", False)
                    if is_available:
                        logger.info(f"✅ PaddleOCR service is available")
                    else:
                        logger.warning(f"⚠️ PaddleOCR service responded but paddleocr_available=False")
                    return is_available
                else:
                    logger.warning(f"⚠️ PaddleOCR service returned status {response.status_code}")
                    return False
        except httpx.ConnectError as e:
            logger.warning(f"⚠️ Cannot connect to PaddleOCR service: {str(e)}")
        except httpx.TimeoutException:
            logger.warning(f"⚠️ PaddleOCR service timeout (5s)")
        except Exception as e:
            logger.warning(f"⚠️ PaddleOCR health check failed: {str(e)}")
        return False

    def get_available_engines(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about available OCR engines.

        Returns:
            Dict mapping engine names to their capabilities
        """
        # Safely check Vision LLM availability
        vision_available = False
        try:
            vision_available = (
                hasattr(self.hybrid_extractor, 'ovh_client') and
                self.hybrid_extractor.ovh_client is not None and
                hasattr(self.hybrid_extractor.ovh_client, 'vision_client') and
                self.hybrid_extractor.ovh_client.vision_client is not None
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not check Vision LLM availability: {e}")
            vision_available = False

        # Check PaddleOCR service availability (synchronous check)
        paddleocr_available = self._check_paddleocr_health_sync()

        return {
            "TESSERACT": {
                "engine": "TESSERACT",
                "name": "Tesseract OCR",
                "description": "Fast local OCR for clean documents",
                "speed": "Fast (< 5s per page)",
                "accuracy": "Good for clean text",
                "available": self.hybrid_extractor.local_ocr_available,
                "cost": "Free",
                "configuration": self.get_engine_config(OCREngineEnum.TESSERACT)
            },
            "PADDLEOCR": {
                "engine": "PADDLEOCR",
                "name": "PaddleOCR",
                "description": "CPU-based OCR for complex documents",
                "speed": "Fast (~2-5s per page)",
                "accuracy": "Excellent",
                "available": paddleocr_available,
                "cost": "Free (CPU-based microservice)",
                "configuration": self.get_engine_config(OCREngineEnum.PADDLEOCR)
            },
            "VISION_LLM": {
                "engine": "VISION_LLM",
                "name": "Qwen 2.5 VL (Vision LLM)",
                "description": "AI-powered OCR for highly complex documents",
                "speed": "Slow (~2 minutes per page)",
                "accuracy": "Excellent",
                "available": vision_available,
                "cost": "OVH AI Endpoints pricing",
                "configuration": self.get_engine_config(OCREngineEnum.VISION_LLM)
            },
            "HYBRID": {
                "engine": "HYBRID",
                "name": "Hybrid (Intelligent Routing)",
                "description": "Automatically selects best OCR based on document quality",
                "speed": "Variable",
                "accuracy": "Optimal",
                "available": True,
                "cost": "Variable",
                "configuration": self.get_engine_config(OCREngineEnum.HYBRID)
            }
        }

    def get_engine_status(self, engine: OCREngineEnum) -> Dict[str, Any]:
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
            "configuration": config
        }
