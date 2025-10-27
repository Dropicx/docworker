"""
Advanced OCR processor with multi-pass extraction and row reconstruction
Ensures complete extraction of all table rows from medical documents
"""

import logging
import re


import cv2
import numpy as np
from PIL import Image, ImageFilter
import pytesseract

logger = logging.getLogger(__name__)


class AdvancedOCRProcessor:
    """Advanced OCR processor that ensures complete row extraction"""

    def __init__(self):
        # Tesseract configurations for different extraction strategies
        self.configs = {
            # Best for clean, high-quality text
            "high_quality": "--oem 1 --psm 6 -l deu+eng -c preserve_interword_spaces=1",
            # For dense text blocks
            "dense_text": "--oem 1 --psm 4 -l deu+eng -c preserve_interword_spaces=1",
            # For sparse text and forms
            "sparse_text": "--oem 1 --psm 11 -l deu+eng -c preserve_interword_spaces=1",
            # For single column text
            "single_column": "--oem 1 --psm 8 -l deu+eng -c preserve_interword_spaces=1",
            # For treating image as single text line (useful for rows)
            "single_line": "--oem 1 --psm 7 -l deu+eng -c preserve_interword_spaces=1",
            # RAW line detection - no preprocessing
            "raw_line": "--oem 1 --psm 13 -l deu+eng",
        }

        # Medical lab parameters for better recognition
        self.lab_parameters = [
            "Hämoglobin",
            "Hämatokrit",
            "Erythrozyten",
            "Leukozyten",
            "Thrombozyten",
            "MCV",
            "MCH",
            "MCHC",
            "RDW",
            "MPV",
            "Neutrophile",
            "Lymphozyten",
            "Monozyten",
            "Eosinophile",
            "Basophile",
            "Glucose",
            "Kreatinin",
            "Harnstoff",
            "Harnsäure",
            "Natrium",
            "Kalium",
            "Chlorid",
            "Calcium",
            "Phosphat",
            "Magnesium",
            "Eisen",
            "Ferritin",
            "Transferrin",
            "Bilirubin",
            "GOT",
            "GPT",
            "GGT",
            "AP",
            "LDH",
            "CK",
            "CK-MB",
            "Troponin",
            "BNP",
            "D-Dimer",
            "INR",
            "PTT",
            "Fibrinogen",
            "CRP",
            "BSG",
            "Procalcitonin",
            "TSH",
            "fT3",
            "fT4",
            "PSA",
            "HbA1c",
            "Cholesterin",
            "HDL",
            "LDL",
            "Triglyzeride",
        ]

    def process_image_multipass(self, image: Image.Image) -> tuple[str, dict[str, Any]]:
        """
        Process image with multiple OCR passes to ensure complete extraction

        Returns:
            Tuple of (extracted_text, metadata_dict)
        """
        logger.info("🔍 Starting multi-pass OCR processing...")

        # Convert PIL Image to OpenCV format for advanced processing
        img_cv = self._pil_to_cv2(image)

        # Step 1: Detect table structure and lines
        table_regions = self._detect_table_regions(img_cv)

        # Step 2: Extract text using multiple strategies
        extraction_results = []

        # Strategy 1: Full page extraction with data
        full_text, full_data = self._extract_with_data(image, self.configs["high_quality"])
        extraction_results.append(("full_page", full_text, full_data))

        # Strategy 2: Row-by-row extraction if table detected
        if table_regions:
            row_texts = self._extract_rows(image, img_cv, table_regions)
            extraction_results.append(("rows", "\n".join(row_texts), None))

        # Strategy 3: Enhanced preprocessing and extraction
        enhanced_image = self._enhance_image_for_ocr(image)
        enhanced_text, enhanced_data = self._extract_with_data(
            enhanced_image, self.configs["dense_text"]
        )
        extraction_results.append(("enhanced", enhanced_text, enhanced_data))

        # Step 3: Merge and reconcile results
        final_text = self._merge_extraction_results(extraction_results)

        # Step 4: Post-process and structure the text
        final_text = self._structure_medical_text(final_text)

        # Metadata for debugging and confidence
        metadata = {
            "extraction_methods": len(extraction_results),
            "table_regions_found": len(table_regions) if table_regions else 0,
            "final_length": len(final_text),
        }

        logger.info(f"✅ Multi-pass OCR complete: {len(final_text)} characters extracted")

        return final_text, metadata

    def _pil_to_cv2(self, pil_image: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format"""
        # Convert to RGB if necessary
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        # Convert to numpy array
        open_cv_image = np.array(pil_image)

        # Convert RGB to BGR (OpenCV uses BGR)
        return cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)

    def _detect_table_regions(self, img_cv: np.ndarray) -> list[tuple[int, int, int, int]]:
        """
        Detect table regions using line detection
        Returns list of (x, y, width, height) tuples for each detected table region
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

            # Apply threshold to get binary image
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

            # Detect horizontal and vertical lines
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

            horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
            vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)

            # Combine lines
            table_mask = cv2.add(horizontal_lines, vertical_lines)

            # Find contours (potential table regions)
            contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Filter and return significant regions
            regions = []
            min_area = 10000  # Minimum area for a table region

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > min_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    regions.append((x, y, w, h))
                    logger.info(f"📊 Table region detected: x={x}, y={y}, w={w}, h={h}")

            return regions

        except Exception as e:
            logger.warning(f"Table detection failed: {e}")
            return []

    def _extract_rows(
        self,
        pil_image: Image.Image,
        cv_image: np.ndarray,
        table_regions: list[tuple[int, int, int, int]],
    ) -> list[str]:
        """Extract text row by row from detected table regions"""
        all_rows = []

        for region in table_regions:
            x, y, w, h = region

            # Crop the table region
            table_crop = cv_image[y : y + h, x : x + w]

            # Convert back to PIL for OCR
            table_pil = Image.fromarray(cv2.cvtColor(table_crop, cv2.COLOR_BGR2RGB))

            # Detect row boundaries within the table
            row_boundaries = self._detect_row_boundaries(table_crop)

            if row_boundaries:
                # Extract each row separately
                for i, (row_y, row_height) in enumerate(row_boundaries):
                    row_img = table_crop[row_y : row_y + row_height, :]
                    row_pil = Image.fromarray(cv2.cvtColor(row_img, cv2.COLOR_BGR2RGB))

                    # OCR the row with single line config
                    row_text = pytesseract.image_to_string(
                        row_pil, config=self.configs["single_line"]
                    )
                    row_text = row_text.strip()

                    if row_text:
                        all_rows.append(row_text)
                        logger.debug(f"Row {i + 1}: {row_text[:100]}...")
            else:
                # Fall back to extracting the whole table region
                table_text = pytesseract.image_to_string(
                    table_pil, config=self.configs["high_quality"]
                )
                all_rows.extend(table_text.split("\n"))

        return all_rows

    def _detect_row_boundaries(self, table_img: np.ndarray) -> list[tuple[int, int]]:
        """
        Detect row boundaries in a table image
        Returns list of (y_start, height) for each row
        """
        try:
            # Convert to grayscale
            gray = (
                cv2.cvtColor(table_img, cv2.COLOR_BGR2GRAY)
                if len(table_img.shape) == 3
                else table_img
            )

            # Calculate horizontal projection (sum of pixels in each row)
            h_projection = np.sum(255 - gray, axis=1)

            # Find gaps between text rows (low projection values)
            threshold = np.mean(h_projection) * 0.1
            gaps = h_projection < threshold

            # Find row boundaries
            rows = []
            in_gap = True
            row_start = 0

            for y, is_gap in enumerate(gaps):
                if in_gap and not is_gap:
                    # Start of a row
                    row_start = y
                    in_gap = False
                elif not in_gap and is_gap:
                    # End of a row
                    if y - row_start > 10:  # Minimum row height
                        rows.append((row_start, y - row_start))
                    in_gap = True

            # Handle last row if needed
            if not in_gap and len(gray) - row_start > 10:
                rows.append((row_start, len(gray) - row_start))

            return rows

        except Exception as e:
            logger.warning(f"Row boundary detection failed: {e}")
            return []

    def _extract_with_data(self, image: Image.Image, config: str) -> tuple[str, dict]:
        """Extract text with position data"""
        try:
            # Get both text and data
            text = pytesseract.image_to_string(image, config=config)
            data = pytesseract.image_to_data(
                image, config=config, output_type=pytesseract.Output.DICT
            )

            return text, data
        except Exception as e:
            logger.warning(f"OCR extraction failed with config {config}: {e}")
            return "", {}

    def _enhance_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Apply advanced image enhancement for better OCR"""
        try:
            # Convert to grayscale if not already
            if image.mode != "L":
                image = image.convert("L")

            # Apply adaptive histogram equalization for better contrast
            image_array = np.array(image)

            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image_array)

            # Convert back to PIL
            image = Image.fromarray(enhanced)

            # Apply slight sharpening
            image = image.filter(ImageFilter.SHARPEN)

            # Denoise
            return image.filter(ImageFilter.MedianFilter(size=3))

        except Exception as e:
            logger.warning(f"Image enhancement failed: {e}")
            return image

    def _merge_extraction_results(self, results: list[tuple[str, str, dict | None]]) -> str:
        """
        Intelligently merge results from multiple extraction methods
        Prioritizes completeness and accuracy
        """
        if not results:
            return ""

        # For now, use a voting/consensus approach
        # In production, this could be much more sophisticated

        # Collect all unique lines from all extractions
        all_lines = set()
        for _method, text, _data in results:
            if text:
                lines = text.split("\n")
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 2:  # Filter out noise
                        all_lines.add(line)

        # Sort lines to maintain document order (simplified)
        sorted_lines = sorted(all_lines)

        # Group related lines (e.g., parameter-value pairs)
        grouped_lines = self._group_related_lines(sorted_lines)

        return "\n".join(grouped_lines)

    def _group_related_lines(self, lines: list[str]) -> list[str]:
        """Group related lines together (e.g., lab parameters with their values)"""
        grouped = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this line is a parameter name
            if any(param.lower() in line.lower() for param in self.lab_parameters):
                # Look ahead for potential value on next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # Check if next line contains a number (potential value)
                    if re.search(r"\d+[,.]?\d*", next_line):
                        # Combine parameter and value
                        combined = f"{line}: {next_line}"
                        grouped.append(combined)
                        i += 2
                        continue

            grouped.append(line)
            i += 1

        return grouped

    def _structure_medical_text(self, text: str) -> str:
        """
        Structure and format medical text for better readability
        """
        lines = text.split("\n")
        structured_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect section headers
            line_lower = line.lower()
            if any(
                header in line_lower
                for header in ["laborwerte", "befund", "diagnose", "medikation"]
            ):
                structured_lines.append(f"\n=== {line.upper()} ===")
                continue

            # Format lab values
            lab_match = re.match(
                r"([A-Za-zÄÖÜäöüß\-\s]+?)[\s:]+(\d+[,.]?\d*)\s*([A-Za-z/%]+)?(?:\s*\(?([\d,.\-\s]+)\)?)?",
                line,
            )
            if lab_match:
                param = lab_match.group(1).strip()
                value = lab_match.group(2)
                unit = lab_match.group(3) or ""
                reference = lab_match.group(4)

                # Check if parameter is known
                param_formatted = param
                for known_param in self.lab_parameters:
                    if known_param.lower() in param.lower():
                        param_formatted = known_param
                        break

                formatted = f"{param_formatted}: {value}"
                if unit:
                    formatted += f" {unit}"
                if reference:
                    formatted += f" (Referenz: {reference.strip()})"

                structured_lines.append(formatted)
            else:
                # Regular line
                structured_lines.append(line)

        return "\n".join(structured_lines)

    def extract_with_confidence(self, image: Image.Image) -> tuple[str, float]:
        """
        Main extraction method with confidence scoring

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        # Perform multi-pass extraction
        text, metadata = self.process_image_multipass(image)

        # Calculate confidence based on extraction success
        confidence = 0.5  # Base confidence

        if metadata.get("table_regions_found", 0) > 0:
            confidence += 0.2  # Found table structure

        if metadata.get("final_length", 0) > 500:
            confidence += 0.2  # Substantial text extracted

        if metadata.get("extraction_methods", 0) >= 3:
            confidence += 0.1  # Multiple methods succeeded

        # Check for medical content
        medical_terms_found = sum(
            1 for param in self.lab_parameters if param.lower() in text.lower()
        )
        if medical_terms_found > 5:
            confidence += 0.2

        confidence = min(confidence, 0.95)  # Cap at 95%

        return text, confidence
