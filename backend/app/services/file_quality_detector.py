"""
File Quality Detector for Conditional OCR Routing
Analyzes documents to determine the best text extraction strategy
"""

import os
import logging
from typing import Tuple, Dict, Any, Optional
from io import BytesIO
from enum import Enum

import PyPDF2
import pdfplumber
from PIL import Image

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
    LOCAL_TEXT = "local_text"          # Use pdfplumber/PyPDF2 for clean PDFs
    LOCAL_OCR = "local_ocr"            # Use Tesseract for moderate quality
    VISION_LLM = "vision_llm"          # Use Qwen 2.5 VL for complex/poor quality
    HYBRID = "hybrid"                  # Use combination of methods

class DocumentComplexity(Enum):
    """Document complexity levels"""
    SIMPLE = "simple"                  # Clean text, simple layout
    MODERATE = "moderate"              # Some formatting, tables
    COMPLEX = "complex"                # Complex layouts, forms, tables
    VERY_COMPLEX = "very_complex"      # Handwritten, poor quality, complex forms

class FileQualityDetector:
    """
    Analyzes files to determine optimal text extraction strategy
    """

    def __init__(self):
        self.tesseract_available = self._check_tesseract_available()
        self.opencv_available = OPENCV_AVAILABLE
        logger.info(f"🔍 File Quality Detector initialized:")
        logger.info(f"   - Tesseract: {'✅' if self.tesseract_available else '❌'}")
        logger.info(f"   - OpenCV: {'✅' if self.opencv_available else '❌'}")

    def _check_tesseract_available(self) -> bool:
        """Check if Tesseract OCR is available"""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    async def analyze_file(
        self,
        file_content: bytes,
        file_type: str,
        filename: str
    ) -> Tuple[ExtractionStrategy, DocumentComplexity, Dict[str, Any]]:
        """
        Analyze a file and determine the best extraction strategy

        Args:
            file_content: File content as bytes
            file_type: Type of file ('pdf' or 'image')
            filename: Original filename

        Returns:
            Tuple of (strategy, complexity, analysis_metadata)
        """
        logger.info(f"🔍 Analyzing file: {filename} (type: {file_type})")

        if file_type == "pdf":
            return await self._analyze_pdf(file_content, filename)
        elif file_type == "image":
            return await self._analyze_image(file_content, filename)
        else:
            # Default to vision LLM for unknown types
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.COMPLEX, {"reason": "unknown_file_type"}

    async def _analyze_pdf(self, content: bytes, filename: str) -> Tuple[ExtractionStrategy, DocumentComplexity, Dict[str, Any]]:
        """Analyze PDF file to determine extraction strategy"""

        analysis = {
            "filename": filename,
            "file_type": "pdf",
            "has_embedded_text": False,
            "text_coverage": 0.0,
            "page_count": 0,
            "has_images": False,
            "has_tables": False,
            "text_quality_score": 0.0,
            "reasons": []
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

                for i, page in enumerate(pdf.pages[:pages_to_check]):
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
                    analysis["avg_text_per_page"] = total_text_length / pages_to_check if pages_to_check > 0 else 0

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

            return strategy, complexity, analysis

        except Exception as e:
            logger.error(f"❌ PDF analysis failed for {filename}: {e}")
            analysis["error"] = str(e)
            analysis["reasons"].append("analysis_failed")
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.COMPLEX, analysis

    def _detect_table_structure_in_page(self, page) -> bool:
        """Detect if a PDF page contains actual table structures (improved algorithm)"""
        try:
            # Method 1: Use pdfplumber's built-in table detection
            tables = page.find_tables()
            if tables and len(tables) > 0:
                # Found actual table structures
                logger.debug(f"📊 Found {len(tables)} table structures using pdfplumber")
                return True

            # Method 2: Look for table-like character alignment patterns
            chars = page.chars
            if not chars:
                return False

            # Count characters aligned vertically (potential columns)
            x_positions = [char['x0'] for char in chars]
            y_positions = [char['y0'] for char in chars]

            from collections import Counter

            # Group x-positions (columns) with tighter grouping
            x_counter = Counter([round(x/8)*8 for x in x_positions])  # Group by ~8px
            # Group y-positions (rows)
            y_counter = Counter([round(y/5)*5 for y in y_positions])  # Group by ~5px

            # Must have multiple distinct columns AND rows for a table
            significant_columns = [count for count in x_counter.values() if count >= 8]
            significant_rows = [count for count in y_counter.values() if count >= 4]

            has_column_structure = len(significant_columns) >= 4  # At least 4 columns
            has_row_structure = len(significant_rows) >= 3        # At least 3 rows

            # Method 3: Look for table indicators in text
            page_text = page.extract_text() or ""
            table_indicators = [
                # Common table separators
                '\t', '|',
                # Multiple spaces (column separation)
                '   ',
                # Common medical table terms
                'wert', 'normal', 'bereich', 'referenz',
                'labor', 'befund', 'ergebnis',
                # Table-like number patterns
            ]

            has_table_text_patterns = any(indicator in page_text.lower() for indicator in table_indicators)

            # Also check for number-heavy content (likely lab values in tables)
            import re
            numbers = re.findall(r'\d+[.,]\d+|\d+\s*(mg|ml|mmol|µg|ng|u/l|iu/l|%)', page_text)
            has_many_numbers = len(numbers) >= 5

            # Decision logic: must have strong evidence of table structure
            is_table = (
                (has_column_structure and has_row_structure) or  # Strong structural evidence
                (has_column_structure and has_many_numbers) or   # Columns + lab values
                (has_table_text_patterns and has_many_numbers and len(significant_columns) >= 2)  # Text indicators + numbers + some structure
            )

            if is_table:
                logger.debug(f"📊 Table detected - Columns: {len(significant_columns)}, Rows: {len(significant_rows)}, Numbers: {len(numbers)}")

            return is_table

        except Exception as e:
            logger.debug(f"Table detection error: {e}")
            return False

    def _evaluate_text_quality(self, text: str) -> float:
        """Evaluate the quality of extracted text"""
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
        total_chars = len(text.replace(' ', '').replace('\n', ''))

        if total_chars > 0:
            letter_ratio = letters / total_chars
            quality_score += letter_ratio * 0.4

        # Word-like patterns
        import re
        words = re.findall(r'\b[a-zA-ZäöüÄÖÜß]{3,}\b', text)
        if len(words) > 10:
            quality_score += 0.2

        return min(quality_score, 1.0)

    def _determine_pdf_strategy(self, analysis: Dict[str, Any]) -> Tuple[ExtractionStrategy, DocumentComplexity]:
        """Determine the best strategy based on PDF analysis"""

        text_coverage = analysis.get("text_coverage", 0.0)
        text_quality = analysis.get("text_quality_score", 0.0)
        has_tables = analysis.get("has_tables", False)
        has_images = analysis.get("has_images", False)

        # High-quality embedded text - always use local extraction (cost-effective)
        if text_coverage >= 0.9 and text_quality >= 0.7 and not has_tables:
            analysis["reasons"].append("high_quality_embedded_text")
            return ExtractionStrategy.LOCAL_TEXT, DocumentComplexity.SIMPLE

        # Very high-quality text with simple tables - try local first (cost optimization)
        if text_coverage >= 0.9 and text_quality >= 0.8 and has_tables:
            analysis["reasons"].append("high_quality_text_with_simple_tables")
            # For very clean PDFs, even with tables, try local extraction first
            return ExtractionStrategy.LOCAL_TEXT, DocumentComplexity.MODERATE

        # Good embedded text but with complex tables - use vision LLM
        if text_coverage >= 0.8 and text_quality >= 0.6 and has_tables:
            analysis["reasons"].append("good_text_with_complex_tables")
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.COMPLEX

        # Good embedded text without tables - use local (cost-effective)
        if text_coverage >= 0.7 and text_quality >= 0.6 and not has_tables:
            analysis["reasons"].append("good_embedded_text_no_tables")
            return ExtractionStrategy.LOCAL_TEXT, DocumentComplexity.SIMPLE

        # Moderate embedded text
        if text_coverage >= 0.5 and text_quality >= 0.4:
            analysis["reasons"].append("moderate_embedded_text")
            if not has_tables and self.tesseract_available:
                return ExtractionStrategy.LOCAL_OCR, DocumentComplexity.MODERATE
            elif not has_tables:
                return ExtractionStrategy.LOCAL_TEXT, DocumentComplexity.MODERATE  # Try local first
            else:
                return ExtractionStrategy.VISION_LLM, DocumentComplexity.MODERATE

        # Poor or no embedded text - likely scanned
        analysis["reasons"].append("poor_or_no_embedded_text")
        if has_tables or has_images:
            analysis["reasons"].append("complex_layout_detected")
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.VERY_COMPLEX
        else:
            # Simple scanned document
            if self.tesseract_available:
                return ExtractionStrategy.LOCAL_OCR, DocumentComplexity.MODERATE
            else:
                return ExtractionStrategy.VISION_LLM, DocumentComplexity.MODERATE

    async def _analyze_image(self, content: bytes, filename: str) -> Tuple[ExtractionStrategy, DocumentComplexity, Dict[str, Any]]:
        """Analyze image file to determine extraction strategy"""

        analysis = {
            "filename": filename,
            "file_type": "image",
            "image_size": None,
            "has_text": False,
            "text_density": 0.0,
            "has_tables": False,
            "has_forms": False,
            "image_quality": 0.0,
            "reasons": []
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

        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

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
            quality = (sharpness_score + contrast) / 2

            return quality

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
            h_lines = cv2.HoughLinesP(horizontal_lines, 1, np.pi/180, threshold=50, minLineLength=100, maxLineGap=10)
            v_lines = cv2.HoughLinesP(vertical_lines, 1, np.pi/180, threshold=50, minLineLength=100, maxLineGap=10)

            # If we have both horizontal and vertical lines, likely a table
            return (h_lines is not None and len(h_lines) >= 3) and (v_lines is not None and len(v_lines) >= 2)

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

            density = text_pixels / total_pixels

            return density

        except Exception:
            return 0.1  # Default low density

    def _determine_image_strategy(self, analysis: Dict[str, Any]) -> Tuple[ExtractionStrategy, DocumentComplexity]:
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
            else:
                return ExtractionStrategy.VISION_LLM, DocumentComplexity.SIMPLE

        # Moderate quality
        if image_quality >= 0.4 and text_density >= 0.02:
            analysis["reasons"].append("moderate_quality")
            return ExtractionStrategy.VISION_LLM, DocumentComplexity.MODERATE

        # Poor quality or very low text density
        analysis["reasons"].append("poor_quality_or_low_text")
        return ExtractionStrategy.VISION_LLM, DocumentComplexity.COMPLEX

    async def analyze_multiple_files(
        self,
        files: list[tuple[bytes, str, str]]
    ) -> Dict[str, Any]:
        """
        Analyze multiple files and provide consolidated strategy

        Args:
            files: List of (content, file_type, filename) tuples

        Returns:
            Consolidated analysis and recommended strategy
        """
        if not files:
            return {"strategy": ExtractionStrategy.VISION_LLM, "complexity": DocumentComplexity.COMPLEX}

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
            "reasons": self._get_consolidation_reasons(strategies, complexities)
        }

        logger.info(f"📊 Multi-file analysis complete:")
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

    def _consolidate_complexities(self, complexities: list[DocumentComplexity]) -> DocumentComplexity:
        """Consolidate multiple complexities into one level"""

        # Take the highest complexity level
        complexity_order = [
            DocumentComplexity.SIMPLE,
            DocumentComplexity.MODERATE,
            DocumentComplexity.COMPLEX,
            DocumentComplexity.VERY_COMPLEX
        ]

        max_complexity = DocumentComplexity.SIMPLE
        for complexity in complexities:
            if complexity_order.index(complexity) > complexity_order.index(max_complexity):
                max_complexity = complexity

        return max_complexity

    def _get_consolidation_reasons(
        self,
        strategies: list[ExtractionStrategy],
        complexities: list[DocumentComplexity]
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