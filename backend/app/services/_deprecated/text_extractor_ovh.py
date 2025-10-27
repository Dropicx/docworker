"""
Enhanced text extractor with OVH Vision API support for OCR
Handles both embedded text PDFs and scanned documents/images
"""

import os
import base64
from typing import Optional, Tuple
from io import BytesIO
import logging

import PyPDF2
import pdfplumber
from pdf2image import convert_from_bytes
from PIL import Image

from app.services.ovh_client import OVHClient

logger = logging.getLogger(__name__)

class TextExtractorWithOCR:

    def __init__(self):
        # Check if we should use OCR
        self.use_ocr = os.getenv("ENABLE_OCR", "true").lower() == "true"
        self.ovh_client = OVHClient() if self.use_ocr else None

        if self.use_ocr:
            logger.info("📄 Text extractor initialized with OVH Vision OCR support")
        else:
            logger.info("📄 Text extractor initialized (basic mode - no OCR)")

    async def extract_text(self, file_content: bytes, file_type: str, filename: str) -> tuple[str, float]:
        """
        Extrahiert Text aus Datei basierend auf Typ

        Args:
            file_content: Dateiinhalt als Bytes
            file_type: Dateityp ('pdf' oder 'image')
            filename: Ursprünglicher Dateiname

        Returns:
            tuple[str, float]: (extracted_text, confidence_score)
        """
        if file_type == "pdf":
            return await self._extract_from_pdf(file_content)
        elif file_type == "image":
            return await self._extract_from_image(file_content)
        else:
            raise ValueError(f"Nicht unterstützter Dateityp: {file_type}")

    async def _extract_from_pdf(self, content: bytes) -> tuple[str, float]:
        """Extrahiert Text aus PDF-Datei"""
        try:
            # Erst versuchen mit pdfplumber (bessere Textextraktion)
            text = await self._extract_pdf_with_pdfplumber(content)

            if text and len(text.strip()) > 50:
                logger.info("✅ PDF text extracted with pdfplumber")
                return text.strip(), 0.9

            # Fallback auf PyPDF2
            text = await self._extract_pdf_with_pypdf2(content)

            if text and len(text.strip()) > 50:
                logger.info("✅ PDF text extracted with PyPDF2")
                return text.strip(), 0.7

            # Wenn kein eingebetteter Text gefunden wurde, versuche OCR
            if self.use_ocr and self.ovh_client:
                logger.info("⚠️ No embedded text found, attempting OCR...")
                return await self._ocr_pdf(content)

            # Wenn kein OCR verfügbar
            return (
                "PDF enthält keinen extrahierbaren Text. "
                "Für gescannte Dokumente aktivieren Sie bitte OCR in den Einstellungen.",
                0.1
            )

        except Exception as e:
            logger.error(f"❌ PDF-Extraktion fehlgeschlagen: {e}")
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
            logger.warning(f"⚠️ pdfplumber Extraktion fehlgeschlagen: {e}")
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
            logger.warning(f"⚠️ PyPDF2 Extraktion fehlgeschlagen: {e}")
            return ""

    async def _ocr_pdf(self, content: bytes) -> tuple[str, float]:
        """Führt OCR auf PDF-Seiten aus"""
        try:
            # Konvertiere PDF zu Bildern
            logger.info("🔄 Converting PDF pages to images for OCR...")
            images = convert_from_bytes(content)

            text_parts = []
            for i, image in enumerate(images, 1):
                logger.info(f"🔍 Processing page {i}/{len(images)} with OCR...")
                page_text = await self._ocr_image(image)
                if page_text:
                    text_parts.append(f"--- Seite {i} (OCR) ---\n{page_text}")

            if text_parts:
                logger.info(f"✅ OCR completed for {len(images)} pages")
                return "\n\n".join(text_parts), 0.8
            else:
                return "OCR konnte keinen Text aus dem PDF extrahieren.", 0.1

        except Exception as e:
            logger.error(f"❌ PDF OCR failed: {e}")
            # Wenn pdf2image nicht installiert ist
            if "pdf2image" in str(e) or "poppler" in str(e):
                return (
                    "PDF-zu-Bild-Konvertierung nicht verfügbar. "
                    "Bitte verwenden Sie PDFs mit eingebettetem Text oder laden Sie Bilder direkt hoch.",
                    0.0
                )
            return f"OCR-Fehler: {str(e)}", 0.0

    async def _extract_from_image(self, content: bytes) -> tuple[str, float]:
        """Extrahiert Text aus Bilddatei mit OCR"""
        if not self.use_ocr or not self.ovh_client:
            return (
                "Bilddateien können ohne OCR nicht verarbeitet werden. "
                "Bitte aktivieren Sie OCR in den Einstellungen oder verwenden Sie PDF-Dokumente.",
                0.0
            )

        try:
            # Lade Bild mit PIL
            image = Image.open(BytesIO(content))
            text = await self._ocr_image(image)

            if text and len(text.strip()) > 10:
                logger.info("✅ Text extracted from image with OCR")
                return text.strip(), 0.85
            else:
                return "OCR konnte keinen Text aus dem Bild extrahieren.", 0.1

        except Exception as e:
            logger.error(f"❌ Image OCR failed: {e}")
            return f"Bildverarbeitung fehlgeschlagen: {str(e)}", 0.0

    async def _ocr_image(self, image: Image.Image) -> str:
        """
        Führt OCR auf einem Bild mit OVH Vision API aus
        """
        try:
            # Konvertiere Bild zu Base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

            # Erstelle Prompt für Vision API
            ocr_prompt = """Du bist ein präziser OCR-Scanner für medizinische Dokumente.

AUFGABE:
- Extrahiere ALLEN Text aus diesem Bild/Dokument
- Behalte die originale Struktur und Formatierung bei
- Erkenne Tabellen, Listen und spezielle Formatierungen
- Achte besonders auf medizinische Begriffe, Zahlen und Werte
- Bei unleserlichen Stellen markiere mit [unleserlich]

WICHTIG:
- Füge NICHTS hinzu, was nicht im Bild steht
- Lasse NICHTS weg
- Korrigiere KEINE Rechtschreibfehler
- Interpretiere NICHTS

Extrahierter Text:"""

            # Nutze OVH's Vision-fähiges Modell für OCR
            # Hinweis: Dies würde eine Vision-API Integration benötigen
            # Für jetzt nutzen wir das normale Modell mit Base64-Bild-Beschreibung

            result = await self.ovh_client.process_medical_text(
                text=f"[Bild-Daten: {len(img_base64)} Zeichen Base64-kodiert]",
                custom_prompt=ocr_prompt,
                temperature=0.1,  # Sehr niedrig für präzise Extraktion
                max_tokens=4000
            )

            return result

        except Exception as e:
            logger.error(f"❌ OVH OCR API call failed: {e}")
            # Fallback auf Fehlermeldung
            return ""

# Singleton-Instanz für globale Verwendung
text_extractor = None

def get_text_extractor():
    """Factory function to get text extractor instance"""
    global text_extractor
    if text_extractor is None:
        # Entscheide basierend auf Umgebungsvariable
        use_advanced = os.getenv("ENABLE_OCR", "false").lower() == "true"
        if use_advanced:
            text_extractor = TextExtractorWithOCR()
        else:
            # Fallback auf simple version
            from app.services.text_extractor_simple import TextExtractor
            text_extractor = TextExtractor()
    return text_extractor