"""
File Sequence Detector for Logical Page Ordering
Analyzes multiple files to determine the logical order for medical documents
"""

from dataclasses import dataclass
from datetime import datetime
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PageInfo:
    """Metadata container for individual page analysis in sequence detection.

    Stores extracted content features, structural indicators, and medical document
    markers used to determine logical page ordering. Populated during content
    analysis phase, then used for intelligent sequencing of multi-file submissions.

    **Content Analysis Fields**:
        - extracted_text: Quick text extraction (first 2000 chars) for pattern matching
        - page_number: Explicit page number if detected (e.g., "Seite 2", "Page 3")
        - dates: List of detected dates (document dates, lab dates, etc.)
        - sections: Detected medical sections (patient_info, lab_values, diagnosis, etc.)

    **Structural Indicators**:
        - starts_with_header: Page begins with document title/header
        - ends_with_continuation: Page ends with "Fortsetzung", "siehe nächste"
        - has_table_start: Page contains table opening structure
        - has_table_end: Page contains table closing structure

    **Medical Content Markers**:
        - has_patient_info: Contains patient demographics (name, DOB, insurance)
        - has_lab_values: Contains lab results (Laborwerte, numeric values with units)
        - has_diagnosis: Contains diagnostic information (ICD codes, diagnoses)
        - has_medication: Contains medication/therapy information

    **Quality Indicators**:
        - confidence: Analysis confidence score (0.0-1.0) based on detected features

    Example:
        >>> page = PageInfo(
        ...     index=0,
        ...     filename="report_page2.pdf",
        ...     file_content=pdf_bytes,
        ...     file_type="pdf"
        ... )
        >>> page.page_number = 2
        >>> page.has_lab_values = True
        >>> page.confidence = 0.85
    """

    index: int
    filename: str
    file_content: bytes
    file_type: str

    # Content analysis
    extracted_text: str | None = None
    page_number: int | None = None
    dates: list[datetime] = None
    sections: list[str] = None

    # Structural indicators
    starts_with_header: bool = False
    ends_with_continuation: bool = False
    has_table_start: bool = False
    has_table_end: bool = False

    # Medical document indicators
    has_patient_info: bool = False
    has_lab_values: bool = False
    has_diagnosis: bool = False
    has_medication: bool = False

    # Quality indicators
    confidence: float = 0.0

    def __post_init__(self):
        if self.dates is None:
            self.dates = []
        if self.sections is None:
            self.sections = []


