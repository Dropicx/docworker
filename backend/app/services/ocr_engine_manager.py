"""
OCR Engine Manager

Simplified OCR service with two engines:
1. Mistral OCR (primary) - Fast, accurate document OCR
2. PaddleOCR Hetzner (fallback) - External service via EXTERNAL_OCR_URL
"""

import base64
from io import BytesIO
import logging
import os
import time
from typing import Any

import httpx
from pdf2image import convert_from_bytes
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import OCRConfigurationDB, OCREngineEnum
from app.models.ocr_result import OCRResult
from app.repositories.ocr_configuration_repository import OCRConfigurationRepository

logger = logging.getLogger(__name__)

# External PaddleOCR service configuration (Hetzner deployment)
EXTERNAL_OCR_URL = os.getenv("EXTERNAL_OCR_URL", "")
EXTERNAL_API_KEY = os.getenv("EXTERNAL_API_KEY", "")

if EXTERNAL_OCR_URL:
    logger.info(f"🌐 PaddleOCR URL configured: {EXTERNAL_OCR_URL}")
    logger.info(f"🔑 PaddleOCR API key: {'configured' if EXTERNAL_API_KEY else 'not set'}")

# Mistral OCR configuration
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
if MISTRAL_API_KEY:
    logger.info("🔮 Mistral OCR API key configured")


