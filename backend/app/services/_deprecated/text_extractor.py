import os
import tempfile
from typing import Optional, Tuple
from io import BytesIO
import asyncio

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import PyPDF2
import pdfplumber
from fastapi import UploadFile

class TextExtractor:
    
    def __init__(self):
        # Tesseract-Konfiguration für deutsche Texterkennung
        self.tesseract_config = '--oem 3 --psm 6 -l deu'
        # Überprüfen ob Tesseract verfügbar ist
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            print(f"⚠️ Tesseract nicht gefunden: {e}")
    
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
        if file_type == "pdf":
            return await self._extract_from_pdf(file_content)
        elif file_type == "image":
            return await self._extract_from_image(file_content)
        else:
            raise ValueError(f"Nicht unterstützter Dateityp: {file_type}")
    
    async def _extract_from_pdf(self, content: bytes) -> Tuple[str, float]:
        """Extrahiert Text aus PDF-Datei"""
        try:
            # Erst versuchen mit pdfplumber (bessere Textextraktion)
            text = await self._extract_pdf_with_pdfplumber(content)
            
            if text and len(text.strip()) > 50:
                return text.strip(), 0.9
            
            # Fallback: PyPDF2
            text = await self._extract_pdf_with_pypdf2(content)
            
            if text and len(text.strip()) > 50:
                return text.strip(), 0.8
            
            # Wenn kein Text gefunden: PDF zu Bildern und OCR
            text = await self._extract_pdf_with_ocr(content)
            
            if text and len(text.strip()) > 20:
                return text.strip(), 0.6
            
            return "Kein Text in der PDF-Datei gefunden.", 0.0
            
        except Exception as e:
            print(f"❌ PDF-Textextraktion fehler: {e}")
            return f"Fehler bei der PDF-Verarbeitung: {str(e)}", 0.0
    
    async def _extract_pdf_with_pdfplumber(self, content: bytes) -> Optional[str]:
        """Textextraktion mit pdfplumber"""
        try:
            pdf_file = BytesIO(content)
            
            with pdfplumber.open(pdf_file) as pdf:
                text_parts = []
                
                for page in pdf.pages[:20]:  # Maximal 20 Seiten
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                
                return "\n\n".join(text_parts) if text_parts else None
                
        except Exception as e:
            print(f"pdfplumber Fehler: {e}")
            return None
    
    async def _extract_pdf_with_pypdf2(self, content: bytes) -> Optional[str]:
        """Textextraktion mit PyPDF2"""
        try:
            pdf_file = BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            
            for page in pdf_reader.pages[:20]:  # Maximal 20 Seiten
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            return "\n\n".join(text_parts) if text_parts else None
            
        except Exception as e:
            print(f"PyPDF2 Fehler: {e}")
            return None
    
    async def _extract_pdf_with_ocr(self, content: bytes) -> Optional[str]:
        """PDF zu Bildern konvertieren und OCR anwenden"""
        try:
            # Dies erfordert pdf2image - für jetzt einen Platzhalter
            # In einer vollständigen Implementierung würde hier pdf2image verwendet
            print("📋 OCR für PDF würde pdf2image benötigen")
            return None
            
        except Exception as e:
            print(f"PDF-OCR Fehler: {e}")
            return None
    
    async def _extract_from_image(self, content: bytes) -> Tuple[str, float]:
        """Extrahiert Text aus Bild mit OCR"""
        try:
            # Bild öffnen
            image = Image.open(BytesIO(content))
            
            # Bildvorverarbeitung für bessere OCR
            processed_image = await self._preprocess_image(image)
            
            # OCR mit Tesseract
            extracted_text = pytesseract.image_to_string(
                processed_image, 
                config=self.tesseract_config
            )
            
            if not extracted_text or len(extracted_text.strip()) < 10:
                # Versuche verschiedene Vorverarbeitungen
                for method in ['enhance_contrast', 'sharpen', 'threshold']:
                    try:
                        alt_image = await self._preprocess_image(image, method)
                        alt_text = pytesseract.image_to_string(
                            alt_image, 
                            config=self.tesseract_config
                        )
                        
                        if alt_text and len(alt_text.strip()) > len(extracted_text.strip()):
                            extracted_text = alt_text
                            
                    except Exception as e:
                        continue
            
            # Textqualität bewerten
            confidence = await self._calculate_ocr_confidence(extracted_text)
            
            if not extracted_text.strip():
                return "Kein Text im Bild erkannt.", 0.0
            
            return extracted_text.strip(), confidence
            
        except Exception as e:
            print(f"❌ Bild-OCR Fehler: {e}")
            return f"Fehler bei der Bildverarbeitung: {str(e)}", 0.0
    
    async def _preprocess_image(self, image: Image.Image, method: str = 'default') -> Image.Image:
        """Bildvorverarbeitung für bessere OCR-Ergebnisse"""
        try:
            # Zu RGB konvertieren falls nötig
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            if method == 'enhance_contrast':
                # Kontrast erhöhen
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(2.0)
                
            elif method == 'sharpen':
                # Schärfen
                image = image.filter(ImageFilter.SHARPEN)
                
            elif method == 'threshold':
                # Zu Graustufen und Schwellenwert
                image = image.convert('L')
                image = image.point(lambda x: 0 if x < 140 else 255, '1')
                
            else:  # default
                # Standard-Verbesserungen
                # Größe anpassen falls zu klein
                width, height = image.size
                if width < 600:
                    scale_factor = 600 / width
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Leichte Kontrastverbesserung
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.2)
                
                # Zu Graustufen für OCR
                image = image.convert('L')
            
            return image
            
        except Exception as e:
            print(f"Bildvorverarbeitung Fehler: {e}")
            return image
    
    async def _calculate_ocr_confidence(self, text: str) -> float:
        """Berechnet Vertrauensgrad für OCR-Text"""
        if not text or not text.strip():
            return 0.0
        
        # Einfache Heuristiken für Textqualität
        confidence = 0.5  # Basis
        
        # Länge des Textes
        if len(text.strip()) > 100:
            confidence += 0.1
        if len(text.strip()) > 500:
            confidence += 0.1
        
        # Verhältnis von Buchstaben zu Sonderzeichen
        letters = sum(1 for c in text if c.isalpha())
        total_chars = len(text.replace(' ', '').replace('\n', ''))
        
        if total_chars > 0:
            letter_ratio = letters / total_chars
            confidence += letter_ratio * 0.3
        
        # Deutsche Wörter erkennen
        german_indicators = ['der', 'die', 'das', 'und', 'ist', 'von', 'zu', 'mit', 'für']
        text_lower = text.lower()
        found_indicators = sum(1 for word in german_indicators if word in text_lower)
        confidence += (found_indicators / len(german_indicators)) * 0.1
        
        return min(confidence, 1.0) 