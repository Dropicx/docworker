"""
Hybrid Text Extractor with Conditional OCR Logic
Intelligently routes between local text extraction, local OCR, and Vision LLM OCR
"""

from io import BytesIO
import logging
from typing import Any

import pdfplumber
from PIL import Image
import pypdf as PyPDF2

from app.services.file_quality_detector import (
    DocumentComplexity,
    ExtractionStrategy,
    FileQualityDetector,
)
from app.services.file_sequence_detector import FileSequenceDetector
from app.services.ovh_client import OVHClient

# Optional imports for local OCR (fallback gracefully if not available)
try:
    from app.services.text_extractor_ocr import TextExtractorWithOCR

    LOCAL_OCR_AVAILABLE = True
except ImportError:
    LOCAL_OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


class HybridTextExtractor:
    """Intelligent text extractor with adaptive strategy selection.

    This extractor analyzes documents and intelligently selects the optimal
    extraction method: LOCAL_TEXT (fast PDF parsing), LOCAL_OCR (Tesseract),
    VISION_LLM (AI-powered), or HYBRID (combined approach).

    Attributes:
        quality_detector (FileQualityDetector): Analyzes file quality and recommends strategy
        ovh_client (OVHClient): Client for Vision LLM processing
        sequence_detector (FileSequenceDetector): Detects logical order of multi-file documents
        local_ocr_available (bool): Whether Tesseract OCR is available
        local_ocr (TextExtractorWithOCR | None): Local OCR implementation if available

    Example:
        >>> extractor = HybridTextExtractor()
        >>> text, confidence = await extractor.extract_text(
        ...     file_content=pdf_bytes,
        ...     file_type="pdf",
        ...     filename="medical_report.pdf"
        ... )
        >>> print(f"Extracted {len(text)} characters with {confidence:.1%} confidence")
    """

    def __init__(self) -> None:
        # Initialize components
        self.quality_detector = FileQualityDetector()
        self.ovh_client = OVHClient()
        self.sequence_detector = FileSequenceDetector()

        # Initialize local OCR if available (legacy fallback - PaddleOCR is primary)
        self.local_ocr_available = LOCAL_OCR_AVAILABLE
        if self.local_ocr_available:
            try:
                self.local_ocr = TextExtractorWithOCR()
                logger.debug("✅ Local OCR (Tesseract) available as fallback")
            except Exception as e:
                logger.debug(f"⚠️ Local OCR initialization failed: {e}")
                self.local_ocr = None
                self.local_ocr_available = False
        else:
            self.local_ocr = None
            logger.debug("ℹ️ Local OCR not available, using PaddleOCR microservice")

        logger.debug("🚀 Hybrid Text Extractor initialized")
        logger.debug("   - Quality Detector: ✅")
        logger.debug("   - Sequence Detector: ✅")
        logger.debug(f"   - OVH Vision: {'✅' if self.ovh_client.vision_client else '❌'}")
        logger.debug(f"   - Local OCR: {'✅' if self.local_ocr_available else '❌'}")

    async def _apply_ocr_preprocessing(self, raw_text: str) -> str:
        """
        OCR preprocessing temporarily disabled to prevent content truncation.
        The enhanced Vision LLM prompt already provides clean, well-formatted text.
        """
        logger.debug("ℹ️ OCR preprocessing skipped - Vision LLM provides pre-formatted text")
        return raw_text

    async def extract_text(
        self, file_content: bytes, file_type: str, filename: str
    ) -> tuple[str, float]:
        """Extract text from a single file using optimal strategy.

        Analyzes the file to determine the best extraction method (LOCAL_TEXT,
        LOCAL_OCR, VISION_LLM, or HYBRID), then extracts text accordingly.
        Falls back to Vision LLM if local methods fail.

        Args:
            file_content: Raw file content as bytes
            file_type: File type identifier ('pdf', 'image', 'jpg', 'png')
            filename: Original filename for logging and analysis

        Returns:
            Tuple containing:
                - str: Extracted text content
                - float: Confidence score (0.0 to 1.0)

        Raises:
            Exception: Returns error message in tuple if extraction fails

        Example:
            >>> extractor = HybridTextExtractor()
            >>> text, conf = await extractor.extract_text(
            ...     file_content=pdf_bytes,
            ...     file_type="pdf",
            ...     filename="lab_results.pdf"
            ... )
            >>> if conf > 0.8:
            ...     print(f"High confidence extraction: {len(text)} chars")
        """
        logger.info(f"📄 Starting hybrid extraction for: {filename}")

        try:
            # Step 1: Analyze file to determine strategy
            strategy, complexity, analysis = await self.quality_detector.analyze_file(
                file_content, file_type, filename
            )

            logger.info(f"🎯 Strategy selected: {strategy.value} (complexity: {complexity.value})")

            # Step 2: Extract text using the determined strategy
            if strategy == ExtractionStrategy.LOCAL_TEXT:
                return await self._extract_with_local_text(file_content, file_type, analysis)

            if strategy == ExtractionStrategy.LOCAL_OCR:
                return await self._extract_with_local_ocr(file_content, file_type, analysis)

            if strategy == ExtractionStrategy.VISION_LLM:
                return await self._extract_with_vision_llm(file_content, file_type, analysis)

            if strategy == ExtractionStrategy.HYBRID:
                return await self._extract_with_hybrid(file_content, file_type, analysis)

            # Fallback to vision LLM
            logger.warning(f"⚠️ Unknown strategy {strategy}, falling back to vision LLM")
            return await self._extract_with_vision_llm(file_content, file_type, analysis)

        except Exception as e:
            logger.error(f"❌ Hybrid extraction failed for {filename}: {e}")
            return f"Hybrid extraction error: {str(e)}", 0.0

    async def extract_from_multiple_files(
        self, files: list[tuple[bytes, str, str]], merge_strategy: str = "smart"
    ) -> tuple[str, float]:
        """Extract and intelligently merge text from multiple related files.

        Processes multi-page medical documents by:
        1. Detecting logical page sequence (e.g., "page1.jpg", "page2.jpg")
        2. Analyzing all files to determine optimal extraction strategy
        3. Extracting text from each file using the same strategy
        4. Intelligently merging results based on medical document structure

        Args:
            files: List of tuples, each containing:
                - bytes: File content
                - str: File type ('pdf', 'image', 'jpg', 'png')
                - str: Filename
            merge_strategy: Merge approach, either:
                - "smart": Context-aware merging with medical structure detection
                - "sequential": Simple sequential concatenation with separators

        Returns:
            Tuple containing:
                - str: Merged text content from all files
                - float: Average confidence score across all files (0.0 to 1.0)

        Example:
            >>> extractor = HybridTextExtractor()
            >>> files = [
            ...     (page1_bytes, "image", "scan_page1.jpg"),
            ...     (page2_bytes, "image", "scan_page2.jpg"),
            ...     (page3_bytes, "image", "scan_page3.jpg")
            ... ]
            >>> merged_text, avg_conf = await extractor.extract_from_multiple_files(
            ...     files=files,
            ...     merge_strategy="smart"
            ... )
            >>> print(f"Merged {len(files)} pages: {len(merged_text)} chars")
        """
        if not files:
            return "No files provided", 0.0

        logger.info(f"📚 Starting multi-file extraction: {len(files)} files")

        try:
            # Step 1: Detect logical sequence of files
            logger.info("🔍 Detecting file sequence...")
            ordered_files = await self.sequence_detector.detect_sequence(files)

            # Log sequence detection results
            if ordered_files != files:
                original_names = [f[2] for f in files]
                ordered_names = [f[2] for f in ordered_files]
                logger.info("📄 File sequence reordered:")
                logger.info(f"   Original: {original_names}")
                logger.info(f"   Ordered:  {ordered_names}")
            else:
                logger.info("📄 Files already in logical order")

            # Step 2: Analyze all files to determine consolidated strategy
            consolidated_analysis = await self.quality_detector.analyze_multiple_files(
                ordered_files
            )

            strategy = ExtractionStrategy(consolidated_analysis["recommended_strategy"])
            complexity = DocumentComplexity(consolidated_analysis["recommended_complexity"])

            logger.info(
                f"🎯 Multi-file strategy: {strategy.value} (complexity: {complexity.value})"
            )

            # Step 3: Extract text from each file using the same strategy for consistency
            extraction_results = []
            total_confidence = 0.0

            for i, (content, file_type, filename) in enumerate(ordered_files, 1):
                logger.info(f"📄 Processing file {i}/{len(files)}: {filename}")

                # Use the consolidated strategy for all files
                if strategy == ExtractionStrategy.LOCAL_TEXT:
                    text, confidence = await self._extract_with_local_text(content, file_type, {})
                elif strategy == ExtractionStrategy.LOCAL_OCR:
                    text, confidence = await self._extract_with_local_ocr(content, file_type, {})
                elif strategy == ExtractionStrategy.VISION_LLM:
                    text, confidence = await self._extract_with_vision_llm(content, file_type, {})
                else:
                    text, confidence = await self._extract_with_vision_llm(content, file_type, {})

                if text and not text.startswith("Error"):
                    extraction_results.append(
                        {
                            "filename": filename,
                            "text": text,
                            "confidence": confidence,
                            "file_index": i,
                        }
                    )
                    total_confidence += confidence
                    logger.info(
                        f"✅ File {i} processed: {len(text)} chars, confidence: {confidence:.2%}"
                    )
                else:
                    logger.warning(f"⚠️ File {i} failed: {text}")

            if not extraction_results:
                return "Failed to extract text from any file", 0.0

            # Step 4: Merge results intelligently
            merged_text = self._merge_extraction_results(extraction_results, merge_strategy)
            avg_confidence = total_confidence / len(extraction_results)

            logger.info("🎯 Multi-file extraction complete:")
            logger.info(f"   - Files processed: {len(extraction_results)}/{len(files)}")
            logger.info(f"   - Total characters: {len(merged_text)}")
            logger.info(f"   - Average confidence: {avg_confidence:.2%}")

            return merged_text, avg_confidence

        except Exception as e:
            logger.error(f"❌ Multi-file extraction failed: {e}")
            return f"Multi-file extraction error: {str(e)}", 0.0

    async def _extract_with_local_text(
        self, content: bytes, file_type: str, analysis: dict[str, Any]
    ) -> tuple[str, float]:
        """Extract text using local PDF parsing (no OCR).

        Uses pdfplumber (preferred) and PyPDF2 (fallback) to extract text
        from PDF files. Best for PDFs with selectable text. Falls back to
        Vision LLM if quality is insufficient.

        Args:
            content: PDF file content as bytes
            file_type: Must be "pdf" (falls back to Vision LLM otherwise)
            analysis: File analysis metadata from quality detector

        Returns:
            Tuple of (extracted_text, confidence_score)
        """

        if file_type != "pdf":
            logger.warning(
                "⚠️ Local text extraction only works with PDFs, falling back to vision LLM"
            )
            return await self._extract_with_vision_llm(content, file_type, analysis)

        try:
            logger.info("📖 Extracting with local PDF text extraction (cost-optimized)")

            # Try pdfplumber first - better for tables
            text = await self._extract_pdf_with_pdfplumber(content)

            # Quality check for local extraction
            if text and len(text.strip()) > 50:
                # Check if the text looks reasonable
                confidence = self._evaluate_local_extraction_quality(text)

                if confidence >= 0.7:  # Good quality local extraction
                    logger.info(
                        f"✅ pdfplumber successful: {len(text)} characters, confidence: {confidence:.2%}"
                    )
                    return text.strip(), confidence
                logger.info(
                    f"⚠️ pdfplumber low quality (confidence: {confidence:.2%}), trying PyPDF2"
                )

            # Fallback to PyPDF2
            text = await self._extract_pdf_with_pypdf2(content)

            if text and len(text.strip()) > 50:
                confidence = self._evaluate_local_extraction_quality(text)

                if confidence >= 0.6:  # Reasonable quality
                    logger.info(
                        f"✅ PyPDF2 successful: {len(text)} characters, confidence: {confidence:.2%}"
                    )
                    return text.strip(), confidence
                logger.info(
                    f"⚠️ PyPDF2 low quality (confidence: {confidence:.2%}), falling back to vision LLM"
                )

            # If local extraction quality is poor, fallback to vision LLM
            logger.warning(
                "⚠️ Local text extraction quality insufficient, falling back to vision LLM"
            )
            return await self._extract_with_vision_llm(content, file_type, analysis)

        except Exception as e:
            logger.error(f"❌ Local text extraction failed: {e}")
            return await self._extract_with_vision_llm(content, file_type, analysis)

    def _evaluate_local_extraction_quality(self, text: str) -> float:
        """Evaluate the quality of locally extracted text"""
        if not text or len(text.strip()) < 20:
            return 0.0

        confidence = 0.5  # Base confidence

        # Length indicators (longer text usually means better extraction)
        if len(text) > 200:
            confidence += 0.1
        if len(text) > 1000:
            confidence += 0.1

        # Medical content indicators
        medical_terms = [
            "patient",
            "arzt",
            "diagnose",
            "behandlung",
            "medizin",
            "befund",
            "labor",
            "wert",
            "normal",
            "untersuchung",
            "datum",
            "geburtsdatum",
            "versicherung",
        ]

        text_lower = text.lower()
        found_medical_terms = sum(1 for term in medical_terms if term in text_lower)
        confidence += min(found_medical_terms * 0.02, 0.1)

        # Structure indicators (proper sentences, punctuation)
        import re

        sentences = len(re.findall(r"[.!?]+", text))
        if sentences > 5:
            confidence += 0.05
        if sentences > 15:
            confidence += 0.05

        # Check for garbage characters (indicates poor extraction)
        garbage_patterns = ["���", "□", "▢", "※", "◦"]
        has_garbage = any(pattern in text for pattern in garbage_patterns)
        if has_garbage:
            confidence -= 0.2

        # Check for reasonable word structure
        words = text.split()
        if len(words) > 20:
            confidence += 0.05

            # Average word length should be reasonable (2-15 characters)
            avg_word_length = sum(len(word) for word in words[:50]) / min(50, len(words))
            if 3 <= avg_word_length <= 12:
                confidence += 0.05

        # Check for medical numbers and units (lab values, measurements)
        medical_numbers = re.findall(r"\d+[.,]?\d*\s*(mg|ml|mmol|µg|ng|u/l|iu/l|%|cm|kg)", text)
        if len(medical_numbers) > 0:
            confidence += min(len(medical_numbers) * 0.01, 0.1)

        return min(confidence, 0.95)  # Cap at 95%

    async def _extract_pdf_with_pdfplumber(self, content: bytes) -> str | None:
        """Extract text using pdfplumber with enhanced table handling"""
        try:
            pdf_file = BytesIO(content)
            text_parts = []

            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_content = []

                    # First, try to extract tables
                    tables = page.find_tables()

                    if tables:
                        logger.debug(f"📊 Found {len(tables)} tables on page {page_num}")

                        # Extract text outside tables first
                        page_text = page.extract_text()
                        if page_text:
                            page_content.append(page_text)

                        # Then add table data
                        for i, table in enumerate(tables):
                            try:
                                table_data = table.extract()
                                if table_data:
                                    # Format table as markdown-like structure
                                    table_text = f"\n--- Tabelle {i + 1} ---\n"
                                    for row in table_data:
                                        if row and any(
                                            cell for cell in row if cell
                                        ):  # Skip empty rows
                                            # Join non-empty cells with " | "
                                            cells = [
                                                str(cell).strip() if cell else "" for cell in row
                                            ]
                                            table_text += " | ".join(cells) + "\n"

                                    page_content.append(table_text)
                            except Exception as e:
                                logger.debug(f"Table extraction error on page {page_num}: {e}")

                    else:
                        # No tables found, extract text normally
                        page_text = page.extract_text()
                        if page_text:
                            page_content.append(page_text)

                    if page_content:
                        combined_content = "\n".join(page_content)
                        text_parts.append(f"--- Seite {page_num} ---\n{combined_content}")

            return "\n\n".join(text_parts) if text_parts else None

        except Exception as e:
            logger.debug(f"pdfplumber extraction failed: {e}")
            return None

    async def _extract_pdf_with_pypdf2(self, content: bytes) -> str | None:
        """Extract text using PyPDF2"""
        try:
            pdf_file = BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text_parts = []

            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Seite {page_num} ---\n{page_text}")

            return "\n\n".join(text_parts) if text_parts else None

        except Exception as e:
            logger.debug(f"PyPDF2 extraction failed: {e}")
            return None

    async def _extract_with_local_ocr(
        self, content: bytes, file_type: str, analysis: dict[str, Any]
    ) -> tuple[str, float]:
        """Extract text using local OCR (Tesseract)"""

        if not self.local_ocr_available or not self.local_ocr:
            logger.warning("⚠️ Local OCR not available, falling back to vision LLM")
            return await self._extract_with_vision_llm(content, file_type, analysis)

        try:
            logger.info("🔍 Extracting with local OCR (Tesseract)")

            # Use the existing local OCR implementation
            text, confidence = await self.local_ocr.extract_text(content, file_type, "temp_file")

            if text and len(text.strip()) > 20 and not text.startswith("Error"):
                logger.info(
                    f"✅ Local OCR successful: {len(text)} characters, confidence: {confidence:.2%}"
                )
                # Apply OCR preprocessing using unified prompt system
                processed_text = await self._apply_ocr_preprocessing(text)
                return processed_text, confidence
            logger.warning(
                "⚠️ Local OCR failed or returned poor results, falling back to vision LLM"
            )
            return await self._extract_with_vision_llm(content, file_type, analysis)

        except Exception as e:
            logger.error(f"❌ Local OCR failed: {e}")
            return await self._extract_with_vision_llm(content, file_type, analysis)

    async def _extract_with_vision_llm(
        self, content: bytes, file_type: str, analysis: dict[str, Any]
    ) -> tuple[str, float]:
        """Extract text using Vision LLM (Qwen 2.5 VL)"""

        try:
            logger.info("🤖 Extracting with Vision LLM (Qwen 2.5 VL)")

            if file_type == "pdf":
                # Convert PDF to images first
                try:
                    from pdf2image import convert_from_bytes

                    # Convert PDF to images
                    logger.info("🔄 Converting PDF to images for vision processing")
                    images = convert_from_bytes(content, dpi=300)

                    if images:
                        # Process multiple images
                        pil_images = list(images)
                        text, confidence = await self.ovh_client.process_multiple_images_ocr(
                            pil_images, merge_strategy="smart"
                        )

                        if text and len(text.strip()) > 20 and not text.startswith("Error"):
                            logger.info(
                                f"✅ Vision LLM PDF processing successful: {len(text)} characters"
                            )
                            # Apply OCR preprocessing using unified prompt system
                            processed_text = await self._apply_ocr_preprocessing(text)
                            return processed_text, confidence
                        return "Vision LLM konnte keinen Text aus dem PDF extrahieren.", 0.1

                except ImportError:
                    logger.error("❌ pdf2image not available for PDF to image conversion")
                    return "PDF-zu-Bild-Konvertierung nicht verfügbar.", 0.0

            elif file_type == "image":
                # Process image directly
                image = Image.open(BytesIO(content))
                text, confidence = await self.ovh_client.extract_text_with_vision(image, file_type)

                if text and len(text.strip()) > 10 and not text.startswith("Error"):
                    logger.info(
                        f"✅ Vision LLM image processing successful: {len(text)} characters"
                    )
                    # Apply OCR preprocessing using unified prompt system
                    processed_text = await self._apply_ocr_preprocessing(text)
                    return processed_text, confidence
                return "Vision LLM konnte keinen Text aus dem Bild extrahieren.", 0.1

            else:
                return f"Nicht unterstützter Dateityp für Vision LLM: {file_type}", 0.0

        except Exception as e:
            logger.error(f"❌ Vision LLM extraction failed: {e}")
            return f"Vision LLM Fehler: {str(e)}", 0.0

    async def _extract_with_hybrid(
        self, content: bytes, file_type: str, analysis: dict[str, Any]
    ) -> tuple[str, float]:
        """Extract text using a hybrid approach"""

        logger.info("🔄 Using hybrid extraction approach")

        # Try local methods first, then vision LLM as fallback
        try:
            # First attempt: Local text/OCR
            if file_type == "pdf":
                text, confidence = await self._extract_with_local_text(content, file_type, analysis)
            else:
                text, confidence = await self._extract_with_local_ocr(content, file_type, analysis)

            # If local method succeeded with good confidence, use it
            if confidence >= 0.7 and len(text.strip()) > 100:
                logger.info(f"✅ Hybrid: Local method successful (confidence: {confidence:.2%})")
                return text, confidence

            # Otherwise, try vision LLM
            logger.info("⚠️ Hybrid: Local method insufficient, trying vision LLM")
            vision_text, vision_confidence = await self._extract_with_vision_llm(
                content, file_type, analysis
            )

            # Compare results and choose the best one
            if vision_confidence > confidence:
                logger.info(f"✅ Hybrid: Vision LLM better (confidence: {vision_confidence:.2%})")
                return vision_text, vision_confidence
            logger.info(f"✅ Hybrid: Local method better (confidence: {confidence:.2%})")
            return text, confidence

        except Exception as e:
            logger.error(f"❌ Hybrid extraction failed: {e}")
            return f"Hybrid extraction error: {str(e)}", 0.0

    def _merge_extraction_results(
        self, results: list[dict[str, Any]], strategy: str = "smart"
    ) -> str:
        """
        Merge extraction results from multiple files

        Args:
            results: List of extraction results with text, confidence, filename
            strategy: Merge strategy ("sequential", "smart")

        Returns:
            Merged text
        """
        if not results:
            return ""

        if len(results) == 1:
            return results[0]["text"]

        logger.info(f"🔧 Merging {len(results)} extraction results using '{strategy}' strategy")

        if strategy == "sequential":
            return self._merge_sequential(results)
        if strategy == "smart":
            return self._merge_smart(results)
        return self._merge_sequential(results)

    def _merge_sequential(self, results: list[dict[str, Any]]) -> str:
        """Merge results in sequential order with clear page separators"""
        merged_parts = []

        for result in sorted(results, key=lambda x: x["file_index"]):
            filename = result["filename"]
            text = result["text"]

            # Add file header
            merged_parts.append(f"=== {filename} ===")
            merged_parts.append(text)
            merged_parts.append("")  # Empty line between files

        return "\n".join(merged_parts)

    def _merge_smart(self, results: list[dict[str, Any]]) -> str:
        """Intelligently merge results with context awareness and medical structure"""
        if len(results) == 1:
            return results[0]["text"]

        logger.info(f"🧠 Smart merging {len(results)} extraction results")

        merged_parts = []
        previous_section_type = None

        for i, result in enumerate(sorted(results, key=lambda x: x["file_index"])):
            text = result["text"].strip()
            filename = result["filename"]

            # Analyze current text to understand its medical content type
            current_section_type = self._identify_medical_section_type(text)

            if i == 0:
                # First file - add as is with potential header
                if current_section_type in ["patient_info", "header"]:
                    merged_parts.append(text)
                else:
                    # Add a document header if first page doesn't have one
                    merged_parts.append(f"# Medizinische Dokumentation\n\n{text}")

                logger.info(f"📄 File {i + 1}: Started document (type: {current_section_type})")
            else:
                # Subsequent files - intelligent merging
                prev_text = merged_parts[-1] if merged_parts else ""

                if self._should_merge_seamlessly(
                    prev_text, text, previous_section_type, current_section_type
                ):
                    # Seamless continuation
                    merged_parts.append(f"\n{text}")
                    logger.info(f"📄 File {i + 1}: Seamless merge (type: {current_section_type})")

                elif self._is_table_continuation(prev_text, text):
                    # Table continuation - preserve structure
                    merged_parts.append(f"\n{text}")
                    logger.info(f"📄 File {i + 1}: Table continuation")

                elif current_section_type == "lab_values" and previous_section_type in [
                    "lab_values",
                    "examination",
                ]:
                    # Lab values continuation
                    merged_parts.append(f"\n## Laborwerte (Fortsetzung)\n\n{text}")
                    logger.info(f"📄 File {i + 1}: Lab values continuation")

                else:
                    # New section - add appropriate header
                    section_header = self._get_section_header(current_section_type, filename)
                    merged_parts.append(f"\n{section_header}\n\n{text}")
                    logger.info(f"📄 File {i + 1}: New section (type: {current_section_type})")

            previous_section_type = current_section_type

        # Post-process the merged text
        final_text = "\n".join(merged_parts)
        final_text = self._post_process_merged_text(final_text)

        logger.info(f"✅ Smart merge complete: {len(final_text)} characters")
        return final_text

    def _identify_medical_section_type(self, text: str) -> str:
        """Identify the type of medical section from text content"""
        text_lower = text.lower()

        # Patient information patterns
        if any(
            pattern in text_lower
            for pattern in ["patient", "name:", "geburtsdatum", "versicherten"]
        ):
            return "patient_info"

        # Lab values patterns
        if any(
            pattern in text_lower
            for pattern in ["laborwerte", "blutwerte", "mg/dl", "mmol/l", "referenzbereich"]
        ):
            return "lab_values"

        # Diagnosis patterns
        if any(pattern in text_lower for pattern in ["diagnose", "befund", "beurteilung", "icd"]):
            return "diagnosis"

        # Medication patterns
        if any(
            pattern in text_lower
            for pattern in ["medikation", "therapie", "einnahme", "mg täglich"]
        ):
            return "medication"

        # Header/title patterns
        if any(
            pattern in text_lower
            for pattern in ["arztbrief", "entlassungsbrief", "klinik", "krankenhaus"]
        ):
            return "header"

        # Examination patterns
        if any(
            pattern in text_lower
            for pattern in ["untersuchung", "röntgen", "mrt", "ct", "ultraschall"]
        ):
            return "examination"

        return "general"

    def _should_merge_seamlessly(
        self, prev_text: str, current_text: str, prev_section: str, current_section: str
    ) -> bool:
        """Determine if texts should be merged seamlessly without headers"""

        # Same section type - likely continuation
        if prev_section == current_section and prev_section != "general":
            return True

        # Check for explicit continuation indicators
        if self._is_likely_continuation(prev_text, current_text):
            return True

        # Patient info continuing to examination/diagnosis
        if prev_section == "patient_info" and current_section in ["examination", "diagnosis"]:
            return True

        # Examination continuing to lab values
        return bool(prev_section == "examination" and current_section == "lab_values")

    def _is_table_continuation(self, prev_text: str, current_text: str) -> bool:
        """Check if current text continues a table from previous text"""

        # Check if previous text ends with table indicators
        prev_lines = prev_text.strip().split("\n")[-3:]  # Last 3 lines
        current_lines = current_text.strip().split("\n")[:3]  # First 3 lines

        # Look for table patterns (pipes, tabs, aligned columns)
        prev_has_table = any("|" in line or "\t" in line for line in prev_lines)
        current_has_table = any("|" in line or "\t" in line for line in current_lines)

        # If both have table indicators, likely continuation
        if prev_has_table and current_has_table:
            return True

        # Check for numeric patterns (lab values)
        import re

        prev_has_numbers = any(
            re.search(r"\d+[.,]\d*\s*(mg|ml|mmol|µg|ng|u/l)", line) for line in prev_lines
        )
        current_has_numbers = any(
            re.search(r"\d+[.,]\d*\s*(mg|ml|mmol|µg|ng|u/l)", line) for line in current_lines
        )

        return prev_has_numbers and current_has_numbers

    def _get_section_header(self, section_type: str, filename: str) -> str:
        """Get appropriate section header based on content type"""

        headers = {
            "patient_info": "## Patienteninformationen",
            "lab_values": "## Laborwerte",
            "diagnosis": "## Diagnosen und Befunde",
            "medication": "## Medikation und Therapie",
            "examination": "## Untersuchungsergebnisse",
            "header": "## Dokumentenkopf",
            "general": f"## {filename}",
        }

        return headers.get(section_type, f"## {filename}")

    def _post_process_merged_text(self, text: str) -> str:
        """Post-process merged text for better readability"""

        # Remove excessive blank lines
        import re

        text = re.sub(r"\n{4,}", "\n\n\n", text)

        # Fix spacing around headers
        text = re.sub(r"\n(##[^\n]+)\n{1,2}", r"\n\n\1\n\n", text)

        # Ensure proper spacing before new sections
        text = re.sub(r"([^\n])\n(##)", r"\1\n\n\2", text)

        # Clean up redundant section headers
        text = re.sub(r"(##[^\n]+)\n+\1", r"\1", text)

        return text.strip()

    def _is_likely_continuation(self, prev_text: str, current_text: str) -> bool:
        """Determine if current text is likely a continuation of previous text"""

        if not prev_text or not current_text:
            return False

        # Check if previous text ends with continuation indicators
        prev_endings = prev_text.rstrip().lower()
        continuation_indicators = [
            ",",
            "-",
            "und",
            "oder",
            "sowie",
            "mit",
            "bei",
            "für",
            "siehe",
            "fortsetzung",
            "weiter",
            "nächste seite",
        ]

        for indicator in continuation_indicators:
            if prev_endings.endswith(indicator):
                return True

        # Check if current text starts with continuation indicators
        current_start = current_text.lstrip().lower()
        start_indicators = [
            "fortsetzung",
            "weiter",
            "- ",
            "• ",
            "und ",
            "oder ",
            "sowie ",
            "außerdem",
            "darüber hinaus",
        ]

        for indicator in start_indicators:
            if current_start.startswith(indicator):
                return True

        # Check for numbered lists continuation
        import re

        if re.match(r"^\s*\d+[.)]\s", current_text):
            # Current starts with number - check if previous had numbers
            if re.search(r"\d+[.)]\s", prev_text):
                return True

        return False


# Factory function for backward compatibility
def get_hybrid_text_extractor():
    """Factory function to get hybrid text extractor instance"""
    return HybridTextExtractor()
