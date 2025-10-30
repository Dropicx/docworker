"""
Markdown Table Formatter for Medical OCR

Converts OCR-extracted table data into clean markdown format for better AI comprehension.
Specializes in medical laboratory results and clinical data tables.
"""

import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)


class MarkdownTableFormatter:
    """Converts OCR table data to markdown format for improved AI understanding"""

    def __init__(self):
        # Common medical lab parameters for header detection
        self.medical_headers = {
            "parameter": ["parameter", "test", "untersuchung", "wert", "messwert"],
            "value": ["wert", "ergebnis", "resultat", "result", "value", "messwert"],
            "unit": ["einheit", "unit", "maßeinheit"],
            "reference": [
                "referenz",
                "normalwert",
                "norm",
                "reference",
                "referenzbereich",
                "grenzwert",
            ],
        }

        # Medical parameter patterns for row classification
        self.medical_parameters = [
            "hämoglobin",
            "hämatokrit",
            "erythrozyten",
            "leukozyten",
            "thrombozyten",
            "glucose",
            "kreatinin",
            "harnstoff",
            "natrium",
            "kalium",
            "chlorid",
            "tsh",
            "ft3",
            "ft4",
            "cholesterin",
            "triglyceride",
            "bilirubin",
            "albumin",
            "protein",
        ]

    def format_table(self, ocr_data: dict, text: str) -> str | None:
        """
        Format OCR data as markdown table.

        Args:
            ocr_data: OCR data with position information (from pytesseract)
            text: Raw OCR text as fallback

        Returns:
            Markdown-formatted table string or None if conversion fails
        """
        try:
            if not ocr_data or "text" not in ocr_data:
                logger.warning("No OCR data available for markdown formatting")
                return None

            # Extract words with positions
            words = self._extract_positioned_words(ocr_data)
            if not words:
                logger.warning("No words extracted from OCR data")
                return None

            # Detect if this is actually a table
            if not self._is_table_structure(words):
                logger.debug("OCR data does not appear to be a table")
                return None

            # Group words into rows and columns
            rows = self._group_into_rows(words)
            if len(rows) < 2:  # Need at least header + 1 data row
                logger.debug(f"Insufficient rows for table: {len(rows)}")
                return None

            # Detect columns
            columns = self._detect_columns(rows)
            if len(columns) < 2:  # Need at least 2 columns
                logger.debug(f"Insufficient columns for table: {len(columns)}")
                return None

            # Build table structure
            table_data = self._build_table_structure(rows, columns)
            if not table_data:
                return None

            # Format as markdown
            markdown = self._format_as_markdown(table_data)

            logger.info(f"✅ Successfully formatted table with {len(table_data)} rows")
            return markdown

        except Exception as e:
            logger.error(f"❌ Markdown table formatting failed: {e}")
            return None

    def _extract_positioned_words(self, ocr_data: dict) -> list[dict]:
        """Extract words with position information from OCR data"""
        words = []

        for i in range(len(ocr_data["text"])):
            word_text = ocr_data["text"][i].strip()
            confidence = int(ocr_data.get("conf", [0])[i])

            # Skip empty words and very low confidence
            if not word_text or confidence < 20:
                continue

            words.append(
                {
                    "text": word_text,
                    "left": ocr_data["left"][i],
                    "top": ocr_data["top"][i],
                    "width": ocr_data["width"][i],
                    "height": ocr_data["height"][i],
                    "right": ocr_data["left"][i] + ocr_data["width"][i],
                    "bottom": ocr_data["top"][i] + ocr_data["height"][i],
                    "confidence": confidence,
                }
            )

        return words

    def _is_table_structure(self, words: list[dict]) -> bool:
        """Check if words form a table-like structure"""
        if len(words) < 6:  # Too few words for a table
            return False

        # Group by Y position to find rows
        rows = defaultdict(list)
        for word in words:
            y_key = round(word["top"] / 10) * 10  # 10px grouping tolerance
            rows[y_key].append(word)

        # Check if we have multiple rows with similar column structure
        if len(rows) < 2:
            return False

        # Check if rows have consistent column count
        row_widths = [len(row) for row in rows.values()]
        avg_width = sum(row_widths) / len(row_widths)

        # Most rows should have similar word counts (±50%)
        consistent_rows = sum(1 for w in row_widths if abs(w - avg_width) < avg_width * 0.5)

        return consistent_rows >= len(rows) * 0.6  # 60% of rows should be consistent

    def _group_into_rows(self, words: list[dict]) -> list[list[dict]]:
        """Group words into rows based on Y position"""
        # Sort words by Y position
        sorted_words = sorted(words, key=lambda w: w["top"])

        rows = []
        current_row = [sorted_words[0]]
        current_y = sorted_words[0]["top"]
        row_tolerance = sorted_words[0]["height"] * 0.5  # Half line height

        for word in sorted_words[1:]:
            if abs(word["top"] - current_y) <= row_tolerance:
                # Same row
                current_row.append(word)
            else:
                # New row - sort current row by X position
                current_row.sort(key=lambda w: w["left"])
                rows.append(current_row)
                current_row = [word]
                current_y = word["top"]

        # Don't forget last row
        if current_row:
            current_row.sort(key=lambda w: w["left"])
            rows.append(current_row)

        return rows

    def _detect_columns(self, rows: list[list[dict]]) -> list[int]:
        """Detect column positions from row data"""
        # Collect all X positions
        all_x_positions = []
        for row in rows:
            for word in row:
                all_x_positions.append(word["left"])

        if not all_x_positions:
            return []

        # Sort and cluster X positions
        all_x_positions.sort()

        columns = [all_x_positions[0]]
        min_column_gap = 30  # Minimum pixels between columns

        for x in all_x_positions:
            if x - columns[-1] > min_column_gap:
                columns.append(x)

        return columns

    def _build_table_structure(
        self, rows: list[list[dict]], columns: list[int]
    ) -> list[list[str]]:
        """Build 2D table structure by assigning words to cells"""
        table = []

        for row_words in rows:
            row_cells = [""] * len(columns)

            for word in row_words:
                # Find which column this word belongs to
                col_idx = self._find_column_index(word["left"], columns)
                if col_idx < len(row_cells):
                    if row_cells[col_idx]:
                        row_cells[col_idx] += " " + word["text"]
                    else:
                        row_cells[col_idx] = word["text"]

            # Only add rows with at least 2 non-empty cells
            non_empty = sum(1 for cell in row_cells if cell)
            if non_empty >= 2:
                table.append(row_cells)

        return table

    def _find_column_index(self, x_position: int, columns: list[int]) -> int:
        """Find which column an X position belongs to"""
        for i, col_x in enumerate(columns):
            if i == len(columns) - 1:  # Last column
                return i
            if col_x <= x_position < columns[i + 1]:
                return i
        return 0

    def _format_as_markdown(self, table_data: list[list[str]]) -> str:
        """Format table data as markdown"""
        if not table_data:
            return ""

        # Detect or create headers
        headers = self._detect_headers(table_data)

        # Build markdown table
        lines = []

        # Add section header
        lines.append("\n### Laboratory Results\n")

        # Header row
        lines.append("| " + " | ".join(headers) + " |")

        # Separator row
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Data rows (skip first row if it was used as header)
        start_idx = 1 if self._first_row_is_header(table_data[0]) else 0

        for row in table_data[start_idx:]:
            # Pad row to match header length
            padded_row = row + [""] * (len(headers) - len(row))
            # Trim row if longer than headers
            padded_row = padded_row[: len(headers)]

            lines.append("| " + " | ".join(padded_row) + " |")

        return "\n".join(lines)

    def _detect_headers(self, table_data: list[list[str]]) -> list[str]:
        """Detect or generate appropriate headers"""
        if not table_data:
            return []

        first_row = table_data[0]

        # Check if first row looks like headers
        if self._first_row_is_header(first_row):
            return first_row

        # Generate default headers based on content
        num_cols = len(first_row)

        # Try to infer column types from content
        headers = []
        for col_idx in range(num_cols):
            # Check first few rows to determine column type
            sample_values = [
                row[col_idx] if col_idx < len(row) else "" for row in table_data[:3]
            ]

            if col_idx == 0:
                # First column is usually parameter name
                headers.append("Parameter")
            elif any(self._is_numeric(val) for val in sample_values):
                # Column contains numbers - likely value
                headers.append("Value")
            elif any(self._is_unit(val) for val in sample_values):
                # Column contains units
                headers.append("Unit")
            elif any(
                "-" in val or "bis" in val.lower() or "to" in val.lower()
                for val in sample_values
            ):
                # Column contains ranges - reference values
                headers.append("Reference Range")
            else:
                headers.append(f"Column {col_idx + 1}")

        return headers

    def _first_row_is_header(self, first_row: list[str]) -> bool:
        """Check if first row appears to be headers"""
        if not first_row:
            return False

        # Check if words match common header terms
        header_matches = 0
        for cell in first_row:
            cell_lower = cell.lower()
            for header_type, keywords in self.medical_headers.items():
                if any(keyword in cell_lower for keyword in keywords):
                    header_matches += 1
                    break

        # If more than half the cells look like headers
        return header_matches >= len(first_row) / 2

    def _is_numeric(self, text: str) -> bool:
        """Check if text is numeric or contains numeric value"""
        if not text:
            return False
        # Remove spaces and common separators
        cleaned = text.replace(" ", "").replace(",", ".")
        return bool(re.search(r"\d+\.?\d*", cleaned))

    def _is_unit(self, text: str) -> bool:
        """Check if text looks like a measurement unit"""
        if not text:
            return False

        text_lower = text.lower()

        # Common medical units
        units = [
            "mg/dl",
            "mmol/l",
            "g/dl",
            "g/l",
            "µg/l",
            "ng/ml",
            "pg/ml",
            "u/l",
            "iu/l",
            "mU/l",
            "/µl",
            "%",
            "mg",
            "ml",
            "g",
            "µg",
            "ng",
        ]

        return any(unit in text_lower for unit in units)

    def format_lab_results_text(self, text: str) -> str:
        """
        Fallback method to format text-based lab results when position data is unavailable.

        Args:
            text: Raw OCR text

        Returns:
            Markdown-formatted text
        """
        lines = text.split("\n")
        formatted_lines = []
        in_table = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line looks like a lab result
            if self._looks_like_lab_result_line(line):
                if not in_table:
                    # Start table
                    formatted_lines.append("\n### Laboratory Results\n")
                    formatted_lines.append("| Parameter | Value | Unit | Reference Range |")
                    formatted_lines.append("| --- | --- | --- | --- |")
                    in_table = True

                # Parse and format as table row
                row = self._parse_lab_result_line(line)
                if row:
                    formatted_lines.append(f"| {' | '.join(row)} |")
            else:
                if in_table:
                    formatted_lines.append("")  # End table with blank line
                    in_table = False
                formatted_lines.append(line)

        return "\n".join(formatted_lines)

    def _looks_like_lab_result_line(self, line: str) -> bool:
        """Check if line looks like a laboratory result"""
        line_lower = line.lower()

        # Check for medical parameters
        has_param = any(param in line_lower for param in self.medical_parameters)

        # Check for numeric values
        has_number = bool(re.search(r"\d+[.,]?\d*", line))

        # Check for units
        has_unit = self._is_unit(line)

        return (has_param or has_unit) and has_number

    def _parse_lab_result_line(self, line: str) -> list[str] | None:
        """Parse a lab result line into table columns"""
        try:
            # Try to split by multiple spaces or tabs
            parts = re.split(r"\s{2,}|\t+", line)
            parts = [p.strip() for p in parts if p.strip()]

            if len(parts) < 2:
                return None

            # Ensure we have 4 columns (pad with empty strings)
            while len(parts) < 4:
                parts.append("")

            # Trim to 4 columns if more
            return parts[:4]

        except Exception:
            return None
