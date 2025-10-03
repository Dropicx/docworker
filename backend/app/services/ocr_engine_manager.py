"""
OCR Engine Manager

Worker-ready service for managing OCR engine selection and configuration.
Supports multiple OCR engines based on database configuration.
"""

import logging
import json
from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import OCRConfigurationDB, OCREngineEnum
from app.services.hybrid_text_extractor import HybridTextExtractor

logger = logging.getLogger(__name__)


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
        Extract text using PaddleOCR (GPU-based).

        Future implementation - 30x faster than Vision LLM.
        Currently falls back to hybrid extraction.
        """
        logger.warning("⚠️ PaddleOCR not yet implemented")
        logger.info("🔄 Falling back to hybrid extraction")
        return await self._extract_with_hybrid(file_content, file_type, filename)

        # Future PaddleOCR implementation:
        # try:
        #     from paddleocr import PaddleOCR
        #     paddleocr_config = self.get_engine_config(OCREngineEnum.PADDLEOCR)
        #
        #     ocr = PaddleOCR(
        #         use_angle_cls=True,
        #         lang=paddleocr_config.get('lang', 'german'),
        #         use_gpu=paddleocr_config.get('use_gpu', True)
        #     )
        #
        #     # Process image/PDF
        #     result = ocr.ocr(file_content, cls=True)
        #
        #     # Extract text from result
        #     text = '\n'.join([line[1][0] for line in result[0]])
        #     confidence = sum([line[1][1] for line in result[0]]) / len(result[0])
        #
        #     return text, confidence
        # except Exception as e:
        #     logger.error(f"❌ PaddleOCR extraction failed: {e}")
        #     return await self._extract_with_hybrid(file_content, file_type, filename)

    # ==================== UTILITY METHODS ====================

    def get_available_engines(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about available OCR engines.

        Returns:
            Dict mapping engine names to their capabilities
        """
        return {
            "TESSERACT": {
                "name": "Tesseract OCR",
                "description": "Fast local OCR for clean documents",
                "speed": "Fast (< 5s per page)",
                "accuracy": "Good for clean text",
                "available": self.hybrid_extractor.local_ocr_available,
                "cost": "Free"
            },
            "PADDLEOCR": {
                "name": "PaddleOCR",
                "description": "GPU-accelerated OCR for complex documents",
                "speed": "Very Fast (~2s per page)",
                "accuracy": "Excellent",
                "available": False,  # Not yet implemented
                "cost": "Free (requires GPU)"
            },
            "VISION_LLM": {
                "name": "Qwen 2.5 VL (Vision LLM)",
                "description": "AI-powered OCR for highly complex documents",
                "speed": "Slow (~2 minutes per page)",
                "accuracy": "Excellent",
                "available": self.hybrid_extractor.ovh_client.vision_client is not None,
                "cost": "OVH AI Endpoints pricing"
            },
            "HYBRID": {
                "name": "Hybrid (Intelligent Routing)",
                "description": "Automatically selects best OCR based on document quality",
                "speed": "Variable",
                "accuracy": "Optimal",
                "available": True,
                "cost": "Variable"
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
