"""
OCR Engine Manager

Worker-ready service for managing OCR engine selection and configuration.
Supports multiple OCR engines based on database configuration.
"""

import base64
import json
import logging
import os
import re
from io import BytesIO
from typing import Any

import httpx
from pdf2image import convert_from_bytes
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import OCRConfigurationDB, OCREngineEnum
from app.models.ocr_result import OCRResult
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
    ) -> OCRResult:
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
            OCRResult: Complete OCR result containing:
                - text: Extracted text with preserved formatting
                - confidence: Score (0.0-1.0) based on OCR quality
                - markdown: Markdown-formatted text (if available)
                - structured_output: PP-StructureV3 JSON with tables/pages
                - processing_time: Time taken for extraction
                - engine: OCR engine used

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
            return OCRResult(
                text=f"OCR extraction error: {str(e)}",
                confidence=0.0,
                engine=str(selected_engine)
            )

    async def extract_text_legacy(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        override_engine: OCREngineEnum | None = None,
    ) -> tuple[str, float]:
        """Legacy method returning only text and confidence for backward compatibility.

        Use extract_text() for full OCRResult with structured_output.
        """
        result = await self.extract_text(file_content, file_type, filename, override_engine)
        return result.text, result.confidence

    # ==================== ENGINE-SPECIFIC EXTRACTION ====================

    async def _extract_with_hybrid(
        self, file_content: bytes, file_type: str, filename: str
    ) -> OCRResult:
        """
        Extract text using hybrid strategy (intelligent routing).

        This is the current production system that automatically selects
        the best OCR method based on document quality analysis.
        Note: Hybrid extractor returns legacy tuple, wrap in OCRResult.
        """
        logger.info("🎯 Using HYBRID extraction (intelligent routing)")
        text, confidence = await self.hybrid_extractor.extract_text(file_content, file_type, filename)
        return OCRResult(
            text=text,
            confidence=confidence,
            engine="HYBRID",
            mode="hybrid"
        )

    async def _extract_with_vision_llm(
        self, file_content: bytes, file_type: str, filename: str
    ) -> OCRResult:
        """
        Extract text using Vision Language Model (Qwen 2.5 VL).

        Slow (~2 minutes/page) but very accurate for complex documents.
        """
        logger.info("🤖 Using VISION_LLM extraction")

        # Get Vision LLM configuration
        vision_config = self.get_engine_config(OCREngineEnum.VISION_LLM)

        try:
            text, confidence = await self.hybrid_extractor._extract_with_vision_llm(
                file_content, file_type, vision_config
            )
            return OCRResult(
                text=text,
                confidence=confidence,
                engine="VISION_LLM",
                mode="vision"
            )
        except Exception as e:
            logger.error(f"❌ Vision LLM extraction failed: {e}")
            logger.info("🔄 Falling back to hybrid extraction")
            return await self._extract_with_hybrid(file_content, file_type, filename)

    async def _extract_with_paddleocr(
        self, file_content: bytes, file_type: str, filename: str
    ) -> OCRResult:
        """
        Extract text using PaddleOCR services.

        Priority (fallback chain):
        1. External PaddleOCR (Hetzner/GPU) - if USE_EXTERNAL_OCR=true
        2. Railway internal PaddleOCR (CPU)
        3. Hybrid extraction (final fallback)

        Calls services via HTTP with structured mode for Markdown/JSON output.
        Returns OCRResult with structured_output for semantic table processing.
        """
        # Try external Hetzner OCR if configured
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
    ) -> OCRResult:
        """
        Extract text using external PaddleOCR service (Hetzner/external deployment).

        Uses API key authentication via X-API-Key header.
        Returns OCRResult with structured_output for semantic table processing.
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

                # Capture structured_output for semantic table processing
                structured_output = result.get("structured_output")
                markdown = result.get("markdown")

                logger.info(f"✅ External {engine} extraction completed in {processing_time:.2f}s (mode: {mode})")
                logger.info(f"📊 Confidence: {confidence:.2%}, Length: {len(extracted_text)} chars")

                if markdown:
                    logger.info("📝 Using Markdown output (structured)")
                if structured_output:
                    logger.info(f"📊 Captured structured_output with {len(structured_output.get('pages', []))} pages")

                return OCRResult(
                    text=extracted_text,
                    confidence=confidence,
                    markdown=markdown,
                    structured_output=structured_output,
                    processing_time=processing_time,
                    engine=engine,
                    mode=mode
                )

            elif response.status_code in (401, 403):
                logger.error(f"❌ External OCR authentication failed: {response.status_code}")
                raise Exception(f"External OCR authentication failed: {response.status_code}")
            else:
                logger.error(f"❌ External OCR service error: {response.status_code}")
                raise Exception(f"External OCR service returned {response.status_code}")

    def _convert_pipe_tables_to_markdown(self, text: str) -> str:
        """
        Convert pipe-delimited table rows from PaddleOCR-VL to proper markdown tables.

        Input:  "Header1 | Header2 | Header3\\nVal1 | Val2 | Val3"
        Output: "| Header1 | Header2 | Header3 |\\n|---------|---------|---------|\\n| Val1 | Val2 | Val3 |"
        """
        lines = text.split('\n')
        result_lines = []
        in_table = False
        table_lines = []

        for line in lines:
            # Check if line looks like a table row (has | separators and multiple columns)
            stripped = line.strip()
            if ' | ' in stripped and stripped.count('|') >= 1:
                # Looks like a table row
                if not in_table:
                    in_table = True
                    table_lines = []
                table_lines.append(stripped)
            else:
                # Not a table row
                if in_table and table_lines:
                    # End of table - convert accumulated table lines
                    result_lines.extend(self._format_markdown_table(table_lines))
                    table_lines = []
                    in_table = False
                result_lines.append(line)

        # Handle table at end of text
        if in_table and table_lines:
            result_lines.extend(self._format_markdown_table(table_lines))

        return '\n'.join(result_lines)

    def _format_markdown_table(self, table_lines: list[str]) -> list[str]:
        """Convert list of pipe-delimited rows to markdown table format."""
        if not table_lines:
            return []

        result = []
        for i, line in enumerate(table_lines):
            # Ensure line starts and ends with |
            if not line.startswith('|'):
                line = '| ' + line
            if not line.endswith('|'):
                line = line + ' |'
            result.append(line)

            # Add separator row after first row (header)
            if i == 0:
                # Count columns
                cols = line.count('|') - 1
                separator = '|' + '|'.join(['---'] * cols) + '|'
                result.append(separator)

        return result

    def _normalize_line_breaks(self, text: str) -> str:
        """
        Normalize line breaks by joining paragraph lines while preserving structure.

        OCR output often has line breaks after every visual line on the page.
        This method joins lines that belong to the same paragraph while keeping
        intentional breaks for headings, lists, tables, and page separators.

        Approach: Join lines UNLESS there's a clear structural boundary.
        Works with German text where nouns are capitalized mid-sentence.

        Preserves line breaks:
        - After headings (lines ending with :)
        - Before/after numbered items (1., 2., etc.)
        - Before/after bullet points (·, -, ∞, •, o)
        - Around tables (lines with | or markdown table format)
        - Around page separators (---)
        - After complete sentences (ends with . ! ?)
        - Empty lines (paragraph breaks)
        - Short standalone lines (< 30 chars, likely headers)
        """
        lines = text.split('\n')
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Skip empty lines - they mark paragraph breaks
            if not stripped:
                result.append('')
                i += 1
                continue

            # Check if this line is a clear block boundary (should NOT be joined)
            # Bullet point check: "o " or "· " etc, but NOT "o.B." (German abbreviation)
            is_bullet = (
                len(stripped) > 1 and
                stripped[0] in '·∞•' and stripped[1] == ' '
            ) or (
                # "o text" style bullet (but not "o.B." abbreviation)
                len(stripped) > 2 and
                stripped[0] == 'o' and stripped[1] == ' '
            ) or (
                # "- text" bullet (but not negative numbers like "-5")
                len(stripped) > 2 and
                stripped[0] == '-' and stripped[1] == ' '
            )

            # Document header elements that should stay on separate lines
            is_header_element = (
                # German greeting
                'Sehr geehrt' in stripped or
                # Date of birth
                'geb. am' in stripped or
                'geb.am' in stripped or
                # Address indicators (German street types)
                bool(re.search(r'\b(Straße|Strasse|Weg|Platz|Allee|Ring|Gasse)\b', stripped, re.IGNORECASE)) or
                # Postal code pattern (5 digits followed by city, or masked XXXXX)
                bool(re.search(r'\b(\d{5}|XXXXX|xxxxx)\s+[A-ZÄÖÜa-zäöü]', stripped)) or
                # Date pattern at end of line (DD.MM.YYYY or XX.XX.XXXX masked)
                bool(re.search(r'[\dXx]{2}\.[\dXx]{2}\.[\dXx]{4}\s*$', stripped)) or
                # Doctor titles / signatures
                bool(re.match(r'^Dr\.?\s*(med\.?)?', stripped, re.IGNORECASE)) or
                # Fax/Tel patterns
                bool(re.search(r'\b(Fax|Tel|Telefon)\b', stripped, re.IGNORECASE))
            )

            is_block_end = (
                # Page separator
                stripped == '---' or
                # Heading (ends with :)
                stripped.endswith(':') or
                # Table row (has | separators)
                '|' in stripped or
                # Complete sentence (ends with terminal punctuation)
                stripped[-1] in '.!?' or
                # Numbered list item
                bool(re.match(r'^\d+[\.\)]\s', stripped)) or
                # Bullet point
                is_bullet or
                # Document header element (address, date, greeting, etc.)
                is_header_element or
                # Very short line (likely header/label, not wrapped text)
                len(stripped) < 30
            )

            # Check if next line starts a new block
            has_next = i + 1 < len(lines)
            next_line = lines[i + 1].strip() if has_next else ''

            # Check if next line is a bullet point
            next_is_bullet = next_line and (
                (len(next_line) > 1 and next_line[0] in '·∞•' and next_line[1] == ' ') or
                (len(next_line) > 2 and next_line[0] == 'o' and next_line[1] == ' ') or
                (len(next_line) > 2 and next_line[0] == '-' and next_line[1] == ' ')
            )

            next_is_block_start = (
                # Empty line (paragraph break)
                not next_line or
                # Page separator
                next_line == '---' or
                # Numbered list item
                bool(re.match(r'^\d+[\.\)]\s', next_line)) or
                # Bullet point
                next_is_bullet or
                # Table row
                '|' in next_line or
                # Starts with special characters (except letters/numbers)
                (next_line and not next_line[0].isalnum())
            )

            # Join if no structural boundary detected
            should_join = (
                not is_block_end and
                has_next and
                not next_is_block_start
            )

            if should_join:
                # Join with next line (same paragraph)
                joined = stripped + ' ' + next_line
                lines[i + 1] = joined
                i += 1
            else:
                result.append(line)
                i += 1

        return '\n'.join(result)

    async def _extract_with_internal_paddleocr(
        self, file_content: bytes, file_type: str, filename: str
    ) -> OCRResult:
        """
        Extract text using internal PaddleOCR microservice (Railway deployment).

        Returns OCRResult with structured_output for semantic table processing.
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

                    # Capture structured_output for semantic table processing
                    structured_output = result.get("structured_output")
                    markdown = result.get("markdown")

                    logger.info(f"✅ {engine} extraction completed in {processing_time:.2f}s (mode: {mode})")
                    logger.info(
                        f"📊 Confidence: {confidence:.2%}, Length: {len(extracted_text)} chars"
                    )

                    # Log if we got markdown or structured output
                    if markdown:
                        logger.info("📝 Using Markdown output (structured)")
                    if structured_output:
                        pages = structured_output.get("pages", [])
                        logger.info(f"📊 Captured structured_output with {len(pages)} pages")

                    return OCRResult(
                        text=extracted_text,
                        confidence=confidence,
                        markdown=markdown,
                        structured_output=structured_output,
                        processing_time=processing_time,
                        engine=engine,
                        mode=mode
                    )

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