class OCREngineManager:
    """Simplified OCR engine manager with Mistral (primary) and PaddleOCR (fallback).

    Two-engine setup:
    - MISTRAL_OCR: Primary engine, fast and accurate
    - PADDLEOCR: Fallback via Hetzner (EXTERNAL_OCR_URL)

    Fallback Strategy:
        Mistral OCR failure → PaddleOCR Hetzner → Error

    Example:
        >>> manager = OCREngineManager(db_session)
        >>> result = await manager.extract_text(
        ...     file_content=pdf_bytes,
        ...     file_type="pdf",
        ...     filename="document.pdf"
        ... )
    """

    def __init__(
        self, session: Session, config_repository: OCRConfigurationRepository | None = None
    ) -> None:
        """Initialize OCR Engine Manager.

        Args:
            session: SQLAlchemy session
            config_repository: OCR configuration repository
        """
        self.session = session
        self.config_repository = config_repository or OCRConfigurationRepository(session)

    # ==================== CONFIGURATION ====================

    def load_ocr_config(self) -> OCRConfigurationDB | None:
        """Load OCR configuration from database."""
        try:
            config = self.config_repository.get_config()
            if config:
                logger.info(f"🔍 Loaded OCR config: {config.selected_engine}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load OCR config: {e}")
            return None

    def get_engine_config(self, engine: OCREngineEnum) -> dict[str, Any]:
        """Get configuration for specific OCR engine."""
        config = self.load_ocr_config()
        if not config:
            return {}

        config_map = {
            OCREngineEnum.MISTRAL_OCR: config.mistral_ocr_config,
            OCREngineEnum.PADDLEOCR: config.paddleocr_config,
        }

        engine_config = config_map.get(engine)
        return engine_config or {}

    # ==================== OCR EXECUTION ====================

    async def extract_text(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        override_engine: OCREngineEnum | None = None,
    ) -> OCRResult:
        """Extract text from document using configured OCR engine.

        Args:
            file_content: Document content as bytes
            file_type: File type ('pdf', 'jpg', 'png')
            filename: Original filename
            override_engine: Optional engine override

        Returns:
            OCRResult with extracted text, confidence, and metadata
        """
        config = self.load_ocr_config()
        selected_engine = override_engine or (
            config.selected_engine if config else OCREngineEnum.MISTRAL_OCR
        )

        logger.info(f"🔍 Starting OCR with engine: {selected_engine}")

        try:
            if selected_engine == OCREngineEnum.MISTRAL_OCR:
                return await self._extract_with_mistral_ocr(file_content, file_type, filename)

            if selected_engine == OCREngineEnum.PADDLEOCR:
                return await self._extract_with_paddleocr(file_content, file_type, filename)

            # Default to Mistral
            logger.warning(f"⚠️ Unknown engine {selected_engine}, using Mistral OCR")
            return await self._extract_with_mistral_ocr(file_content, file_type, filename)

        except Exception as e:
            logger.error(f"❌ OCR extraction failed: {e}")
            return OCRResult(
                text=f"OCR extraction error: {str(e)}", confidence=0.0, engine=str(selected_engine)
            )

    async def extract_text_legacy(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        override_engine: OCREngineEnum | None = None,
    ) -> tuple[str, float]:
        """Legacy method returning tuple for backward compatibility."""
        result = await self.extract_text(file_content, file_type, filename, override_engine)
        return result.text, result.confidence

    # ==================== MISTRAL OCR ====================

    async def _extract_with_mistral_ocr(
        self, file_content: bytes, file_type: str, filename: str
    ) -> OCRResult:
        """Extract text using Mistral OCR API (primary engine).

        Falls back to PaddleOCR on failure.
        """
        from mistralai import Mistral

        logger.info("🔮 Using MISTRAL_OCR extraction")
        logger.info(f"📄 File: {filename}, Type: {file_type}, Size: {len(file_content)} bytes")

        if not MISTRAL_API_KEY:
            logger.warning("⚠️ MISTRAL_API_KEY not set, falling back to PaddleOCR")
            return await self._extract_with_paddleocr(file_content, file_type, filename)

        start_time = time.time()

        try:
            client = Mistral(api_key=MISTRAL_API_KEY)
            all_markdown = []

            if file_type.lower() == "pdf":
                logger.info("📄 Converting PDF pages to images for Mistral OCR...")

                try:
                    images = convert_from_bytes(file_content, dpi=200, fmt="png")
                    logger.info(f"📄 Converted PDF to {len(images)} page images")
                except Exception as e:
                    logger.error(f"❌ PDF to image conversion failed: {e}")
                    return await self._extract_with_paddleocr(file_content, file_type, filename)

                for page_num, image in enumerate(images, 1):
                    logger.info(f"📤 Processing page {page_num}/{len(images)} with Mistral OCR...")

                    img_buffer = BytesIO()
                    image.save(img_buffer, format="PNG")
                    img_bytes = img_buffer.getvalue()
                    b64_content = base64.b64encode(img_bytes).decode("utf-8")
                    data_url = f"data:image/png;base64,{b64_content}"

                    ocr_response = client.ocr.process(
                        model="mistral-ocr-latest",
                        document={"type": "image_url", "image_url": {"url": data_url}},
                        include_image_base64=False,
                    )

                    for page in ocr_response.pages:
                        if page.markdown:
                            all_markdown.append(page.markdown)
            else:
                # For images, send directly
                if file_type.lower() in ("jpg", "jpeg"):
                    mime_type = "image/jpeg"
                elif file_type.lower() == "png":
                    mime_type = "image/png"
                else:
                    mime_type = f"image/{file_type.lower()}"

                b64_content = base64.b64encode(file_content).decode("utf-8")
                data_url = f"data:{mime_type};base64,{b64_content}"

                logger.info("📤 Calling Mistral OCR API")

                ocr_response = client.ocr.process(
                    model="mistral-ocr-latest",
                    document={"type": "image_url", "image_url": {"url": data_url}},
                    include_image_base64=False,
                )

                for page in ocr_response.pages:
                    if page.markdown:
                        all_markdown.append(page.markdown)

            extracted_text = "\n\n---\n\n".join(all_markdown)
            processing_time = time.time() - start_time

            logger.info(f"✅ Mistral OCR completed in {processing_time:.2f}s")
            logger.info(f"📊 Pages: {len(all_markdown)}, Length: {len(extracted_text)} chars")

            return OCRResult(
                text=extracted_text,
                confidence=0.95,
                markdown=extracted_text,
                processing_time=processing_time,
                engine="MISTRAL_OCR",
                mode="mistral",
            )

        except Exception as e:
            logger.error(f"❌ Mistral OCR failed: {e}")
            logger.info("🔄 Falling back to PaddleOCR")
            return await self._extract_with_paddleocr(file_content, file_type, filename)

    # ==================== PADDLEOCR (HETZNER) ====================

    async def _extract_with_paddleocr(
        self, file_content: bytes, file_type: str, filename: str
    ) -> OCRResult:
        """Extract text using PaddleOCR via Hetzner (fallback engine).

        Uses EXTERNAL_OCR_URL and EXTERNAL_API_KEY environment variables.
        """
        if not EXTERNAL_OCR_URL:
            logger.error("❌ EXTERNAL_OCR_URL not configured")
            return OCRResult(
                text="OCR service not configured. Set EXTERNAL_OCR_URL.",
                confidence=0.0,
                engine="PADDLEOCR",
            )

        logger.info(f"🌐 Using PaddleOCR at {EXTERNAL_OCR_URL}")
        logger.info(f"📄 File: {filename}, Type: {file_type}, Size: {len(file_content)} bytes")

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                mime_type = (
                    "application/pdf" if file_type.lower() == "pdf" else f"image/{file_type}"
                )
                files = {"file": (filename, file_content, mime_type)}

                headers = {}
                if EXTERNAL_API_KEY:
                    headers["X-API-Key"] = EXTERNAL_API_KEY

                response = await client.post(
                    f"{EXTERNAL_OCR_URL}/extract", files=files, headers=headers
                )

                if response.status_code == 200:
                    result = response.json()

                    extracted_text = result.get("text", "")
                    confidence = result.get("confidence", 0.0)
                    processing_time = result.get("processing_time", time.time() - start_time)
                    engine = result.get("engine", "PaddleOCR")

                    logger.info(f"✅ PaddleOCR completed in {processing_time:.2f}s")
                    logger.info(
                        f"📊 Confidence: {confidence:.2%}, Length: {len(extracted_text)} chars"
                    )

                    return OCRResult(
                        text=extracted_text,
                        confidence=confidence,
                        processing_time=processing_time,
                        engine=engine,
                        mode="paddleocr",
                    )

                if response.status_code in (401, 403):
                    logger.error(f"❌ PaddleOCR authentication failed: {response.status_code}")
                    return OCRResult(
                        text="PaddleOCR authentication failed. Check EXTERNAL_API_KEY.",
                        confidence=0.0,
                        engine="PADDLEOCR",
                    )
                logger.error(f"❌ PaddleOCR service error: {response.status_code}")
                return OCRResult(
                    text=f"PaddleOCR service error: {response.status_code}",
                    confidence=0.0,
                    engine="PADDLEOCR",
                )

        except httpx.TimeoutException:
            logger.error("❌ PaddleOCR service timeout")
            return OCRResult(text="PaddleOCR service timeout", confidence=0.0, engine="PADDLEOCR")

        except httpx.ConnectError as e:
            logger.error(f"❌ Cannot connect to PaddleOCR: {e}")
            return OCRResult(
                text=f"Cannot connect to PaddleOCR service: {e}", confidence=0.0, engine="PADDLEOCR"
            )

        except Exception as e:
            logger.error(f"❌ PaddleOCR extraction failed: {e}")
            return OCRResult(text=f"PaddleOCR error: {e}", confidence=0.0, engine="PADDLEOCR")

    # ==================== UTILITY METHODS ====================

    async def check_paddleocr_health(self) -> bool:
        """Check if PaddleOCR service is available (async)."""
        if not EXTERNAL_OCR_URL:
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{EXTERNAL_OCR_URL}/health")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("paddleocr_available", False) or data.get("status") == "healthy"
        except Exception as e:
            logger.debug(f"PaddleOCR health check failed: {e}")
        return False

    def _check_paddleocr_health_sync(self) -> bool:
        """Check if PaddleOCR service is available (sync)."""
        if not EXTERNAL_OCR_URL:
            return False

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{EXTERNAL_OCR_URL}/health")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("paddleocr_available", False) or data.get("status") == "healthy"
        except Exception as e:
            logger.debug(f"PaddleOCR health check failed: {e}")
        return False

    def get_available_engines(self) -> dict[str, dict[str, Any]]:
        """Get information about available OCR engines."""
        paddleocr_available = self._check_paddleocr_health_sync()

        return {
            "MISTRAL_OCR": {
                "engine": "MISTRAL_OCR",
                "name": "Mistral OCR",
                "description": "Fast, accurate document OCR with markdown output",
                "speed": "Fast (~2-5s per page)",
                "accuracy": "Excellent",
                "available": bool(MISTRAL_API_KEY),
                "cost": "Mistral API pricing",
                "configuration": self.get_engine_config(OCREngineEnum.MISTRAL_OCR),
            },
            "PADDLEOCR": {
                "engine": "PADDLEOCR",
                "name": "PaddleOCR (Hetzner)",
                "description": "CPU-based OCR via external Hetzner service",
                "speed": "Fast (~3-10s per page)",
                "accuracy": "Excellent",
                "available": paddleocr_available,
                "cost": "Self-hosted (Hetzner ~€36/mo)",
                "configuration": self.get_engine_config(OCREngineEnum.PADDLEOCR),
            },
        }

    def get_engine_status(self, engine: OCREngineEnum) -> dict[str, Any]:
        """Get detailed status of a specific OCR engine."""
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
