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

logger = logging.getLogger(__name__)

class TextExtractorWithOCR:
    
    def __init__(self):
        # Check if Tesseract is available
        self.ocr_available = self._check_tesseract()
        
        if self.ocr_available:
            logger.info("✅ Text extractor initialized with Tesseract OCR support")
            print("✅ Text extractor initialized with Tesseract OCR support", flush=True)
            # Configure Tesseract for German and English
            self.tesseract_config = '--oem 3 --psm 3 -l deu+eng'
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
                    # Get text with confidence scores
                    data = pytesseract.image_to_data(image, config=self.tesseract_config, output_type=pytesseract.Output.DICT)
                    
                    # Extract text
                    page_text = pytesseract.image_to_string(image, config=self.tesseract_config)
                    
                    # Calculate average confidence for non-empty text
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    page_confidence = sum(confidences) / len(confidences) if confidences else 0
                    total_confidence += page_confidence
                    
                    if page_text.strip():
                        text_parts.append(f"--- Seite {i} (OCR) ---\n{page_text}")
                        logger.info(f"✅ Page {i} OCR complete: {len(page_text)} chars, confidence: {page_confidence:.1f}%")
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
            
            # Perform OCR with confidence data
            data = pytesseract.image_to_data(image, config=self.tesseract_config, output_type=pytesseract.Output.DICT)
            text = pytesseract.image_to_string(image, config=self.tesseract_config)
            
            # Calculate confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            if text and len(text.strip()) > 10:
                logger.info(f"✅ OCR successful: {len(text)} characters, confidence: {avg_confidence:.1f}%")
                print(f"✅ Image OCR completed: {len(text)} characters extracted", flush=True)
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