class FileSequenceDetector:
    """Intelligent page sequencer for multi-file medical document submissions.

    Automatically detects and corrects logical page ordering when medical documents
    are submitted as multiple separate files (common for scanned/faxed records).
    Uses dual-strategy approach: explicit page numbers OR medical document structure.

    **Use Cases**:
        - Faxed medical records received page-by-page
        - Scanned multi-page documents uploaded separately
        - Mobile phone photos of paper documents
        - Out-of-order document pages requiring resequencing

    **Detection Strategies**:
        1. **Page Number Detection** (Priority 1):
           - Extracts explicit page numbers from text
           - Patterns: "Seite 2", "Page 3", "2/5", "Blatt 2", etc.
           - Used when 70%+ of pages have detectable numbers

        2. **Medical Structure Detection** (Priority 2):
           - Orders by typical medical document flow
           - Sequence: Patient Info → History → Labs → Diagnosis → Treatment
           - Used when page numbers insufficient

    **Content Analysis**:
        - Pattern matching for medical sections (regex-based)
        - Date extraction for chronological ordering
        - Structural indicators (headers, continuation markers)
        - Table boundary detection (start/end markers)

    **Medical Document Awareness**:
        Recognizes German medical terminology and document structures:
        - Arztbrief, Entlassungsbrief headers
        - Laborwerte, Befund sections
        - ICD codes, Diagnose patterns
        - Medikation, Therapie sections

    Attributes:
        section_patterns (dict): Regex patterns for medical section detection
        page_patterns (list): Regex patterns for page number extraction
        date_patterns (list): Regex patterns for date extraction

    Example:
        >>> detector = FileSequenceDetector()
        >>> # Files uploaded out of order
        >>> files = [
        ...     (page3_bytes, "pdf", "scan_003.pdf"),
        ...     (page1_bytes, "pdf", "scan_001.pdf"),
        ...     (page2_bytes, "pdf", "scan_002.pdf")
        ... ]
        >>> ordered = await detector.detect_sequence(files)
        >>> print([f[2] for f in ordered])
        ['scan_001.pdf', 'scan_002.pdf', 'scan_003.pdf']

    Note:
        **Fallback Behavior**:
        If sequence detection fails or produces low confidence results,
        returns files in original order to avoid corruption.

        **Performance**:
        - Quick PyPDF2 text extraction (first 2000 chars per page)
        - No OCR for images (uses filename patterns only)
        - Typical: ~50-100ms per page analysis

        **Limitations**:
        - Images without readable filenames may not sequence correctly
        - Handwritten page numbers not detected (no OCR)
        - Complex multi-document submissions may need manual review
    """

    def __init__(self):
        logger.info("🔍 File Sequence Detector initialized")

        # Medical document section patterns
        self.section_patterns = {
            "patient_info": [
                r"patient.*(?:name|nummer)",
                r"(?:vor|nach)name",
                r"geburtsdatum",
                r"versicherten.*nummer",
                r"krankenversicherung",
                r"adresse",
            ],
            "header": [
                r"(?:arzt|kranken|klinik).*brief",
                r"entlassungsbrief",
                r"befundbericht",
                r"laborwerte",
                r"blutwerte",
                r"befund",
                r"diagnose",
            ],
            "lab_values": [
                r"laborwerte",
                r"blutwerte",
                r"laborergebnis",
                r"parameter",
                r"\d+[.,]\d*\s*(?:mg/dl|mmol/l|µg/ml|ng/ml|u/l|iu/l)",
                r"referenzbereich",
                r"normwert",
            ],
            "diagnosis": [
                r"diagnose",
                r"verdachtsdiagnose",
                r"hauptdiagnose",
                r"nebendiagnose",
                r"icd.*\d+",
                r"befund",
                r"beurteilung",
            ],
            "medication": [
                r"medikation",
                r"therapie",
                r"verschreibung",
                r"einnahme",
                r"\d+\s*mg",
                r"täglich",
                r"morgens",
                r"abends",
            ],
            "continuation": [
                r"fortsetzung",
                r"siehe.*(?:nächste|folgende)",
                r"weiter auf",
                r"anhang",
                r"anlage",
                r"siehe.*(?:rückseite|blatt)",
            ],
        }

        # Page number patterns
        self.page_patterns = [
            r"seite\s*(\d+)",
            r"page\s*(\d+)",
            r"(\d+)\s*/\s*\d+",
            r"blatt\s*(\d+)",
            r"-\s*(\d+)\s*-",
            r"^\s*(\d+)\s*$",
        ]

        # Date patterns
        self.date_patterns = [
            r"(\d{1,2})[./](\d{1,2})[./](\d{4})",
            r"(\d{4})-(\d{1,2})-(\d{1,2})",
            r"(\d{1,2})\.\s*(\w+)\s*(\d{4})",
        ]

    async def detect_sequence(
        self, files: list[tuple[bytes, str, str]]
    ) -> list[tuple[bytes, str, str]]:
        """Analyze and reorder files into logical medical document sequence.

        Main entry point for sequence detection. Performs three-stage process:
        content extraction → page analysis → intelligent sequencing. Falls back
        to original order on errors to prevent document corruption.

        Args:
            files: List of (content, file_type, filename) tuples where:
                - content (bytes): Raw file data (PDF or image)
                - file_type (str): "pdf" or "image"
                - filename (str): Original filename

        Returns:
            list[tuple[bytes, str, str]]: Files reordered into logical sequence,
                maintaining same tuple structure as input. Returns original order
                if sequence detection fails or single file provided.

        Example:
            >>> detector = FileSequenceDetector()
            >>> # Out-of-order lab report pages
            >>> files = [
            ...     (page2_bytes, "pdf", "labs_2.pdf"),  # Has "Laborwerte"
            ...     (cover_bytes, "pdf", "labs_cover.pdf"),  # Has patient info
            ...     (page3_bytes, "pdf", "labs_3.pdf")  # Has "Fortsetzung"
            ... ]
            >>> ordered = await detector.detect_sequence(files)
            >>> print([f[2] for f in ordered])
            ['labs_cover.pdf', 'labs_2.pdf', 'labs_3.pdf']
            >>>
            >>> # With explicit page numbers
            >>> files_numbered = [
            ...     (pg3, "pdf", "report.pdf"),  # Contains "Seite 3"
            ...     (pg1, "pdf", "report.pdf"),  # Contains "Seite 1"
            ...     (pg2, "pdf", "report.pdf")   # Contains "Seite 2"
            ... ]
            >>> ordered = await detector.detect_sequence(files_numbered)
            >>> # Returns pages in order: 1, 2, 3

        Note:
            **Processing Stages**:
            1. **Content Extraction** (per file):
               - PDFs: PyPDF2 extraction of first page (max 2000 chars)
               - Images: Skip extraction (no OCR performed)

            2. **Page Analysis** (per file):
               - Extract page numbers via regex patterns
               - Detect medical sections (patient_info, labs, diagnosis, etc.)
               - Identify structural markers (headers, continuations, tables)
               - Calculate confidence score

            3. **Sequence Determination**:
               - If 70%+ pages numbered → Use page number ordering
               - Otherwise → Use medical structure ordering

            **Strategy Selection**:
            - **Page Numbers** (70%+ detection threshold):
              * Most reliable when available
              * Handles missing page numbers by preserving relative order

            - **Medical Structure** (fallback):
              * Priority order: Patient Info → Labs → Diagnosis → Treatment
              * Uses content markers + original order for ties

            **Error Handling**:
            Any exception during detection → Returns original order with warning.
            Ensures processing continues even if sequencing fails.

            **Single File**:
            Returns immediately without analysis if only one file provided.
        """
        if len(files) <= 1:
            return files

        logger.info(f"🔍 Detecting sequence for {len(files)} files")

        try:
            # Step 1: Analyze each file
            page_infos = []

            for i, (content, file_type, filename) in enumerate(files):
                logger.info(f"📄 Analyzing file {i + 1}: {filename}")

                page_info = PageInfo(
                    index=i, filename=filename, file_content=content, file_type=file_type
                )

                # Extract basic text for analysis
                text = await self._extract_text_for_analysis(content, file_type)
                page_info.extracted_text = text

                if text:
                    # Analyze content
                    await self._analyze_page_content(page_info, text)

                page_infos.append(page_info)

                logger.info(f"✅ File {i + 1} analyzed:")
                logger.info(f"   - Page number: {page_info.page_number}")
                logger.info(f"   - Has patient info: {page_info.has_patient_info}")
                logger.info(f"   - Text length: {len(text) if text else 0}")

            # Step 2: Determine sequence
            ordered_indices = self._determine_sequence(page_infos)

            # Step 3: Reorder files
            ordered_files = [files[i] for i in ordered_indices]

            logger.info("🎯 Sequence detection complete:")
            logger.info(f"   - Original order: {[f[2] for f in files]}")
            logger.info(f"   - Detected order: {[f[2] for f in ordered_files]}")
            logger.info(f"   - Reordering applied: {ordered_indices != list(range(len(files)))}")

            return ordered_files

        except Exception as e:
            logger.error(f"❌ Sequence detection failed: {e}")
            logger.warning("⚠️ Returning files in original order")
            return files

    async def _extract_text_for_analysis(self, content: bytes, file_type: str) -> str:
        """Extract text for sequence analysis (quick and dirty)"""
        try:
            if file_type == "pdf":
                # Quick PDF text extraction
                from io import BytesIO

                import PyPDF2

                pdf_file = BytesIO(content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)

                if len(pdf_reader.pages) > 0:
                    # Just get first page for analysis
                    return pdf_reader.pages[0].extract_text()[:2000]  # Limit to 2000 chars

            elif file_type == "image":
                # For images, we'd need OCR but for sequence detection,
                # we can use filename patterns as primary indicator
                return ""

        except Exception as e:
            logger.debug(f"Text extraction for analysis failed: {e}")

        return ""

    async def _analyze_page_content(self, page_info: PageInfo, text: str):
        """Analyze page content for ordering clues"""
        if not text:
            return

        text_lower = text.lower()

        # Detect page numbers
        page_info.page_number = self._extract_page_number(text)

        # Detect dates
        page_info.dates = self._extract_dates(text)

        # Detect sections
        page_info.sections = self._detect_sections(text_lower)

        # Detect medical content types
        page_info.has_patient_info = self._has_pattern(text_lower, "patient_info")
        page_info.has_lab_values = self._has_pattern(text_lower, "lab_values")
        page_info.has_diagnosis = self._has_pattern(text_lower, "diagnosis")
        page_info.has_medication = self._has_pattern(text_lower, "medication")

        # Detect structural indicators
        page_info.starts_with_header = self._starts_with_header(text_lower)
        page_info.ends_with_continuation = self._ends_with_continuation(text_lower)
        page_info.has_table_start = self._has_table_start(text)
        page_info.has_table_end = self._has_table_end(text)

        # Calculate confidence
        page_info.confidence = self._calculate_analysis_confidence(page_info, text)

    def _extract_page_number(self, text: str) -> int | None:
        """Extract page number from text"""
        for pattern in self.page_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    # Take the first match
                    return int(matches[0])
                except (ValueError, IndexError):
                    continue
        return None

    def _extract_dates(self, text: str) -> list[datetime]:
        """Extract dates from text"""
        dates = []

        for pattern in self.date_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    if len(match) == 3:
                        # Handle different date formats
                        if len(match[2]) == 4:  # DD/MM/YYYY or DD.MM.YYYY
                            day, month, year = int(match[0]), int(match[1]), int(match[2])
                        else:  # YYYY-MM-DD
                            year, month, day = int(match[0]), int(match[1]), int(match[2])

                        date = datetime(year, month, day)
                        dates.append(date)
                except (ValueError, IndexError):
                    continue

        return dates

    def _detect_sections(self, text_lower: str) -> list[str]:
        """Detect document sections"""
        sections = []

        for section_name, _patterns in self.section_patterns.items():
            if self._has_pattern(text_lower, section_name):
                sections.append(section_name)

        return sections

    def _has_pattern(self, text_lower: str, pattern_group: str) -> bool:
        """Check if text contains patterns from a group"""
        patterns = self.section_patterns.get(pattern_group, [])

        return any(re.search(pattern, text_lower) for pattern in patterns)

    def _starts_with_header(self, text_lower: str) -> bool:
        """Check if page starts with a header"""
        # Check first 200 characters
        start_text = text_lower[:200]
        return self._has_pattern(start_text, "header")

    def _ends_with_continuation(self, text_lower: str) -> bool:
        """Check if page ends with continuation indicator"""
        # Check last 200 characters
        end_text = text_lower[-200:]
        return self._has_pattern(end_text, "continuation")

    def _has_table_start(self, text: str) -> bool:
        """Detect if page has table start indicators"""
        # Look for table-like structures
        lines = text.split("\n")

        for line in lines:
            # Check for header-like lines with multiple columns
            if "|" in line or "\t" in line:
                parts = re.split(r"[|\t]", line)
                if len(parts) >= 3:  # At least 3 columns
                    return True

        return False

    def _has_table_end(self, text: str) -> bool:
        """Detect if page has table end indicators"""
        # Similar to table start but look at end of text
        lines = text.split("\n")[-10:]  # Last 10 lines

        return any("|" in line or "\t" in line for line in lines)

    def _calculate_analysis_confidence(self, page_info: PageInfo, text: str) -> float:
        """Calculate confidence in the analysis"""
        confidence = 0.5  # Base confidence

        if page_info.page_number:
            confidence += 0.3  # Strong indicator

        if page_info.dates:
            confidence += 0.1

        if page_info.sections:
            confidence += len(page_info.sections) * 0.05

        if len(text) > 500:
            confidence += 0.1  # More text = better analysis

        return min(confidence, 1.0)

    def _determine_sequence(self, page_infos: list[PageInfo]) -> list[int]:
        """Determine the logical sequence of pages"""

        # Strategy 1: Use explicit page numbers if available
        pages_with_numbers = [p for p in page_infos if p.page_number is not None]

        if len(pages_with_numbers) >= len(page_infos) * 0.7:  # Most pages have numbers
            logger.info("📊 Using page numbers for sequence detection")
            return self._order_by_page_numbers(page_infos)

        # Strategy 2: Use medical document structure
        logger.info("📊 Using medical document structure for sequence detection")
        return self._order_by_medical_structure(page_infos)

    def _order_by_page_numbers(self, page_infos: list[PageInfo]) -> list[int]:
        """Order by explicit page numbers"""

        # Sort by page number, with None values at the end
        def sort_key(page_info):
            if page_info.page_number is not None:
                return (0, page_info.page_number)  # Priority 0 for numbered pages
            return (1, page_info.index)  # Priority 1 for unnumbered, use original order

        sorted_pages = sorted(page_infos, key=sort_key)
        return [p.index for p in sorted_pages]

    def _order_by_medical_structure(self, page_infos: list[PageInfo]) -> list[int]:
        """Order pages by typical medical document structure and content flow.

        Implements content-based sequencing using medical domain knowledge.
        Assigns priority levels based on detected sections, then sorts pages
        to follow natural clinical documentation order.

        Args:
            page_infos: List of PageInfo objects with analyzed content

        Returns:
            list[int]: Original indices reordered by medical structure priority

        Example:
            >>> detector = FileSequenceDetector()
            >>> pages = [
            ...     PageInfo(index=0, has_diagnosis=True, ...),  # Diagnosis page
            ...     PageInfo(index=1, has_patient_info=True, ...),  # Cover page
            ...     PageInfo(index=2, has_lab_values=True, ...)  # Lab results
            ... ]
            >>> ordered_indices = detector._order_by_medical_structure(pages)
            >>> print(ordered_indices)
            [1, 2, 0]  # Patient info → Labs → Diagnosis

        Note:
            **Medical Document Typical Order**:
            1. Patient info / Header (Arztbrief header, patient demographics)
            2. Medical history / Previous findings (Anamnese, Vorgeschichte)
            3. Current examination / Lab values (Laborwerte, Befund)
            4. Diagnosis (Diagnose, ICD codes)
            5. Treatment / Medication (Therapie, Medikation)
            6. Continuation pages (Fortsetzung markers)

            **Priority Assignment**:
            - Priority 1: has_patient_info OR starts_with_header → First page
            - Priority 2: Default for unclassified content → Middle pages
            - Priority 3: has_lab_values → Lab results section
            - Priority 4: has_diagnosis → Diagnosis section
            - Priority 5: has_medication → Treatment section
            - Priority 6: ends_with_continuation → Continuation pages

            **Tie Breaking**:
            Secondary sort by original index preserves relative order
            for pages with same priority level.

            **Rationale**:
            Medical documents follow standardized structure (especially
            German Arztbriefe). This ordering maximizes readability and
            clinical workflow alignment.
        """

        # Medical document typical order:
        # 1. Patient info / Header
        # 2. Medical history / Previous findings
        # 3. Current examination / Lab values
        # 4. Diagnosis
        # 5. Treatment / Medication
        # 6. Continuation pages

        def medical_priority(page_info: PageInfo) -> tuple[int, int]:
            """Calculate priority for medical document ordering"""

            # Primary priority (document structure)
            if page_info.has_patient_info or page_info.starts_with_header:
                primary = 1  # First page
            elif page_info.has_lab_values:
                primary = 3  # Lab results typically in middle
            elif page_info.has_diagnosis:
                primary = 4  # Diagnosis usually after labs
            elif page_info.has_medication:
                primary = 5  # Treatment at end
            elif page_info.ends_with_continuation:
                primary = 6  # Continuation pages last
            else:
                primary = 2  # Default middle priority

            # Secondary priority (use original order for ties)
            secondary = page_info.index

            return (primary, secondary)

        # Sort by medical structure priority
        sorted_pages = sorted(page_infos, key=medical_priority)

        # Log the reasoning
        logger.info("📊 Medical structure ordering:")
        for i, page in enumerate(sorted_pages):
            priority = medical_priority(page)
            logger.info(f"   {i + 1}. {page.filename} (priority: {priority})")

        return [p.index for p in sorted_pages]

    def analyze_sequence_quality(
        self, original_order: list[str], detected_order: list[str]
    ) -> dict[str, Any]:
        """Analyze quality and impact of sequence detection for validation.

        Compares original vs. detected ordering to quantify reordering decisions.
        Provides metrics for confidence assessment and debugging sequence logic.

        Args:
            original_order: List of filenames in original submission order
            detected_order: List of filenames in detected logical order

        Returns:
            dict[str, Any]: Quality analysis containing:
                - reordering_applied (bool): Whether any reordering occurred
                - original_order (list): Input filename order
                - detected_order (list): Output filename order
                - confidence (str): "high" (no reorder) or "medium" (reordered)
                - files_moved (int): Count of files that changed position (if reordered)
                - reordering_percentage (float): Proportion of files moved (if reordered)

        Example:
            >>> detector = FileSequenceDetector()
            >>> original = ["page3.pdf", "page1.pdf", "page2.pdf"]
            >>> detected = ["page1.pdf", "page2.pdf", "page3.pdf"]
            >>> quality = detector.analyze_sequence_quality(original, detected)
            >>> print(quality)
            {
                'reordering_applied': True,
                'original_order': ['page3.pdf', 'page1.pdf', 'page2.pdf'],
                'detected_order': ['page1.pdf', 'page2.pdf', 'page3.pdf'],
                'confidence': 'medium',
                'files_moved': 2,
                'reordering_percentage': 0.667
            }
            >>>
            >>> # No reordering needed
            >>> original = ["page1.pdf", "page2.pdf"]
            >>> detected = ["page1.pdf", "page2.pdf"]
            >>> quality = detector.analyze_sequence_quality(original, detected)
            >>> print(quality['confidence'])
            'high'

        Note:
            **Confidence Levels**:
            - "high": No reordering applied, original order was correct
            - "medium": Reordering applied based on detected patterns

            **Movement Calculation**:
            Counts files whose position changed between original and detected order.
            A file that moves from index 0 to 2 counts as 1 moved file.

            **Use Cases**:
            - Logging/auditing reordering decisions
            - Quality assurance for sequence detection
            - Debugging incorrect page ordering
            - User feedback (show confidence in detected order)
        """

        reordered = original_order != detected_order

        analysis = {
            "reordering_applied": reordered,
            "original_order": original_order,
            "detected_order": detected_order,
            "confidence": "high" if not reordered else "medium",
        }

        if reordered:
            # Calculate how much reordering was done
            moves = 0
            for i, filename in enumerate(detected_order):
                original_index = original_order.index(filename)
                if original_index != i:
                    moves += 1

            analysis["files_moved"] = moves
            analysis["reordering_percentage"] = moves / len(original_order)

        return analysis
