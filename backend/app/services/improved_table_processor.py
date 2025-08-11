"""
Improved table processing for medical OCR text extraction
Focuses on extracting meaningful content rather than preserving exact table structure
"""

import re
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class ImprovedTableProcessor:
    """Processes OCR output to extract meaningful content from medical tables"""
    
    def __init__(self):
        self.min_column_gap = 2
        self.column_alignment_tolerance = 30
        # Common medical lab parameters for better recognition
        self.medical_parameters = {
            'hemoglobin': ['hämoglobin', 'hb', 'hemoglobin'],
            'hematocrit': ['hämatokrit', 'hkt', 'hct'],
            'erythrocytes': ['erythrozyten', 'ery', 'rbc'],
            'leukocytes': ['leukozyten', 'leuko', 'wbc'],
            'thrombocytes': ['thrombozyten', 'thrombo', 'plt'],
            'glucose': ['glukose', 'glucose', 'blutzucker'],
            'creatinine': ['kreatinin', 'crea', 'krea'],
            'urea': ['harnstoff', 'urea'],
            'sodium': ['natrium', 'na', 'sodium'],
            'potassium': ['kalium', 'k', 'potassium'],
            'chloride': ['chlorid', 'cl'],
            'tsh': ['tsh', 'thyreotropin'],
            'ft3': ['ft3', 'freies t3'],
            'ft4': ['ft4', 'freies t4'],
        }
        
    def process_ocr_output(self, text: str, ocr_data: Optional[dict] = None) -> str:
        """
        Main entry point for improved table processing
        
        Args:
            text: Raw OCR text output
            ocr_data: Optional OCR data with position information
            
        Returns:
            Cleaned and formatted text optimized for AI understanding
        """
        if ocr_data and self._has_good_quality_data(ocr_data):
            # Use position data for better reconstruction
            result = self._process_with_position_data(text, ocr_data)
        else:
            # Fallback to text-based cleaning
            result = self._clean_ocr_text(text)
        
        # Apply medical-specific formatting
        result = self._enhance_medical_content(result)
        
        return result
    
    def _has_good_quality_data(self, ocr_data: dict) -> bool:
        """Check if OCR data has good enough quality for position-based processing"""
        try:
            if not ocr_data or 'conf' not in ocr_data:
                return False
            
            # Calculate average confidence
            confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Only use position data if confidence is good
            return avg_confidence > 60
        except:
            return False
    
    def _process_with_position_data(self, text: str, ocr_data: dict) -> str:
        """Process using OCR position data for better reconstruction"""
        try:
            # Extract words with positions and confidence
            words = []
            for i in range(len(ocr_data['text'])):
                word_text = ocr_data['text'][i].strip()
                confidence = int(ocr_data['conf'][i])
                
                # Only include words with reasonable confidence
                if word_text and confidence > 30:
                    words.append({
                        'text': word_text,
                        'left': ocr_data['left'][i],
                        'top': ocr_data['top'][i],
                        'width': ocr_data['width'][i],
                        'height': ocr_data['height'][i],
                        'confidence': confidence
                    })
            
            if not words:
                return self._clean_ocr_text(text)
            
            # Group words into logical lines
            lines = self._group_into_semantic_lines(words)
            
            # Reconstruct text focusing on readability
            formatted_lines = []
            for line_words in lines:
                line_text = self._reconstruct_line(line_words)
                if line_text:
                    formatted_lines.append(line_text)
            
            return '\n'.join(formatted_lines)
            
        except Exception as e:
            logger.error(f"Position-based processing failed: {e}")
            return self._clean_ocr_text(text)
    
    def _group_into_semantic_lines(self, words: List[Dict]) -> List[List[Dict]]:
        """Group words into semantic lines based on position and content"""
        if not words:
            return []
        
        # Sort by Y position, then X position
        words = sorted(words, key=lambda w: (w['top'], w['left']))
        
        lines = []
        current_line = [words[0]]
        current_y = words[0]['top']
        line_tolerance = 20  # Pixels tolerance for same line
        
        for word in words[1:]:
            if abs(word['top'] - current_y) <= line_tolerance:
                # Same line
                current_line.append(word)
            else:
                # New line - sort current line by X position
                current_line.sort(key=lambda w: w['left'])
                lines.append(current_line)
                current_line = [word]
                current_y = word['top']
        
        # Don't forget the last line
        if current_line:
            current_line.sort(key=lambda w: w['left'])
            lines.append(current_line)
        
        return lines
    
    def _reconstruct_line(self, line_words: List[Dict]) -> str:
        """Reconstruct a line of text from words, handling table-like structures"""
        if not line_words:
            return ""
        
        # Calculate gaps between words to detect table columns
        result_parts = []
        prev_word = None
        
        for word in line_words:
            if prev_word:
                # Calculate gap between words
                gap = word['left'] - (prev_word['left'] + prev_word['width'])
                
                # Large gap suggests different columns - use appropriate separator
                if gap > 50:  # Large gap - likely different columns
                    # Check if this looks like a parameter-value pair
                    if self._is_parameter_value_pair(prev_word['text'], word['text']):
                        result_parts.append(": ")
                    else:
                        result_parts.append("    ")  # Use spaces instead of pipes
                elif gap > 20:  # Medium gap
                    result_parts.append("  ")
                else:  # Small gap - normal word spacing
                    result_parts.append(" ")
            
            result_parts.append(word['text'])
            prev_word = word
        
        return ''.join(result_parts)
    
    def _is_parameter_value_pair(self, text1: str, text2: str) -> bool:
        """Check if two texts form a parameter-value pair"""
        # Check if first text is a known medical parameter
        text1_lower = text1.lower()
        for param_group in self.medical_parameters.values():
            if any(param in text1_lower for param in param_group):
                # Check if second text looks like a value
                if re.search(r'\d+[,.]?\d*', text2):
                    return True
        
        # Check for common patterns
        if text1.endswith(':'):
            return False  # Already has colon
        
        # Check if text2 is numeric or has units
        if re.match(r'^[\d,.\-]+\s*\w*$', text2):
            return True
        
        return False
    
    def _clean_ocr_text(self, text: str) -> str:
        """Clean OCR text without position data"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove excessive pipe characters
            line = re.sub(r'\|\s*\|+', '|', line)  # Collapse multiple pipes
            line = re.sub(r'^\|\s*|\s*\|$', '', line)  # Remove leading/trailing pipes
            
            # Replace remaining pipes with better separators
            if '|' in line:
                parts = [p.strip() for p in line.split('|') if p.strip()]
                
                # Try to intelligently join parts
                if len(parts) == 2:
                    # Likely parameter: value
                    line = f"{parts[0]}: {parts[1]}"
                elif len(parts) > 2:
                    # Check if it's parameter | value | unit | reference
                    if self._looks_like_lab_result(parts):
                        line = self._format_lab_result(parts)
                    else:
                        # Join with spaces
                        line = '  '.join(parts)
            
            # Clean up excessive whitespace
            line = re.sub(r'\s+', ' ', line)
            line = line.strip()
            
            # Skip lines that are just noise
            if self._is_noise_line(line):
                continue
            
            if line:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _looks_like_lab_result(self, parts: List[str]) -> bool:
        """Check if parts look like a lab result"""
        if len(parts) < 2:
            return False
        
        # Check if second part contains numbers
        has_number = any(re.search(r'\d+[,.]?\d*', part) for part in parts[1:])
        
        # Check if first part might be a parameter name
        first_part_lower = parts[0].lower()
        might_be_param = (
            len(first_part_lower) > 1 and
            not first_part_lower.isdigit() and
            not all(c in '.-_=><' for c in first_part_lower)
        )
        
        return has_number and might_be_param
    
    def _format_lab_result(self, parts: List[str]) -> str:
        """Format lab result parts into readable text"""
        if len(parts) == 2:
            return f"{parts[0]}: {parts[1]}"
        elif len(parts) == 3:
            # parameter | value | unit
            return f"{parts[0]}: {parts[1]} {parts[2]}"
        elif len(parts) >= 4:
            # parameter | value | unit | reference
            result = f"{parts[0]}: {parts[1]}"
            if parts[2]:  # unit
                result += f" {parts[2]}"
            if len(parts) > 3 and parts[3]:  # reference
                result += f" (Referenz: {parts[3]})"
            return result
        else:
            return '  '.join(parts)
    
    def _is_noise_line(self, line: str) -> bool:
        """Check if a line is just OCR noise"""
        # Line is too short
        if len(line) < 3:
            return True
        
        # Line is just special characters
        if re.match(r'^[^\w\s]+$', line):
            return True
        
        # Line is just underscores or dashes
        if re.match(r'^[_\-=]+$', line):
            return True
        
        # Line has too many special characters relative to text
        special_chars = len(re.findall(r'[^\w\s]', line))
        alphanum_chars = len(re.findall(r'[\w]', line))
        if alphanum_chars > 0 and special_chars / alphanum_chars > 3:
            return True
        
        return False
    
    def _enhance_medical_content(self, text: str) -> str:
        """Enhance medical content for better AI understanding"""
        # Fix common OCR errors in medical terms
        replacements = {
            r'\bHamoglobin\b': 'Hämoglobin',
            r'\bHamatokrit\b': 'Hämatokrit',
            r'\bLeuko[sz]yten\b': 'Leukozyten',
            r'\bErythro[sz]yten\b': 'Erythrozyten',
            r'\bThrombo[sz]yten\b': 'Thrombozyten',
            r'\bmg/d[lI]\b': 'mg/dl',
            r'\bmmol/[lI]\b': 'mmol/l',
            r'\b[uμ]g/[lI]\b': 'μg/l',
            r'\bpmo[lI]/[lI]\b': 'pmol/l',
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Format lab values more clearly
        # Pattern: Parameter followed by number
        text = re.sub(
            r'(\b\w+[\w\s\-]*?)[\s:]+(\d+[,.]?\d*)\s*([A-Za-z/%]+)?',
            lambda m: self._format_medical_value(m),
            text
        )
        
        # Add section headers if missing
        text = self._add_section_headers(text)
        
        return text
    
    def _format_medical_value(self, match) -> str:
        """Format a medical parameter-value match"""
        param = match.group(1).strip()
        value = match.group(2)
        unit = match.group(3) or ''
        
        # Check if parameter is known medical term
        param_lower = param.lower()
        for standard_name, variations in self.medical_parameters.items():
            if any(var in param_lower for var in variations):
                param = standard_name.capitalize()
                break
        
        result = f"{param}: {value}"
        if unit:
            result += f" {unit}"
        
        return result
    
    def _add_section_headers(self, text: str) -> str:
        """Add section headers to make content clearer"""
        lines = text.split('\n')
        enhanced_lines = []
        
        # Track what sections we've seen
        has_lab_values = False
        has_diagnosis = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Detect lab values section
            if not has_lab_values and any(param in line_lower for params in self.medical_parameters.values() for param in params):
                enhanced_lines.append("\n=== LABORWERTE ===")
                has_lab_values = True
            
            # Detect diagnosis section
            if not has_diagnosis and any(term in line_lower for term in ['diagnose', 'befund', 'beurteilung']):
                enhanced_lines.append("\n=== DIAGNOSE/BEFUND ===")
                has_diagnosis = True
            
            enhanced_lines.append(line)
        
        return '\n'.join(enhanced_lines)
    
    def detect_table_structure(self, ocr_data: dict) -> bool:
        """
        Detect if OCR data contains a table structure
        Simplified version that's less aggressive about table detection
        """
        try:
            if not ocr_data or 'text' not in ocr_data:
                return False
            
            # Count non-empty text elements
            non_empty = sum(1 for t in ocr_data['text'] if t.strip())
            
            # Don't treat everything as a table
            # Only if we have clear multi-column structure
            if non_empty < 10:
                return False
            
            # Check for multiple columns of aligned data
            # (This is simplified - the main improvement is in processing)
            return True
            
        except Exception as e:
            logger.debug(f"Table detection error: {e}")
            return False