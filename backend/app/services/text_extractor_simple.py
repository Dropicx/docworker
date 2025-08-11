"""
Simplified text extractor for Railway deployment
Uses basic PDF text extraction without OCR
For images, returns a message to use OVH's vision capabilities
"""

import os
from typing import Optional, Tuple
from io import BytesIO

import PyPDF2
import pdfplumber

class TextExtractor:
    
    def __init__(self):
        # No Tesseract needed for Railway deployment
        self.use_ocr = False
        print("📄 Text extractor initialized (Railway mode - no OCR)")
    
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
            return await self._handle_image(file_content)
        else:
            raise ValueError(f"Nicht unterstützter Dateityp: {file_type}")
    
    async def _extract_from_pdf(self, content: bytes) -> Tuple[str, float]:
        """Extrahiert Text aus PDF-Datei"""
        try:
            # Erst versuchen mit pdfplumber (bessere Textextraktion)
            text = await self._extract_pdf_with_pdfplumber(content)
            
            if text and len(text.strip()) > 50:
                return text.strip(), 0.9
            
            # Fallback auf PyPDF2
            text = await self._extract_pdf_with_pypdf2(content)
            
            if text and len(text.strip()) > 50:
                return text.strip(), 0.7
            
            # Wenn kein Text gefunden wurde
            return (
                "⚠️ Dieses PDF enthält keinen extrahierbaren Text.\n\n"
                "🔍 Mögliche Ursachen:\n"
                "• Das PDF ist gescannt (enthält nur Bilder)\n"
                "• Das PDF wurde aus Fotos erstellt\n"
                "• Der Text ist als Bild eingebettet\n\n"
                "💡 Lösung:\n"
                "1. Öffnen Sie das PDF in Adobe Acrobat\n"
                "2. Nutzen Sie 'OCR Text erkennen'\n"
                "3. Speichern Sie das PDF neu\n"
                "4. Laden Sie es erneut hoch\n\n"
                "Alternative: Konvertieren Sie das Originaldokument (Word, etc.) direkt zu PDF.",
                0.1
            )
                
        except Exception as e:
            print(f"❌ PDF-Extraktion fehlgeschlagen: {e}")
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
            print(f"⚠️ pdfplumber Extraktion fehlgeschlagen: {e}")
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
            print(f"⚠️ PyPDF2 Extraktion fehlgeschlagen: {e}")
            return ""
    
    async def _handle_image(self, content: bytes) -> Tuple[str, float]:
        """
        Handles image files without OCR
        In production, this would need to use OVH's vision API or similar
        """
        return (
            "⚠️ OCR ist auf Railway derzeit deaktiviert.\n\n"
            "📄 Bitte verwenden Sie:\n"
            "• PDF-Dokumente mit eingebettetem Text (nicht gescannt)\n"
            "• Word-Dokumente die zu PDF konvertiert wurden\n\n"
            "❌ Nicht unterstützt:\n"
            "• Gescannte PDFs (Bilder im PDF)\n"
            "• JPG/PNG Bilder von Dokumenten\n"
            "• Fotografierte Dokumente\n\n"
            "💡 Tipp: Verwenden Sie Adobe Acrobat oder ähnliche Tools, um gescannte PDFs "
            "mit OCR zu verarbeiten, bevor Sie sie hochladen.",
            0.0
        )