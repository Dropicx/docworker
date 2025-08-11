"""
Advanced text extractor with full Tesseract OCR support for Railway deployment
Handles both embedded text PDFs and scanned documents/images
"""

import os
import logging
from typing import Optional, Tuple
from io import BytesIO
import tempfile

import PyPDF2
import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
from .improved_table_processor import ImprovedTableProcessor

logger = logging.getLogger(__name__)

class TextExtractorWithOCR:
    
    def __init__(self):
        # Check if Tesseract is available
        self.ocr_available = self._check_tesseract()
        # Initialize improved table processor for better medical OCR
        self.table_processor = ImprovedTableProcessor()
        
        if self.ocr_available:
            logger.info("✅ Text extractor initialized with Tesseract OCR support")
            print("✅ Text extractor initialized with Tesseract OCR support", flush=True)
            # Configure Tesseract for German and English with BEST quality
            # OEM 1 = LSTM neural net only (best accuracy)
            # PSM 3 = Fully automatic page segmentation (default, works best for most documents)
            # Additional optimizations for German medical documents
            self.tesseract_config = '--oem 1 --psm 3 -l deu+eng -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜabcdefghijklmnopqrstuvwxyzäöüß0123456789.,;:!?()[]{}/-+= " -c preserve_interword_spaces=1 -c textord_heavy_nr=1'
            
            # Special config for tables with better structure preservation
            # PSM 6 = Uniform block of text - better for tables
            # Added more table-specific parameters for better row/column detection
            self.tesseract_table_config = '--oem 1 --psm 6 -l deu+eng -c preserve_interword_spaces=1 -c textord_tabfind_vertical_text=0 -c textord_tablefind_recognize_tables=1 -c textord_tabfind_force_vertical_text=0 -c textord_tabfind_vertical_horizontal_mix=1'
            
            # Config for sparse text (like forms)
            self.tesseract_sparse_config = '--oem 1 --psm 11 -l deu+eng -c preserve_interword_spaces=1'
        else:
            logger.warning("⚠️ Tesseract not found - OCR disabled")
            print("⚠️ Tesseract not found - OCR disabled", flush=True)
    
    def _check_tesseract(self) -> bool:
        """Check if Tesseract is installed and available"""
        try:
            # Try to get Tesseract version
            version = pytesseract.get_tesseract_version()
            logger.info(f"🔍 Tesseract version: {version}")
            print(f"🔍 Tesseract version: {version}", flush=True)
            return True
        except Exception as e:
            logger.warning(f"❌ Tesseract check failed: {e}")
            return False
    
    async def extract_text(self, file_content: bytes, file_type: str, filename: str) -> Tuple[str, float]:
        """
        Extrahiert Text aus Datei basierend auf Typ
        
        Args:
            file_content: Dateiinhalt als Bytes
            file_type: Dateityp ('pdf' oder 'image')
            filename: Ursprünglicher Dateiname
            
        Returns:
            Tuple[str, float]: (extracted_text, confidence_score)
        """
        logger.info(f"📄 Processing {file_type} file: {filename}")
        print(f"📄 Processing {file_type} file: {filename}", flush=True)
        
        if file_type == "pdf":
            return await self._extract_from_pdf(file_content, filename)
        elif file_type == "image":
            return await self._extract_from_image(file_content, filename)
        else:
            raise ValueError(f"Nicht unterstützter Dateityp: {file_type}")
    
    async def _extract_from_pdf(self, content: bytes, filename: str) -> Tuple[str, float]:
        """Extrahiert Text aus PDF-Datei"""
        try:
            # Step 1: Try to extract embedded text with pdfplumber
            logger.info("📖 Step 1: Checking for embedded text with pdfplumber...")
            text = await self._extract_pdf_with_pdfplumber(content)
            
            if text and len(text.strip()) > 50:
                logger.info(f"✅ Embedded text found: {len(text)} characters")
                print(f"✅ Embedded text found in PDF: {len(text)} characters", flush=True)
                return text.strip(), 0.95
            
            # Step 2: Fallback to PyPDF2
            logger.info("📖 Step 2: Trying PyPDF2...")
            text = await self._extract_pdf_with_pypdf2(content)
            
            if text and len(text.strip()) > 50:
                logger.info(f"✅ Text extracted with PyPDF2: {len(text)} characters")
                print(f"✅ Text extracted with PyPDF2: {len(text)} characters", flush=True)
                return text.strip(), 0.85
            
            # Step 3: If no embedded text and OCR is available, use OCR
            if self.ocr_available:
                logger.info("🔍 Step 3: No embedded text found, starting OCR...")
                print(f"🔍 Starting OCR for scanned PDF: {filename}", flush=True)
                return await self._ocr_pdf(content, filename)
            else:
                logger.warning("❌ No embedded text and OCR not available")
                return (
                    "⚠️ Dieses PDF enthält keinen extrahierbaren Text.\n\n"
                    "Das PDF scheint gescannt zu sein, aber OCR ist nicht verfügbar.\n"
                    "Bitte verwenden Sie ein PDF mit eingebettetem Text.",
                    0.1
                )
                
        except Exception as e:
            logger.error(f"❌ PDF extraction failed: {e}")
            print(f"❌ PDF extraction failed: {e}", flush=True)
            return f"Fehler bei der PDF-Verarbeitung: {str(e)}", 0.0
    
    async def _extract_pdf_with_pdfplumber(self, content: bytes) -> str:
        """Verwendet pdfplumber für Textextraktion"""
        try:
            pdf_file = BytesIO(content)
            text_parts = []
            
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Seite {page_num} ---\n{page_text}")
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.debug(f"pdfplumber extraction failed: {e}")
            return ""
    
    async def _extract_pdf_with_pypdf2(self, content: bytes) -> str:
        """Verwendet PyPDF2 als Fallback"""
        try:
            pdf_file = BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text_parts = []
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Seite {page_num} ---\n{page_text}")
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.debug(f"PyPDF2 extraction failed: {e}")
            return ""
    
    async def _ocr_pdf(self, content: bytes, filename: str) -> Tuple[str, float]:
        """Führt OCR auf PDF-Seiten mit Tesseract aus"""
        try:
            # Convert PDF to images
            logger.info(f"🖼️ Converting PDF to images for OCR...")
            print(f"🖼️ Converting PDF to images for OCR: {filename}", flush=True)
            
            # Use a higher DPI for better OCR quality
            images = convert_from_bytes(content, dpi=300)
            logger.info(f"📄 Converted {len(images)} pages to images")
            print(f"📄 Converted {len(images)} pages to images", flush=True)
            
            text_parts = []
            total_confidence = 0.0
            
            for i, image in enumerate(images, 1):
                logger.info(f"🔍 OCR processing page {i}/{len(images)}...")
                print(f"🔍 OCR processing page {i}/{len(images)}...", flush=True)
                
                # Preprocess image for better OCR
                image = self._preprocess_image_for_ocr(image)
                
                # Perform OCR with Tesseract
                try:
                    # Get text with confidence scores and structure data
                    data = pytesseract.image_to_data(image, config=self.tesseract_table_config, output_type=pytesseract.Output.DICT)
                    
                    # Detect if page contains tables using enhanced detection
                    has_table_structure = self.table_processor.detect_table_structure(data)
                    
                    # Always use improved processing for better results
                    logger.info(f"🔍 Processing page {i} with improved OCR...")
                    
                    # Extract text - use table config if table detected, normal otherwise
                    if has_table_structure:
                        logger.info(f"📊 Page {i}: Medical table/form detected - optimizing extraction")
                        page_text = pytesseract.image_to_string(image, config=self.tesseract_table_config)
                    else:
                        page_text = pytesseract.image_to_string(image, config=self.tesseract_config)
                    
                    # Always apply improved processing for cleaner output
                    page_text = self.table_processor.process_ocr_output(page_text, data)
                    
                    # Apply OCR error correction to all text
                    page_text = self._correct_ocr_errors(page_text)
                    page_text = self._apply_medical_dictionary_correction(page_text)
                    page_text = self._enhance_lab_value_formatting(page_text)
                    
                    # Calculate average confidence for non-empty text
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    page_confidence = sum(confidences) / len(confidences) if confidences else 0
                    total_confidence += page_confidence
                    
                    if page_text.strip():
                        text_parts.append(f"--- Seite {i} (OCR) ---\n{page_text}")
                        logger.info(f"✅ Page {i} OCR complete: {len(page_text)} chars, confidence: {page_confidence:.1f}%")
                        # Log first 1500 chars for debugging
                        preview = page_text[:1500] if len(page_text) > 1500 else page_text
                        logger.info(f"📄 Page {i} content preview (first 1500 chars):\n{preview}")
                        print(f"📄 Page {i} extracted text preview:\n{preview[:1000]}...", flush=True)
                    else:
                        logger.warning(f"⚠️ Page {i}: No text detected")
                        
                except Exception as e:
                    logger.error(f"❌ OCR failed for page {i}: {e}")
                    text_parts.append(f"--- Seite {i} (OCR fehlgeschlagen) ---\n[Fehler: {str(e)}]")
            
            if text_parts:
                avg_confidence = (total_confidence / len(images)) / 100.0
                final_text = "\n\n".join(text_parts)
                logger.info(f"✅ OCR completed: {len(final_text)} total characters, avg confidence: {avg_confidence:.2f}")
                print(f"✅ OCR completed for {filename}: {len(final_text)} characters", flush=True)
                return final_text, max(0.5, min(0.9, avg_confidence))
            else:
                return "OCR konnte keinen Text aus dem PDF extrahieren.", 0.1
                
        except Exception as e:
            logger.error(f"❌ PDF OCR failed: {e}")
            print(f"❌ PDF OCR failed: {e}", flush=True)
            
            if "pdf2image" in str(e) or "poppler" in str(e):
                return (
                    "❌ PDF-zu-Bild-Konvertierung fehlgeschlagen.\n"
                    "Poppler-utils scheint nicht korrekt installiert zu sein.",
                    0.0
                )
            return f"OCR-Fehler: {str(e)}", 0.0
    
    async def _extract_from_image(self, content: bytes, filename: str) -> Tuple[str, float]:
        """Extrahiert Text aus Bilddatei mit OCR"""
        if not self.ocr_available:
            return (
                "⚠️ OCR ist nicht verfügbar.\n\n"
                "Tesseract OCR ist nicht installiert oder nicht korrekt konfiguriert.",
                0.0
            )
        
        try:
            logger.info(f"🖼️ Processing image with OCR: {filename}")
            print(f"🖼️ Processing image with OCR: {filename}", flush=True)
            
            # Load image with PIL
            image = Image.open(BytesIO(content))
            
            # Preprocess for better OCR
            image = self._preprocess_image_for_ocr(image)
            
            # Check if image might contain tables (based on structure detection)
            # Try with table-optimized config first
            data = pytesseract.image_to_data(image, config=self.tesseract_table_config, output_type=pytesseract.Output.DICT)
            
            # Detect if there might be table structures using enhanced detection
            has_table_structure = self.table_processor.detect_table_structure(data)
            
            # Always use improved processing for better results
            logger.info("🔍 Processing image with improved OCR...")
            
            if has_table_structure:
                logger.info("📊 Medical table/form detected - optimizing extraction")
                print("📊 Medical table/form detected - optimizing extraction", flush=True)
                text = pytesseract.image_to_string(image, config=self.tesseract_table_config)
            else:
                text = pytesseract.image_to_string(image, config=self.tesseract_config)
            
            # Always apply improved processing for cleaner output
            text = self.table_processor.process_ocr_output(text, data)
            
            # Apply OCR error correction
            text = self._correct_ocr_errors(text)
            text = self._apply_medical_dictionary_correction(text)
            text = self._enhance_lab_value_formatting(text)
            
            # Calculate confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            if text and len(text.strip()) > 10:
                logger.info(f"✅ OCR successful: {len(text)} characters, confidence: {avg_confidence:.1f}%")
                # Log first 1500 chars for debugging
                preview = text[:1500] if len(text) > 1500 else text
                logger.info(f"📄 Image OCR content preview (first 1500 chars):\n{preview}")
                print(f"✅ Image OCR completed: {len(text)} characters extracted", flush=True)
                print(f"📄 Extracted text preview:\n{preview[:1000]}...", flush=True)
                return text.strip(), max(0.5, min(0.95, avg_confidence / 100.0))
            else:
                logger.warning("⚠️ OCR found no text in image")
                return "OCR konnte keinen Text aus dem Bild extrahieren.", 0.1
                
        except Exception as e:
            logger.error(f"❌ Image OCR failed: {e}")
            print(f"❌ Image OCR failed: {e}", flush=True)
            return f"Bildverarbeitung fehlgeschlagen: {str(e)}", 0.0
    
    def _preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy and handle large phone photos"""
        try:
            # First, handle very large images (phone photos)
            width, height = image.size
            max_dimension = 4000  # Maximum dimension for processing
            
            if width > max_dimension or height > max_dimension:
                # Calculate scaling factor to fit within max dimensions
                scale = min(max_dimension / width, max_dimension / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                logger.info(f"📱 Resizing large image from {width}x{height} to {new_width}x{new_height}")
                print(f"📱 Resizing large phone photo: {width}x{height} → {new_width}x{new_height}", flush=True)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                width, height = new_width, new_height
            
            # Convert to grayscale if not already
            if image.mode != 'L':
                image = image.convert('L')
            
            # Ensure minimum size for OCR (but not if already large enough)
            min_width = 1000
            if width < min_width:
                scale = min_width / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.debug(f"Upscaled image to {new_width}x{new_height} for better OCR")
            
            # Optional: Apply image enhancement for better OCR
            from PIL import ImageEnhance
            
            # Increase contrast slightly
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            # Increase sharpness slightly
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            return image
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image
    
    def _detect_table_structure(self, ocr_data: dict) -> bool:
        """Detect if the OCR data suggests a table structure"""
        try:
            # Analyze word positions to detect columnar structure
            if not ocr_data or 'text' not in ocr_data:
                return False
            
            # Get words with positions
            words = []
            for i in range(len(ocr_data['text'])):
                if ocr_data['text'][i].strip():
                    words.append({
                        'text': ocr_data['text'][i],
                        'left': ocr_data['left'][i],
                        'top': ocr_data['top'][i],
                        'width': ocr_data['width'][i],
                        'height': ocr_data['height'][i]
                    })
            
            if len(words) < 10:
                return False
            
            # Check for aligned columns (words with similar x-positions)
            x_positions = [w['left'] for w in words]
            x_clusters = []
            tolerance = 20  # pixels tolerance for column alignment
            
            for x in x_positions:
                found_cluster = False
                for cluster in x_clusters:
                    if abs(cluster[0] - x) < tolerance:
                        cluster.append(x)
                        found_cluster = True
                        break
                if not found_cluster:
                    x_clusters.append([x])
            
            # If we have 3+ columns with 3+ items each, likely a table
            significant_columns = [c for c in x_clusters if len(c) >= 3]
            
            return len(significant_columns) >= 3
            
        except Exception as e:
            logger.debug(f"Table detection failed: {e}")
            return False
    
    def _format_table_text(self, text: str) -> str:
        """Format text to better preserve table structure"""
        try:
            lines = text.split('\n')
            formatted_lines = []
            
            for line in lines:
                # Preserve multiple spaces (likely column separators)
                # But collapse single spaces
                import re
                
                # Replace multiple spaces with a tab-like separator
                line = re.sub(r'  +', ' | ', line)
                
                # Clean up line
                line = line.strip()
                
                if line:
                    formatted_lines.append(line)
            
            # Join lines and add table markers for common patterns
            result = '\n'.join(formatted_lines)
            
            # Detect common lab value patterns and format them
            # Pattern: Parameter Name    Value    Unit    Reference
            result = re.sub(
                r'([A-Za-zÄÖÜäöüß\-]+)\s*\|\s*([\d,\.]+)\s*\|\s*([A-Za-z/%]+)\s*\|\s*([\d,\.\-\s]+)',
                r'\1: \2 \3 (Referenz: \4)',
                result
            )
            
            return result
            
        except Exception as e:
            logger.debug(f"Table formatting failed: {e}")
            return text
    
    def _correct_ocr_errors(self, text: str) -> str:
        """Post-process OCR text to correct common errors in German medical documents"""
        import re
        
        # Common OCR character substitutions
        corrections = {
            # Number/Letter confusions
            r'\b0(?=[a-zäöüß])': 'O',  # 0 -> O before lowercase letters
            r'(?<=[a-zäöüß])0\b': 'o',  # 0 -> o after lowercase letters
            r'\b1(?=[a-zäöüß]{2,})': 'I',  # 1 -> I at word start
            r'(?<=[a-zäöüß])1(?=[a-zäöüß])': 'i',  # 1 -> i in middle of word
            r'(?<=[a-zäöüß])1\b': 'l',  # 1 -> l at word end
            r'\bI(?=\d)': '1',  # I -> 1 before numbers
            r'(?<=\d)O(?=\d)': '0',  # O -> 0 between numbers
            r'(?<=\d)o(?=\d)': '0',  # o -> 0 between numbers
            
            # German special characters
            r'ii': 'ü',  # Common OCR error for ü
            r'ae': 'ä',  # If OCR misses umlauts
            r'oe': 'ö',
            r'ue': 'ü',
            r'ss': 'ß',  # In certain contexts
            
            # Medical terms commonly misread
            r'\bHamoglobin\b': 'Hämoglobin',
            r'\bErythrozyten\b': 'Erythrozyten',
            r'\bLeukozyten\b': 'Leukozyten',
            r'\bThrombocyten\b': 'Thrombozyten',
            r'\bKreatinin\b': 'Kreatinin',
            r'\bBilirubin\b': 'Bilirubin',
            r'\bCholesterin\b': 'Cholesterin',
            r'\bGlukose\b': 'Glucose',
            r'\bNatrium\b': 'Natrium',
            r'\bKalium\b': 'Kalium',
            r'\bCalcium\b': 'Calcium',
            r'\bPhosphat\b': 'Phosphat',
            
            # Common German medical abbreviations
            r'\bmg/d1\b': 'mg/dl',
            r'\bmmol/1\b': 'mmol/l',
            r'\bµmol/1\b': 'µmol/l',
            r'\bg/d1\b': 'g/dl',
            r'\bU/1\b': 'U/l',
            r'\bmU/1\b': 'mU/l',
            r'\bpg/m1\b': 'pg/ml',
            r'\bng/m1\b': 'ng/ml',
            r'\bµg/m1\b': 'µg/ml',
            
            # Fix spacing around units
            r'(\d)\s*mg\b': r'\1 mg',
            r'(\d)\s*ml\b': r'\1 ml',
            r'(\d)\s*mmol\b': r'\1 mmol',
            r'(\d)\s*%': r'\1%',
            
            # Fix decimal points/commas
            r'(\d)\.(\d{3})\b': r'\1,\2',  # German uses comma for decimals
            r'(\d{1,3}),(\d{3})': r'\1.\2',  # But thousand separator is period
        }
        
        # Apply corrections
        for pattern, replacement in corrections.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Fix common medical value patterns
        # Pattern: number-unit without space
        text = re.sub(r'(\d+)([a-zA-Z]+)', r'\1 \2', text)
        
        # Fix reference ranges
        text = re.sub(r'(\d+)\s*-\s*(\d+)', r'\1-\2', text)
        text = re.sub(r'(\d+,\d+)\s*-\s*(\d+,\d+)', r'\1-\2', text)
        
        # Clean up excessive whitespace
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def _apply_medical_dictionary_correction(self, text: str) -> str:
        """Apply medical dictionary-based corrections for German medical terms"""
        import re
        
        # Common medical terms dictionary (correct spelling)
        medical_terms = {
            # Organs
            'Herz', 'Lunge', 'Leber', 'Niere', 'Magen', 'Darm', 'Gehirn',
            'Pankreas', 'Milz', 'Schilddrüse', 'Nebenniere', 'Hypophyse',
            
            # Conditions
            'Diabetes', 'Hypertonie', 'Hypotonie', 'Anämie', 'Leukämie',
            'Pneumonie', 'Bronchitis', 'Gastritis', 'Hepatitis', 'Nephritis',
            'Arthritis', 'Arthrose', 'Osteoporose', 'Thrombose', 'Embolie',
            'Infarkt', 'Apoplex', 'Epilepsie', 'Migräne', 'Depression',
            
            # Lab parameters
            'Hämoglobin', 'Hämatokrit', 'Erythrozyten', 'Leukozyten',
            'Thrombozyten', 'Kreatinin', 'Harnstoff', 'Harnsäure',
            'Bilirubin', 'Albumin', 'Globulin', 'Cholesterin', 'Triglyzeride',
            'Glucose', 'Lactat', 'Pyruvat', 'Amylase', 'Lipase',
            
            # Medications
            'Aspirin', 'Paracetamol', 'Ibuprofen', 'Diclofenac', 'Metamizol',
            'Omeprazol', 'Pantoprazol', 'Simvastatin', 'Atorvastatin',
            'Metformin', 'Insulin', 'Levothyroxin', 'Prednisolon',
            'Amoxicillin', 'Ciprofloxacin', 'Metoprolol', 'Bisoprolol',
            'Ramipril', 'Enalapril', 'Amlodipine', 'Hydrochlorothiazid',
            
            # Procedures
            'Endoskopie', 'Koloskopie', 'Gastroskopie', 'Bronchoskopie',
            'Biopsie', 'Punktion', 'Sonographie', 'Echokardiographie',
            'Angiographie', 'Szintigraphie', 'Elektrokardiogramm',
            'Elektroenzephalogramm', 'Spirometrie', 'Ergometrie'
        }
        
        # Create a case-insensitive replacement function
        def correct_term(match):
            word = match.group(0)
            # Find the correct spelling (case-insensitive)
            for correct_term in medical_terms:
                if word.lower() == correct_term.lower():
                    # Preserve original case pattern if possible
                    if word.isupper():
                        return correct_term.upper()
                    elif word[0].isupper():
                        return correct_term
                    else:
                        return correct_term.lower()
            return word
        
        # Apply corrections for each medical term
        for term in medical_terms:
            # Create pattern for fuzzy matching (allow 1-2 character differences)
            # This is simplified - in production, use Levenshtein distance
            pattern = r'\b' + re.escape(term) + r'\b'
            text = re.sub(pattern, correct_term, text, flags=re.IGNORECASE)
        
        return text
    
    def _enhance_lab_value_formatting(self, text: str) -> str:
        """Enhance formatting of laboratory values for better readability"""
        import re
        
        # Format lab values with proper units
        # Pattern: Parameter: number unit (reference)
        lab_patterns = [
            # Hämoglobin: 14.5 g/dl (12-16)
            (r'(Hämoglobin|Hb):?\s*(\d+[,.]?\d*)\s*(g/dl)?', r'Hämoglobin: \2 g/dl'),
            # Leukozyten: 8500 /µl (4000-10000)
            (r'(Leukozyten|Leukos?):?\s*(\d+)\s*(/µl)?', r'Leukozyten: \2 /µl'),
            # Glucose: 95 mg/dl (70-110)
            (r'(Glucose|Glukose|BZ):?\s*(\d+)\s*(mg/dl)?', r'Glucose: \2 mg/dl'),
            # Kreatinin: 0.9 mg/dl (0.5-1.2)
            (r'(Kreatinin|Krea):?\s*(\d+[,.]?\d*)\s*(mg/dl)?', r'Kreatinin: \2 mg/dl'),
            # Cholesterin: 180 mg/dl (<200)
            (r'(Cholesterin|Chol):?\s*(\d+)\s*(mg/dl)?', r'Cholesterin: \2 mg/dl'),
            # TSH: 2.5 mU/l (0.4-4.0)
            (r'(TSH):?\s*(\d+[,.]?\d*)\s*(mU/l)?', r'TSH: \2 mU/l'),
            # CRP: 0.5 mg/l (<5)
            (r'(CRP|C-reaktives? Protein):?\s*(\d+[,.]?\d*)\s*(mg/l)?', r'CRP: \2 mg/l'),
        ]
        
        for pattern, replacement in lab_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Add reference range formatting
        text = re.sub(
            r'(\d+[,.]?\d*\s*[a-z/]+)\s*\((\d+[,.]?\d*\s*-\s*\d+[,.]?\d*)\)',
            r'\1 (Referenz: \2)',
            text
        )
        
        return text