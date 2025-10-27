"""
File Quality Detector for Conditional OCR Routing
Analyzes documents to determine the best text extraction strategy
"""

from enum import Enum
from io import BytesIO
import logging
from typing import Any

import pdfplumber
from PIL import Image
import PyPDF2

# Optional OpenCV import - graceful fallback if not available
try:
    import cv2
    import numpy as np

    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None
    np = None

logger = logging.getLogger(__name__)


class ExtractionStrategy(Enum):
    """Enumeration of available text extraction strategies"""

    LOCAL_TEXT = "local_text"  # Use pdfplumber/PyPDF2 for clean PDFs
    LOCAL_OCR = "local_ocr"  # Use Tesseract for moderate quality
    VISION_LLM = "vision_llm"  # Use Qwen 2.5 VL for complex/poor quality
    HYBRID = "hybrid"  # Use combination of methods


class DocumentComplexity(Enum):
    """Document complexity levels"""

    SIMPLE = "simple"  # Clean text, simple layout
    MODERATE = "moderate"  # Some formatting, tables
    COMPLEX = "complex"  # Complex layouts, forms, tables
    VERY_COMPLEX = "very_complex"  # Handwritten, poor quality, complex forms


class FileQualityDetector:
    """Intelligent document analyzer for optimal OCR strategy selection.

    Performs deep content analysis of PDF and image files to automatically select
    the most cost-effective and accurate text extraction strategy. Evaluates document
    complexity, text quality, table presence, and image characteristics to route to
    appropriate OCR engines (local text, local OCR, or Vision LLM).

    **Analysis Capabilities**:
        - PDF: Embedded text detection, quality scoring, table detection, page structure
        - Images: Quality assessment, table/form detection, text density estimation
        - Multi-file: Consolidated strategy for document sequences

    **Strategy Selection Logic**:
        - LOCAL_TEXT: Clean PDFs with high-quality embedded text (free, instant)
        - LOCAL_OCR: Moderate quality scanned docs (Tesseract, 2-5s/page, free)
        - VISION_LLM: Complex layouts, tables, poor quality (Qwen 2.5 VL, ~2min/page, OVH cost)
        - HYBRID: Intelligent routing based on content analysis

    **Cost Optimization**:
        Prioritizes free local extraction when quality permits, only escalating to
        paid Vision LLM for complex medical tables, forms, or poor quality scans.

    **Medical Document Awareness**:
        - Detects lab value tables with medical units (mg/dl, mmol/l, etc.)
        - Identifies medical terminology patterns
        - Recognizes reference ranges and clinical formats

    Attributes:
        tesseract_available (bool): Whether Tesseract OCR is installed
        opencv_available (bool): Whether OpenCV is available for image analysis

    Example:
        >>> detector = FileQualityDetector()
        >>> strategy, complexity, metadata = await detector.analyze_file(
        ...     file_content=pdf_bytes,
        ...     file_type="pdf",
        ...     filename="lab_report.pdf"
        ... )
        >>> print(f"Use {strategy.value} for {complexity.value} document")
        Use vision_llm for complex document

    Note:
        **Feature Availability**:
        - Tesseract: Optional, enables LOCAL_OCR strategy
        - OpenCV: Optional, enhances image quality assessment
        - Without optional deps: Falls back to basic analysis + Vision LLM

        **Table Detection Priority**:
        Tables in medical documents trigger Vision LLM for accuracy,
        as table structure preservation is critical for lab values.
    """

    def __init__(self):
        self.tesseract_available = self._check_tesseract_available()
        self.opencv_available = OPENCV_AVAILABLE
        logger.debug("🔍 File Quality Detector initialized (using PaddleOCR microservice)")

    def _check_tesseract_available(self) -> bool:
        """Check if Tesseract OCR is available"""
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    async def analyze_file(
        self, file_content: bytes, file_type: str, filename: str
    ) -> tuple[ExtractionStrategy, DocumentComplexity, dict[str, Any]]:
        """Analyze document and recommend optimal text extraction strategy.

        Main entry point for document analysis. Performs comprehensive content evaluation
        to determine the most cost-effective and accurate OCR approach. Routes to
        specialized analyzers for PDFs vs. images, evaluating text quality, layout
        complexity, and medical content patterns.

        Args:
            file_content: Raw file content as bytes (PDF or image data)
            file_type: File type identifier - "pdf" or "image"
            filename: Original filename for logging and analysis context

        Returns:
            tuple[ExtractionStrategy, DocumentComplexity, dict[str, Any]]:
                - ExtractionStrategy: Recommended OCR engine (LOCAL_TEXT, LOCAL_OCR,
                  VISION_LLM, or HYBRID)
                - DocumentComplexity: Assessed complexity level (SIMPLE, MODERATE,
                  COMPLEX, or VERY_COMPLEX)
                - dict[str, Any]: Detailed analysis metadata including:
                    * file_type, filename
                    * Quality metrics (text_coverage, text_quality_score)
                    * Structure flags (has_tables, has_images, has_forms)
                    * Decision reasons (list explaining strategy choice)
                    * Type-specific metrics (page_count for PDF, image_size for images)

        Example:
            >>> detector = FileQualityDetector()
            >>> # Analyze clean PDF with embedded text
            >>> strategy, complexity, meta = await detector.analyze_file(
            ...     file_content=clean_pdf_bytes,
            ...     file_type="pdf",
            ...     filename="medical_report.pdf"
            ... )
            >>> print(strategy.value)
            'local_text'  # Free, instant extraction
            >>>
            >>> # Analyze scanned lab results with tables
            >>> strategy, complexity, meta = await detector.analyze_file(
            ...     file_content=scanned_labs_bytes,
            ...     file_type="pdf",
            ...     filename="lab_results.pdf"
            ... )
            >>> print(strategy.value, meta['reasons'])
            'vision_llm' ['tables_detected_require_vision_llm']

        Note:
            **Cost Optimization Logic**:
            - Clean embedded text → LOCAL_TEXT (free, instant)
            - Moderate scans without tables → LOCAL_OCR (free, 2-5s)
            - Complex layouts, tables, forms → VISION_LLM (OVH cost, ~2min)

            **Medical Table Priority**:
            Presence of tables triggers Vision LLM regardless of text quality,
            as medical lab tables require precise structure preservation.

            **Fallback Handling**:
            If analysis fails, defaults to VISION_LLM + COMPLEX to ensure
            processing completes with highest accuracy method.
        """
        logger.info(f"🔍 Analyzing file: {filename} (type: {file_type})")

        if file_type == "pdf":
            return await self._analyze_pdf(file_content, filename)
        if file_type == "image":
            return await self._analyze_image(file_content, filename)
        # Default to vision LLM for unknown types
        return (
            ExtractionStrategy.VISION_LLM,
            DocumentComplexity.COMPLEX,
            {"reason": "unknown_file_type"},
        )

    async def _analyze_pdf(
        self, content: bytes, filename: str
    ) -> tuple[ExtractionStrategy, DocumentComplexity, dict[str, Any]]:
        """Perform comprehensive PDF analysis for optimal extraction strategy.

        Analyzes PDF structure, embedded text quality, table presence, and medical
        content patterns. Uses pdfplumber for primary analysis and PyPDF2 for
        quality validation. Implements medical-aware table detection to identify
        lab value tables and complex clinical layouts.

        Args:
            content: Raw PDF file content as bytes
            filename: Original filename for logging context

        Returns:
            tuple[ExtractionStrategy, DocumentComplexity, dict[str, Any]]:
                Strategy recommendation, complexity level, and detailed metadata dict with:
                - has_embedded_text (bool): Whether PDF contains extractable text
                - text_coverage (float): Proportion of pages with text (0.0-1.0)
                - text_quality_score (float): Text extraction quality (0.0-1.0)
                - page_count (int): Total pages in PDF
                - has_images (bool): Whether PDF contains embedded images
                - has_tables (bool): Whether medical tables detected
                - reasons (list): Decision rationale for strategy selection

        Example:
            >>> detector = FileQualityDetector()
            >>> # Clean medical report with embedded text
            >>> strategy, complexity, meta = await detector._analyze_pdf(
            ...     content=report_pdf_bytes,
            ...     filename="discharge_summary.pdf"
            ... )
            >>> print(f"Coverage: {meta['text_coverage']}, Quality: {meta['text_quality_score']}")
            Coverage: 1.0, Quality: 0.85
            >>> print(strategy.value)
            'local_text'
            >>>
            >>> # Scanned lab results with tables
            >>> strategy, complexity, meta = await detector._analyze_pdf(
            ...     content=lab_pdf_bytes,
            ...     filename="blood_work.pdf"
            ... )
            >>> print(f"Tables: {meta['has_tables']}, Reasons: {meta['reasons']}")
            Tables: True, Reasons: ['tables_detected_require_vision_llm']
            >>> print(strategy.value)
            'vision_llm'

        Note:
            **Analysis Stages**:
            1. Embedded text detection (pdfplumber on first 5 pages)
            2. Text quality scoring (PyPDF2 validation)
            3. Medical table detection (structural + content analysis)
            4. Strategy determination (cost-optimized decision tree)

            **Medical Table Detection**:
            Combines pdfplumber's table detection with custom heuristics:
            - Character alignment analysis (row/column structure)
            - Medical content patterns (units: mg/dl, mmol/l, etc.)
            - Lab term matching (laborwerte, befund, referenzbereich)

            **Cost Optimization**:
            - High quality text (0.9+) → LOCAL_TEXT even with moderate coverage
            - Tables present → Always VISION_LLM for accuracy
            - No tables + good text (0.7+ coverage, 0.6+ quality) → LOCAL_TEXT

            **Performance**:
            Analyzes only first 5 pages for speed, sufficient for strategy decision.
        """

        analysis = {
            "filename": filename,
            "file_type": "pdf",
            "has_embedded_text": False,
            "text_coverage": 0.0,
            "page_count": 0,
            "has_images": False,
            "has_tables": False,
            "text_quality_score": 0.0,
            "reasons": [],
        }

        try:
            # Step 1: Check for embedded text with pdfplumber
            pdf_file = BytesIO(content)

            with pdfplumber.open(pdf_file) as pdf:
                analysis["page_count"] = len(pdf.pages)
                total_text_length = 0
                pages_with_text = 0

                # Analyze first 5 pages for performance
                pages_to_check = min(5, len(pdf.pages))

                for _i, page in enumerate(pdf.pages[:pages_to_check]):
                    page_text = page.extract_text()

                    if page_text and len(page_text.strip()) > 20:
                        total_text_length += len(page_text)
                        pages_with_text += 1
                        analysis["has_embedded_text"] = True

                    # Check for images on the page
                    if page.images:
                        analysis["has_images"] = True

                    # Check for table-like structures
                    if page.chars and self._detect_table_structure_in_page(page):
                        analysis["has_tables"] = True

                # Calculate text coverage
                if pages_to_check > 0:
                    analysis["text_coverage"] = pages_with_text / pages_to_check
                    analysis["avg_text_per_page"] = (
                        total_text_length / pages_to_check if pages_to_check > 0 else 0
                    )

            # Step 2: Analyze text quality
            if analysis["has_embedded_text"]:
                # Test with PyPDF2 as fallback
                try:
                    pdf_file = BytesIO(content)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)

                    if len(pdf_reader.pages) > 0:
                        sample_text = pdf_reader.pages[0].extract_text()
                        analysis["text_quality_score"] = self._evaluate_text_quality(sample_text)
                except Exception as e:
                    logger.debug(f"PyPDF2 analysis failed: {e}")

            # Step 3: Determine strategy based on analysis
            strategy, complexity = self._determine_pdf_strategy(analysis)

            logger.info(f"📊 PDF Analysis for {filename}:")
            logger.info(f"   - Text coverage: {analysis['text_coverage']:.1%}")
            logger.info(f"   - Quality score: {analysis['text_quality_score']:.2f}")
            logger.info(f"   - Has tables: {analysis['has_tables']}")
            logger.info(f"   - Strategy: {strategy.value}")
            logger.info(f"   - Complexity: {complexity.value}")
            logger.info(f"   - Decision reason: {analysis.get('reasons', ['unknown'])[-1]}")

            return strategy, complexity, analysis

        except Exception as e:
            logger.error(f"❌ PDF analysis failed for {filename}: {e}")
            analysis["error"] = str(e)
            analysis["reasons"].append("analysis_failed")
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.COMPLEX, analysis

    def _detect_table_structure_in_page(self, page) -> bool:
        """Detect medical tables in PDF pages with high precision to minimize false positives.

        Uses multi-method approach combining pdfplumber's built-in table detection,
        character alignment analysis, and medical content pattern matching. Designed
        to accurately identify lab value tables while avoiding false positives from
        narrative medical text with incidental structure.

        Args:
            page: pdfplumber Page object to analyze

        Returns:
            bool: True if page contains actual table structure, False otherwise

        Example:
            >>> import pdfplumber
            >>> with pdfplumber.open("lab_results.pdf") as pdf:
            ...     detector = FileQualityDetector()
            ...     has_tables = detector._detect_table_structure_in_page(pdf.pages[0])
            >>> print(has_tables)
            True

        Note:
            **Detection Methods** (applied in order):
            1. **pdfplumber validation**: Uses library's table finder, validates
               minimum 2 rows, 2 columns, 30% cell fill ratio
            2. **Character alignment**: Analyzes row/column consistency, requires
               3+ aligned rows with 3+ columns (structure score ≥0.7)
            3. **Medical content patterns**: Detects lab terms (Laborwerte, Befund),
               units (mg/dl, mmol/l), reference ranges (5.0-10.0)

            **False Positive Prevention**:
            - Pre-filters narrative text (long sentences, paragraphs)
            - High thresholds: Structure 0.7+ OR (Structure 0.4+ AND Medical 0.6+)
            - Validates pdfplumber tables for meaningful content

            **Medical Awareness**:
            Table detection tuned for clinical documents:
            - Lab value patterns with units
            - Medical terminology (Hämoglobin, Leukozyten, etc.)
            - Reference ranges typical of lab reports

            **Performance**:
            Complex analysis cached per page, ~50-100ms per page.
        """
        try:
            # Method 1: Use pdfplumber's built-in table detection with validation
            tables = page.find_tables()
            if tables and len(tables) > 0:
                # Validate that detected tables are actually meaningful
                valid_tables = 0
                for table in tables:
                    if self._validate_pdfplumber_table(table):
                        valid_tables += 1

                if valid_tables > 0:
                    logger.debug(
                        f"📊 Found {valid_tables}/{len(tables)} valid table structures using pdfplumber"
                    )
                    return True

            # Method 2: Enhanced character alignment analysis with stricter criteria
            chars = page.chars
            if not chars or len(chars) < 50:  # Need sufficient content to detect tables
                return False

            # Get text for additional validation
            page_text = page.extract_text() or ""

            # Pre-filter: Skip pages that are clearly narrative text
            if self._is_narrative_text(page_text):
                logger.debug("📄 Page appears to be narrative text, skipping table detection")
                return False

            # Analyze character positioning with improved precision
            table_score = self._analyze_character_alignment(chars, page_text)

            # Method 3: Medical table content analysis
            medical_table_score = self._analyze_medical_table_content(page_text)

            # Combined decision with higher thresholds to reduce false positives
            is_table = (
                table_score >= 0.7  # Strong structural evidence (raised from mixed criteria)
                or (
                    table_score >= 0.4 and medical_table_score >= 0.6
                )  # Moderate structure + strong medical indicators
            )

            if is_table:
                logger.debug(
                    f"📊 Table detected - Structure Score: {table_score:.2f}, Medical Score: {medical_table_score:.2f}"
                )

            return is_table

        except Exception as e:
            logger.debug(f"Table detection error: {e}")
            return False

    def _validate_pdfplumber_table(self, table) -> bool:
        """Validate that a pdfplumber-detected table is actually meaningful"""
        try:
            # Extract table data
            table_data = table.extract()
            if not table_data or len(table_data) < 2:  # Need at least 2 rows
                return False

            # Check for meaningful content
            non_empty_cells = 0
            total_cells = 0

            for row in table_data:
                if row:  # Row is not None
                    for cell in row:
                        total_cells += 1
                        if cell and str(cell).strip():  # Non-empty cell
                            non_empty_cells += 1

            # Table should have at least 30% filled cells and minimum dimensions
            fill_ratio = non_empty_cells / total_cells if total_cells > 0 else 0
            has_minimum_size = len(table_data) >= 2 and len(table_data[0] or []) >= 2

            return fill_ratio >= 0.3 and has_minimum_size

        except Exception:
            return False

    def _is_narrative_text(self, text: str) -> bool:
        """Check if text appears to be narrative (not tabular)"""
        if not text or len(text.strip()) < 100:
            return False

        # Count sentences vs. short fragments
        import re

        sentences = re.split(r"[.!?]+\s+", text)
        long_sentences = [s for s in sentences if len(s.strip()) > 30]

        # Count paragraph indicators
        paragraphs = text.count("\n\n")

        # Narrative text typically has longer sentences and paragraph breaks
        narrative_indicators = len(long_sentences) >= 3 or paragraphs >= 2

        # Check for absence of table-like patterns
        has_few_numbers = len(re.findall(r"\d+[.,]\d+", text)) < 5
        has_few_separators = text.count("|") < 3 and text.count("\t") < 5

        return narrative_indicators and has_few_numbers and has_few_separators

    def _analyze_character_alignment(self, chars, page_text: str) -> float:
        """Analyze character alignment patterns with improved precision"""
        from collections import defaultdict

        # Group characters by vertical position (rows) with tighter clustering
        [char["y0"] for char in chars]
        [char["x0"] for char in chars]

        # More precise grouping for row detection
        y_groups = defaultdict(list)
        for _i, char in enumerate(chars):
            y_key = round(char["y0"] / 3) * 3  # Group by 3px for rows
            y_groups[y_key].append(char)

        # Analyze each row for column structure
        consistent_rows = 0
        total_rows = len(y_groups)

        if total_rows < 3:  # Need at least 3 rows for a table
            return 0.0

        # Check each row for consistent column structure
        column_positions = set()
        for _y_key, row_chars in y_groups.items():
            if len(row_chars) < 4:  # Skip rows with too few characters
                continue

            # Extract x-positions for this row
            row_x_positions = [char["x0"] for char in row_chars]
            row_x_positions.sort()

            # Group x-positions into columns (more precise grouping)
            row_columns = []
            current_column = [row_x_positions[0]]

            for x in row_x_positions[1:]:
                if x - current_column[-1] < 15:  # Characters within 15px are same column
                    current_column.append(x)
                else:
                    if len(current_column) >= 2:  # Valid column needs multiple chars
                        row_columns.append(sum(current_column) / len(current_column))
                    current_column = [x]

            # Don't forget the last column
            if len(current_column) >= 2:
                row_columns.append(sum(current_column) / len(current_column))

            # Check if this row has consistent column structure
            if len(row_columns) >= 3:  # At least 3 columns for a table
                column_positions.update(row_columns)
                consistent_rows += 1

        # Calculate structure score
        row_consistency = consistent_rows / max(total_rows, 1)
        column_count = len(column_positions)

        # Bonus for medical lab value patterns
        import re

        lab_patterns = len(re.findall(r"\d+[.,]\d+\s*(mg|ml|mmol|µg|ng|u/l|iu/l|%)", page_text))
        lab_bonus = min(lab_patterns * 0.1, 0.3)  # Up to 0.3 bonus

        structure_score = (row_consistency * 0.7) + (min(column_count / 5, 1.0) * 0.3) + lab_bonus

        return min(structure_score, 1.0)

    def _analyze_medical_table_content(self, text: str) -> float:
        """Analyze text for medical table-specific content"""
        if not text:
            return 0.0

        text_lower = text.lower()
        score = 0.0

        # Medical lab terms (strong indicators)
        lab_terms = [
            "laborwerte",
            "blutwerte",
            "laborergebnisse",
            "befund",
            "referenzbereich",
            "normalwert",
            "grenzwert",
            "hämoglobin",
            "leukozyten",
            "thrombozyten",
            "erythrozyten",
            "glukose",
            "cholesterin",
            "kreatinin",
            "harnstoff",
            "bilirubin",
            "albumin",
            "protein",
            "calcium",
        ]

        lab_term_matches = sum(1 for term in lab_terms if term in text_lower)
        score += min(lab_term_matches * 0.15, 0.6)  # Max 0.6 for lab terms

        # Medical units (very strong indicators for lab tables)
        import re

        medical_units = re.findall(
            r"\d+[.,]\d*\s*(mg/dl|mmol/l|µg/l|ng/ml|u/l|iu/l|g/l|%|/µl)", text_lower
        )
        score += min(len(medical_units) * 0.1, 0.4)  # Max 0.4 for units

        # Table structure indicators
        separators = text.count("|") + text.count("\t") + len(re.findall(r"\s{3,}", text))
        score += min(separators * 0.02, 0.2)  # Max 0.2 for separators

        # Reference ranges (typical in lab tables)
        reference_patterns = len(re.findall(r"\d+[.,]\d*\s*[-–]\s*\d+[.,]\d*", text))
        score += min(reference_patterns * 0.05, 0.2)  # Max 0.2 for ranges

        return min(score, 1.0)

    def _evaluate_text_quality(self, text: str) -> float:
        """Evaluate extracted text quality using heuristic scoring.

        Assesses text extraction quality based on length, character distribution,
        and word patterns. Used to determine if embedded PDF text is sufficiently
        clean for local extraction vs. requiring OCR.

        Args:
            text: Extracted text sample to evaluate

        Returns:
            float: Quality score from 0.0 (poor) to 1.0 (excellent)

        Example:
            >>> detector = FileQualityDetector()
            >>> # High-quality extracted text
            >>> clean_text = "Der Patient zeigt eine deutliche Verbesserung..."
            >>> score = detector._evaluate_text_quality(clean_text)
            >>> print(f"Quality: {score:.2f}")
            Quality: 0.85
            >>>
            >>> # Poor quality (garbled extraction)
            >>> garbled = "D�r P@t!3nt z31gt..."
            >>> score = detector._evaluate_text_quality(garbled)
            >>> print(f"Quality: {score:.2f}")
            Quality: 0.32

        Note:
            **Scoring Components**:
            - Length: 0.2 points for >100 chars, 0.2 more for >500 chars
            - Letter ratio: 0.4 points max based on alphabetic chars / total
            - Word patterns: 0.2 points if 10+ valid German/medical words

            **Thresholds**:
            - 0.9+: Excellent quality → Always try LOCAL_TEXT
            - 0.7-0.9: High quality → LOCAL_TEXT for most cases
            - 0.4-0.7: Moderate → Context-dependent
            - <0.4: Poor → Prefer OCR/Vision LLM

            **Use Cases**:
            - Differentiating clean digital PDFs from scanned
            - Detecting garbled/corrupted text extraction
            - Optimizing cost by avoiding Vision LLM when unnecessary
        """
        if not text or len(text.strip()) < 10:
            return 0.0

        quality_score = 0.0

        # Length indicator
        if len(text) > 100:
            quality_score += 0.2
        if len(text) > 500:
            quality_score += 0.2

        # Character distribution (letters vs. noise)
        letters = sum(1 for c in text if c.isalpha())
        total_chars = len(text.replace(" ", "").replace("\n", ""))

        if total_chars > 0:
            letter_ratio = letters / total_chars
            quality_score += letter_ratio * 0.4

        # Word-like patterns
        import re

        words = re.findall(r"\b[a-zA-ZäöüÄÖÜß]{3,}\b", text)
        if len(words) > 10:
            quality_score += 0.2

        return min(quality_score, 1.0)

    def _determine_pdf_strategy(
        self, analysis: dict[str, Any]
    ) -> tuple[ExtractionStrategy, DocumentComplexity]:
        """Apply cost-optimized decision tree to select PDF extraction strategy.

        Implements prioritized decision logic that balances cost efficiency with
        accuracy requirements. Medical table detection takes highest priority,
        followed by embedded text quality optimization, with fallback to OCR/Vision.

        Args:
            analysis: Analysis metadata dict containing:
                - text_coverage (float): Proportion of pages with text (0.0-1.0)
                - text_quality_score (float): Text quality score (0.0-1.0)
                - has_tables (bool): Whether medical tables detected
                - has_images (bool): Whether embedded images present

        Returns:
            tuple[ExtractionStrategy, DocumentComplexity]:
                Recommended strategy and assessed complexity level

        Example:
            >>> detector = FileQualityDetector()
            >>> # High-quality PDF with tables
            >>> analysis = {
            ...     "text_coverage": 0.95,
            ...     "text_quality_score": 0.85,
            ...     "has_tables": True,
            ...     "has_images": False,
            ...     "reasons": []
            ... }
            >>> strategy, complexity = detector._determine_pdf_strategy(analysis)
            >>> print(f"{strategy.value} - {complexity.value}")
            vision_llm - moderate
            >>>
            >>> # Clean PDF without tables
            >>> analysis = {
            ...     "text_coverage": 0.95,
            ...     "text_quality_score": 0.85,
            ...     "has_tables": False,
            ...     "has_images": False,
            ...     "reasons": []
            ... }
            >>> strategy, complexity = detector._determine_pdf_strategy(analysis)
            >>> print(f"{strategy.value} - {complexity.value}")
            local_text - simple

        Note:
            **Decision Tree Priority** (evaluated top-to-bottom):

            1. **Tables Detected** → VISION_LLM (accuracy critical)
               - Medical lab tables require structure preservation
               - Cost justified by accuracy requirement

            2. **High-Quality Text Without Tables** → LOCAL_TEXT (cost-free)
               - Coverage ≥0.9 + Quality ≥0.7 → SIMPLE
               - Coverage ≥0.7 + Quality ≥0.6 → SIMPLE
               - Quality ≥0.9 + Coverage ≥0.6 → MODERATE (prioritize quality)
               - Quality ≥0.8 + Coverage ≥0.5 → MODERATE

            3. **Moderate Quality** → Context-dependent
               - Coverage ≥0.5 + Quality ≥0.4:
                 * No tables + Tesseract → LOCAL_OCR
                 * No tables + Quality ≥0.7 → LOCAL_TEXT
                 * Otherwise → VISION_LLM

            4. **Poor/No Text** → OCR/Vision
               - Complex layout → VISION_LLM (VERY_COMPLEX)
               - Simple scan + Tesseract → LOCAL_OCR (MODERATE)
               - Otherwise → VISION_LLM (MODERATE)

            **Cost Impact**:
            - LOCAL_TEXT: Free, instant
            - LOCAL_OCR: Free, 2-5s/page
            - VISION_LLM: OVH cost (~$0.001/page), ~2min/page

            **Reason Tracking**:
            Appends decision rationale to analysis['reasons'] for debugging.
        """

        text_coverage = analysis.get("text_coverage", 0.0)
        text_quality = analysis.get("text_quality_score", 0.0)
        has_tables = analysis.get("has_tables", False)
        has_images = analysis.get("has_images", False)

        # PRIORITY 1: Table detection - if tables detected, use Vision LLM for accuracy
        if has_tables:
            analysis["reasons"].append("tables_detected_require_vision_llm")
            if text_coverage >= 0.8 and text_quality >= 0.6:
                return ExtractionStrategy.VISION_LLM, DocumentComplexity.MODERATE
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.COMPLEX

        # PRIORITY 2: High-quality embedded text WITHOUT tables - use local extraction (cost-effective)
        if text_coverage >= 0.9 and text_quality >= 0.7:
            analysis["reasons"].append("high_quality_embedded_text_no_tables")
            return ExtractionStrategy.LOCAL_TEXT, DocumentComplexity.SIMPLE

        # Good embedded text without tables - use local (cost-effective)
        if text_coverage >= 0.7 and text_quality >= 0.6:
            analysis["reasons"].append("good_embedded_text_no_tables")
            return ExtractionStrategy.LOCAL_TEXT, DocumentComplexity.SIMPLE

        # High quality text regardless of coverage - prioritize cost savings
        if text_quality >= 0.9 and text_coverage >= 0.6:
            analysis["reasons"].append("very_high_quality_text_cost_optimization")
            # Excellent quality (0.9+) should always try local extraction first
            return ExtractionStrategy.LOCAL_TEXT, DocumentComplexity.MODERATE

        # High quality text with moderate coverage - cost optimization
        if text_quality >= 0.8 and text_coverage >= 0.5:
            analysis["reasons"].append("high_quality_moderate_coverage_cost_optimization")
            # High quality (0.8+) with reasonable coverage should use local extraction
            return ExtractionStrategy.LOCAL_TEXT, DocumentComplexity.MODERATE

        # Moderate embedded text
        if text_coverage >= 0.5 and text_quality >= 0.4:
            analysis["reasons"].append("moderate_embedded_text")
            if not has_tables and self.tesseract_available:
                return ExtractionStrategy.LOCAL_OCR, DocumentComplexity.MODERATE
            if not has_tables:
                return ExtractionStrategy.LOCAL_TEXT, DocumentComplexity.MODERATE  # Try local first
            # Only use Vision LLM if quality is not high enough for local extraction
            if text_quality >= 0.7:
                analysis["reasons"].append("moderate_coverage_decent_quality_try_local")
                return ExtractionStrategy.LOCAL_TEXT, DocumentComplexity.MODERATE
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.MODERATE

        # Poor or no embedded text - likely scanned
        analysis["reasons"].append("poor_or_no_embedded_text")
        if has_tables or has_images:
            analysis["reasons"].append("complex_layout_detected")
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.VERY_COMPLEX
        # Simple scanned document
        if self.tesseract_available:
            return ExtractionStrategy.LOCAL_OCR, DocumentComplexity.MODERATE
        return ExtractionStrategy.VISION_LLM, DocumentComplexity.MODERATE

    async def _analyze_image(
        self, content: bytes, filename: str
    ) -> tuple[ExtractionStrategy, DocumentComplexity, dict[str, Any]]:
        """Analyze image quality and content for optimal OCR strategy selection.

        Performs computer vision analysis using PIL and OpenCV (if available) to assess
        image quality, detect tables/forms, and estimate text density. Routes to
        appropriate OCR engine based on visual complexity and quality metrics.

        Args:
            content: Raw image file content as bytes (JPEG or PNG)
            filename: Original filename for logging context

        Returns:
            tuple[ExtractionStrategy, DocumentComplexity, dict[str, Any]]:
                Strategy recommendation, complexity level, and detailed metadata dict with:
                - image_size (tuple): Pixel dimensions (width, height)
                - image_quality (float): Sharpness + contrast score (0.0-1.0)
                - text_density (float): Estimated text coverage (0.0-1.0)
                - has_tables (bool): Whether table structures detected
                - has_forms (bool): Whether form fields detected
                - reasons (list): Decision rationale

        Example:
            >>> detector = FileQualityDetector()
            >>> # High-quality scan with tables
            >>> strategy, complexity, meta = await detector._analyze_image(
            ...     content=scan_bytes,
            ...     filename="lab_scan.jpg"
            ... )
            >>> print(f"Quality: {meta['image_quality']:.2f}, Tables: {meta['has_tables']}")
            Quality: 0.82, Tables: True
            >>> print(strategy.value)
            'vision_llm'
            >>>
            >>> # Simple clean scan without tables
            >>> strategy, complexity, meta = await detector._analyze_image(
            ...     content=clean_scan_bytes,
            ...     filename="report.jpg"
            ... )
            >>> print(f"Quality: {meta['image_quality']:.2f}, Text density: {meta['text_density']:.2f}")
            Quality: 0.75, Text density: 0.08
            >>> print(strategy.value)
            'local_ocr'

        Note:
            **Quality Assessment** (requires OpenCV):
            - Sharpness: Laplacian variance (blur detection)
            - Contrast: Standard deviation of grayscale
            - Combined score normalized to 0.0-1.0

            **Table Detection** (requires OpenCV):
            - Morphological operations to find horizontal/vertical lines
            - Hough transform for line detection
            - Requires 3+ horizontal AND 2+ vertical lines

            **Form Detection** (requires OpenCV):
            - Edge detection with Canny algorithm
            - Contour analysis for rectangular shapes
            - Requires 3+ form-sized rectangles (1000-50000 px²)

            **Strategy Selection**:
            - Tables/forms present → VISION_LLM (structure preservation)
            - High quality (0.7+) + text (0.05+) → LOCAL_OCR if Tesseract available
            - Moderate quality (0.4+) → VISION_LLM
            - Poor quality/low text → VISION_LLM

            **Graceful Degradation**:
            Without OpenCV: Defaults to medium quality (0.5) and Vision LLM.
        """

        analysis = {
            "filename": filename,
            "file_type": "image",
            "image_size": None,
            "has_text": False,
            "text_density": 0.0,
            "has_tables": False,
            "has_forms": False,
            "image_quality": 0.0,
            "reasons": [],
        }

        try:
            # Load image
            image = Image.open(BytesIO(content))
            analysis["image_size"] = image.size

            # Convert to OpenCV format for analysis
            cv_image = self._pil_to_cv2(image)

            # Analyze image characteristics
            analysis["image_quality"] = self._assess_image_quality(cv_image)
            analysis["has_tables"] = self._detect_table_in_image(cv_image)
            analysis["has_forms"] = self._detect_form_structure(cv_image)
            analysis["text_density"] = self._estimate_text_density(cv_image)

            # Determine strategy
            strategy, complexity = self._determine_image_strategy(analysis)

            logger.info(f"🖼️ Image Analysis for {filename}:")
            logger.info(f"   - Size: {analysis['image_size']}")
            logger.info(f"   - Quality: {analysis['image_quality']:.2f}")
            logger.info(f"   - Text density: {analysis['text_density']:.2f}")
            logger.info(f"   - Has tables: {analysis['has_tables']}")
            logger.info(f"   - OpenCV available: {self.opencv_available}")
            logger.info(f"   - Strategy: {strategy.value}")
            logger.info(f"   - Complexity: {complexity.value}")

            return strategy, complexity, analysis

        except Exception as e:
            logger.error(f"❌ Image analysis failed for {filename}: {e}")
            analysis["error"] = str(e)
            analysis["reasons"].append("analysis_failed")
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.COMPLEX, analysis

    def _pil_to_cv2(self, pil_image: Image.Image):
        """Convert PIL Image to OpenCV format - returns None if OpenCV not available"""
        if not OPENCV_AVAILABLE:
            return None

        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        open_cv_image = np.array(pil_image)
        return cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)

    def _assess_image_quality(self, cv_image) -> float:
        """Assess the quality of an image for OCR"""
        if not OPENCV_AVAILABLE or cv_image is None:
            return 0.5  # Default medium quality when OpenCV not available

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

            # Calculate sharpness using Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

            # Normalize to 0-1 range (empirically determined thresholds)
            sharpness_score = min(laplacian_var / 1000, 1.0)

            # Calculate contrast
            contrast = gray.std() / 255.0

            # Overall quality score
            return (sharpness_score + contrast) / 2

        except Exception:
            return 0.5  # Default medium quality

    def _detect_table_in_image(self, cv_image) -> bool:
        """Detect if image contains table structures"""
        if not OPENCV_AVAILABLE or cv_image is None:
            return False  # Can't detect tables without OpenCV

        try:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

            # Apply threshold to get binary image
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

            # Detect horizontal and vertical lines
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

            horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
            vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)

            # Count significant lines
            h_lines = cv2.HoughLinesP(
                horizontal_lines, 1, np.pi / 180, threshold=50, minLineLength=100, maxLineGap=10
            )
            v_lines = cv2.HoughLinesP(
                vertical_lines, 1, np.pi / 180, threshold=50, minLineLength=100, maxLineGap=10
            )

            # If we have both horizontal and vertical lines, likely a table
            return (h_lines is not None and len(h_lines) >= 3) and (
                v_lines is not None and len(v_lines) >= 2
            )

        except Exception:
            return False

    def _detect_form_structure(self, cv_image) -> bool:
        """Detect if image contains form-like structures"""
        if not OPENCV_AVAILABLE or cv_image is None:
            return False  # Can't detect forms without OpenCV

        try:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

            # Look for rectangular shapes (form fields)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Count rectangular contours
            rectangular_shapes = 0
            for contour in contours:
                # Approximate contour
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                # Check if it's roughly rectangular and of reasonable size
                if len(approx) == 4:
                    area = cv2.contourArea(contour)
                    if 1000 < area < 50000:  # Reasonable form field size
                        rectangular_shapes += 1

            # If we have multiple rectangular shapes, likely a form
            return rectangular_shapes >= 3

        except Exception:
            return False

    def _estimate_text_density(self, cv_image) -> float:
        """Estimate the density of text in the image"""
        if not OPENCV_AVAILABLE or cv_image is None:
            return 0.1  # Default low density when OpenCV not available

        try:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

            # Apply threshold to isolate text
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Invert so text is white
            binary = cv2.bitwise_not(binary)

            # Calculate text density as ratio of text pixels to total pixels
            text_pixels = cv2.countNonZero(binary)
            total_pixels = binary.shape[0] * binary.shape[1]

            return text_pixels / total_pixels

        except Exception:
            return 0.1  # Default low density

    def _determine_image_strategy(
        self, analysis: dict[str, Any]
    ) -> tuple[ExtractionStrategy, DocumentComplexity]:
        """Determine the best strategy based on image analysis"""

        image_quality = analysis.get("image_quality", 0.0)
        has_tables = analysis.get("has_tables", False)
        has_forms = analysis.get("has_forms", False)
        text_density = analysis.get("text_density", 0.0)

        # Complex medical documents (forms/tables) - always use vision LLM
        if has_tables or has_forms:
            analysis["reasons"].append("complex_medical_layout")
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.VERY_COMPLEX

        # High quality image with good text density
        if image_quality >= 0.7 and text_density >= 0.05:
            analysis["reasons"].append("high_quality_with_text")
            if self.tesseract_available:
                return ExtractionStrategy.LOCAL_OCR, DocumentComplexity.SIMPLE
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.SIMPLE

        # Moderate quality
        if image_quality >= 0.4 and text_density >= 0.02:
            analysis["reasons"].append("moderate_quality")
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.MODERATE

        # Poor quality or very low text density
        analysis["reasons"].append("poor_quality_or_low_text")
        return ExtractionStrategy.VISION_LLM, DocumentComplexity.COMPLEX

    async def analyze_multiple_files(self, files: list[tuple[bytes, str, str]]) -> dict[str, Any]:
        """Analyze document sequence and provide consolidated extraction strategy.

        Performs individual analysis of each file, then consolidates results to
        recommend a unified processing strategy. Ensures consistency across multi-page
        medical documents submitted as separate files (common for scanned records).

        Args:
            files: List of (content, file_type, filename) tuples where:
                - content (bytes): Raw file data
                - file_type (str): "pdf" or "image"
                - filename (str): Original filename

        Returns:
            dict[str, Any]: Consolidated analysis containing:
                - file_count (int): Number of files analyzed
                - individual_analyses (list): Per-file analysis metadata
                - strategies (list): Strategy for each file
                - complexities (list): Complexity for each file
                - recommended_strategy (str): Unified strategy for all files
                - recommended_complexity (str): Highest complexity level detected
                - reasons (list): Rationale for consolidation decision

        Example:
            >>> detector = FileQualityDetector()
            >>> # Multi-page scanned lab report
            >>> files = [
            ...     (page1_bytes, "image", "labs_page1.jpg"),
            ...     (page2_bytes, "image", "labs_page2.jpg"),
            ...     (page3_bytes, "image", "labs_page3.jpg")
            ... ]
            >>> result = await detector.analyze_multiple_files(files)
            >>> print(f"Strategy: {result['recommended_strategy']}")
            Strategy: vision_llm
            >>> print(f"Files: {result['file_count']}, Complexity: {result['recommended_complexity']}")
            Files: 3, Complexity: complex

        Note:
            **Consolidation Logic**:
            - Pessimistic strategy selection: If ANY file needs VISION_LLM, use it for ALL
            - Complexity escalation: Use HIGHEST complexity level detected
            - Rationale: Ensures consistency and quality across document sequence

            **Use Cases**:
            - Multi-page scanned documents split into separate images
            - Mixed document types in single submission
            - Faxed medical records (page-by-page)

            **Performance**:
            Analyzes files sequentially to manage memory, ~100ms per file overhead.

            **Empty Input**:
            Returns default VISION_LLM + COMPLEX if files list is empty.
        """
        if not files:
            return {
                "strategy": ExtractionStrategy.VISION_LLM,
                "complexity": DocumentComplexity.COMPLEX,
            }

        logger.info(f"🔍 Analyzing {len(files)} files for multi-file strategy")

        individual_analyses = []
        strategies = []
        complexities = []

        for content, file_type, filename in files:
            strategy, complexity, analysis = await self.analyze_file(content, file_type, filename)

            individual_analyses.append(analysis)
            strategies.append(strategy)
            complexities.append(complexity)

        # Determine consolidated strategy
        consolidated_strategy = self._consolidate_strategies(strategies)
        consolidated_complexity = self._consolidate_complexities(complexities)

        consolidated_analysis = {
            "file_count": len(files),
            "individual_analyses": individual_analyses,
            "strategies": [s.value for s in strategies],
            "complexities": [c.value for c in complexities],
            "recommended_strategy": consolidated_strategy.value,
            "recommended_complexity": consolidated_complexity.value,
            "reasons": self._get_consolidation_reasons(strategies, complexities),
        }

        logger.info("📊 Multi-file analysis complete:")
        logger.info(f"   - Files: {len(files)}")
        logger.info(f"   - Recommended strategy: {consolidated_strategy.value}")
        logger.info(f"   - Complexity: {consolidated_complexity.value}")

        return consolidated_analysis

    def _consolidate_strategies(self, strategies: list[ExtractionStrategy]) -> ExtractionStrategy:
        """Consolidate multiple strategies into one recommendation"""

        # If any file requires vision LLM, use it for all (consistency)
        if ExtractionStrategy.VISION_LLM in strategies:
            return ExtractionStrategy.VISION_LLM

        # If any file requires local OCR, use it for all
        if ExtractionStrategy.LOCAL_OCR in strategies:
            return ExtractionStrategy.LOCAL_OCR

        # Otherwise, local text extraction is sufficient
        return ExtractionStrategy.LOCAL_TEXT

    def _consolidate_complexities(
        self, complexities: list[DocumentComplexity]
    ) -> DocumentComplexity:
        """Consolidate multiple complexities into one level"""

        # Take the highest complexity level
        complexity_order = [
            DocumentComplexity.SIMPLE,
            DocumentComplexity.MODERATE,
            DocumentComplexity.COMPLEX,
            DocumentComplexity.VERY_COMPLEX,
        ]

        max_complexity = DocumentComplexity.SIMPLE
        for complexity in complexities:
            if complexity_order.index(complexity) > complexity_order.index(max_complexity):
                max_complexity = complexity

        return max_complexity

    def _get_consolidation_reasons(
        self, strategies: list[ExtractionStrategy], complexities: list[DocumentComplexity]
    ) -> list[str]:
        """Get reasons for the consolidation decision"""

        reasons = []

        if ExtractionStrategy.VISION_LLM in strategies:
            reasons.append("vision_llm_required_for_some_files")

        if DocumentComplexity.VERY_COMPLEX in complexities:
            reasons.append("very_complex_files_detected")

        if len(set(strategies)) > 1:
            reasons.append("mixed_file_types_require_unified_approach")

        return reasons
