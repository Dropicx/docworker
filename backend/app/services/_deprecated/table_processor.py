"""
Advanced table processing for OCR text extraction
Specializes in detecting and formatting medical tables from OCR output
"""

import re
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class TableProcessor:
    """Processes OCR output to better handle table structures"""

    def __init__(self):
        self.min_column_gap = 2  # Minimum spaces between columns
        self.column_alignment_tolerance = 30  # Pixels for column alignment

    def process_ocr_output(self, text: str, ocr_data: Optional[dict] = None) -> str:
        """
        Main entry point for table processing

        Args:
            text: Raw OCR text output
            ocr_data: Optional OCR data with position information

        Returns:
            Formatted text with improved table structure
        """
        if ocr_data:
            # Use position data for better table reconstruction
            return self._process_with_position_data(text, ocr_data)
        else:
            # Fallback to heuristic processing
            return self._process_heuristic(text)

    def _process_with_position_data(self, text: str, ocr_data: dict) -> str:
        """Process using OCR position data for accurate table reconstruction"""
        try:
            if not ocr_data or 'text' not in ocr_data:
                return self._process_heuristic(text)

            # Extract words with positions
            words = []
            for i in range(len(ocr_data['text'])):
                word_text = ocr_data['text'][i].strip()
                if word_text:
                    words.append({
                        'text': word_text,
                        'left': ocr_data['left'][i],
                        'top': ocr_data['top'][i],
                        'width': ocr_data['width'][i],
                        'height': ocr_data['height'][i],
                        'right': ocr_data['left'][i] + ocr_data['width'][i],
                        'bottom': ocr_data['top'][i] + ocr_data['height'][i]
                    })

            if not words:
                return text

            # Group words into lines based on Y position
            lines = self._group_into_lines(words)

            # Detect column structure
            columns = self._detect_columns(words)

            # Reconstruct table
            formatted_lines = []
            for line_words in lines:
                if len(line_words) > 1:
                    # This might be a table row
                    formatted_line = self._format_table_row(line_words, columns)
                    formatted_lines.append(formatted_line)
                else:
                    # Single word line, just add it
                    formatted_lines.append(line_words[0]['text'])

            result = '\n'.join(formatted_lines)

            # Apply medical formatting
            result = self._format_medical_values(result)

            logger.info(f"📊 Table processing complete: {len(lines)} lines, {len(columns)} columns detected")

            return result

        except Exception as e:
            logger.error(f"Position-based processing failed: {e}")
            return self._process_heuristic(text)

    def _group_into_lines(self, words: list[Dict]) -> list[list[Dict]]:
        """Group words into lines based on Y position"""
        if not words:
            return []

        # Sort by Y position
        words = sorted(words, key=lambda w: w['top'])

        lines = []
        current_line = [words[0]]
        current_y = words[0]['top']
        line_tolerance = 15  # Pixels tolerance for same line

        for word in words[1:]:
            if abs(word['top'] - current_y) <= line_tolerance:
                # Same line
                current_line.append(word)
            else:
                # New line
                # Sort current line by X position
                current_line.sort(key=lambda w: w['left'])
                lines.append(current_line)
                current_line = [word]
                current_y = word['top']

        # Don't forget the last line
        if current_line:
            current_line.sort(key=lambda w: w['left'])
            lines.append(current_line)

        return lines

    def _detect_columns(self, words: list[Dict]) -> list[int]:
        """Detect column positions from word alignments"""
        # Collect all X positions
        x_positions = {}
        for word in words:
            x = word['left']
            if x not in x_positions:
                x_positions[x] = 0
            x_positions[x] += 1

        # Cluster X positions to find columns
        columns = []
        tolerance = self.column_alignment_tolerance

        for x, count in sorted(x_positions.items()):
            # Check if this X is close to an existing column
            found_column = False
            for i, col_x in enumerate(columns):
                if abs(x - col_x) <= tolerance:
                    # Update column position to weighted average
                    columns[i] = (col_x * len(columns) + x * count) // (len(columns) + count)
                    found_column = True
                    break

            if not found_column and count >= 2:  # At least 2 items to be a column
                columns.append(x)

        return sorted(columns)

    def _format_table_row(self, line_words: list[Dict], columns: list[int]) -> str:
        """Format a line of words as a table row"""
        if not columns:
            # No column structure detected, join with spaces
            return ' '.join([w['text'] for w in line_words])

        # Assign words to columns
        row_data = [''] * len(columns)

        for word in line_words:
            # Find the best matching column
            best_col = 0
            min_distance = float('inf')

            for i, col_x in enumerate(columns):
                distance = abs(word['left'] - col_x)
                if distance < min_distance:
                    min_distance = distance
                    best_col = i

            # Add word to the appropriate column
            if row_data[best_col]:
                row_data[best_col] += ' ' + word['text']
            else:
                row_data[best_col] = word['text']

        # Format as pipe-separated values
        return ' | '.join(row_data).strip()

    def _process_heuristic(self, text: str) -> str:
        """Fallback heuristic processing without position data"""
        lines = text.split('\n')
        formatted_lines = []

        for line in lines:
            if not line.strip():
                continue

            # Check if line might be a table row
            # Look for multiple data points separated by spaces
            parts = re.split(r'\s{2,}', line.strip())

            if len(parts) >= 2:
                # Might be a table row
                # Check if it contains numbers (common in medical tables)
                has_numbers = any(re.search(r'\d+[,.]?\d*', part) for part in parts)

                if has_numbers:
                    # Format as table row
                    formatted_line = ' | '.join(parts)
                    formatted_lines.append(formatted_line)
                else:
                    formatted_lines.append(line.strip())
            else:
                formatted_lines.append(line.strip())

        result = '\n'.join(formatted_lines)

        # Apply medical formatting
        result = self._format_medical_values(result)

        return result

    def _format_medical_values(self, text: str) -> str:
        """Format medical values and lab results"""
        # Pattern for lab values: Parameter | Value | Unit | Reference
        text = re.sub(
            r'([A-Za-zÄÖÜäöüß\-]+)\s*\|\s*([\d,\.]+)\s*\|?\s*([A-Za-z/%]+)?\s*\|?\s*([\d,\.\-\s]+)?',
            lambda m: self._format_lab_value(m),
            text
        )

        # Pattern for simple parameter: value unit
        text = re.sub(
            r'\b([A-Za-zÄÖÜäöüß\-]+):\s*([\d,\.]+)\s*([A-Za-z/%]+)?',
            lambda m: f"{m.group(1)}: {m.group(2)} {m.group(3) or ''}".strip(),
            text
        )

        return text

    def _format_lab_value(self, match) -> str:
        """Format a lab value match"""
        param = match.group(1)
        value = match.group(2)
        unit = match.group(3) or ''
        reference = match.group(4)

        result = f"{param}: {value}"
        if unit:
            result += f" {unit}"
        if reference:
            result += f" (Referenz: {reference.strip()})"

        return result

    def detect_table_structure(self, ocr_data: dict) -> bool:
        """
        Detect if OCR data contains a table structure

        Returns:
            True if table structure is detected
        """
        try:
            if not ocr_data or 'text' not in ocr_data:
                return False

            # Extract words with positions
            words = []
            for i in range(len(ocr_data['text'])):
                if ocr_data['text'][i].strip():
                    words.append({
                        'left': ocr_data['left'][i],
                        'top': ocr_data['top'][i]
                    })

            if len(words) < 4:
                return False

            # Group into lines
            lines = {}
            line_tolerance = 15

            for word in words:
                y = word['top']
                found_line = False
                for line_y in lines.keys():
                    if abs(line_y - y) < line_tolerance:
                        lines[line_y].append(word)
                        found_line = True
                        break
                if not found_line:
                    lines[y] = [word]

            # Check for multiple words per line (table indicator)
            multi_word_lines = sum(1 for line in lines.values() if len(line) >= 2)

            # Check for column alignment
            x_positions = [w['left'] for w in words]
            x_clusters = []

            for x in x_positions:
                found_cluster = False
                for cluster in x_clusters:
                    if abs(cluster[0] - x) < self.column_alignment_tolerance:
                        cluster.append(x)
                        found_cluster = True
                        break
                if not found_cluster:
                    x_clusters.append([x])

            # Count significant columns
            significant_columns = sum(1 for c in x_clusters if len(c) >= 2)

            # Table detection criteria
            is_table = (multi_word_lines >= 2 and significant_columns >= 2) or \
                      (multi_word_lines >= 3) or \
                      (significant_columns >= 3)

            if is_table:
                logger.info(f"📊 Table detected: {multi_word_lines} multi-word lines, {significant_columns} columns")

            return is_table

        except Exception as e:
            logger.debug(f"Table detection error: {e}")
            return False