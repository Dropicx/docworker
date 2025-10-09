import magic
import os
import logging
from typing import Tuple, Optional
from PIL import Image
import PyPDF2
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

# Erlaubte MIME-Types und Dateiendungen (inkl. Fallbacks)
ALLOWED_MIME_TYPES = {
    "application/pdf": [".pdf"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"]
}

# Fallback MIME-Types (manchmal erkennt magic library nicht korrekt)
FALLBACK_MIME_TYPES = {
    "text/plain": [".pdf", ".jpg", ".jpeg", ".png"],  # Magic erkennt manchmal falsch
    "application/octet-stream": [".pdf", ".jpg", ".jpeg", ".png"],  # Generischer binary type
    "image/x-png": [".png"],  # Alternative PNG-Erkennung
    "image/pjpeg": [".jpg", ".jpeg"]  # Alternative JPEG-Erkennung
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB für Handyfotos
MIN_FILE_SIZE = 1024  # 1KB

class FileValidator:
    
    @staticmethod
    async def validate_file(file: UploadFile) -> Tuple[bool, Optional[str]]:
        """
        Validiert eine hochgeladene Datei auf Typ, Größe und Inhalt
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            logger.debug(f"📋 Validating file: {file.filename}")

            # Dateiinhalt lesen
            content = await file.read()
            await file.seek(0)  # Zurück zum Anfang

            # Größenvalidierung
            file_size = len(content)
            logger.debug(f"📋 File size: {file_size} bytes")

            if file_size < MIN_FILE_SIZE:
                logger.warning(f"❌ File too small ({file_size} < {MIN_FILE_SIZE})")
                return False, f"Datei zu klein. Mindestgröße: {MIN_FILE_SIZE} Bytes"

            if file_size > MAX_FILE_SIZE:
                logger.warning(f"❌ File too large ({file_size} > {MAX_FILE_SIZE})")
                return False, f"Datei zu groß. Maximalgröße: {MAX_FILE_SIZE // 1024 // 1024}MB"

            # MIME-Type über magic bestimmen
            detected_mime = magic.from_buffer(content, mime=True)
            logger.debug(f"📋 Detected MIME type: {detected_mime}")
            
            # Dateiendung prüfen
            filename_lower = file.filename.lower() if file.filename else ""
            file_extension = os.path.splitext(filename_lower)[1]
            
            # MIME-Type validieren (mit Fallback-Unterstützung)
            mime_valid = False
            used_mime_type = detected_mime
            
            if detected_mime in ALLOWED_MIME_TYPES:
                # Direkter Match
                allowed_extensions = ALLOWED_MIME_TYPES[detected_mime]
                if file_extension in allowed_extensions:
                    mime_valid = True
                    logger.debug(f"✅ Direct MIME type match: {detected_mime} with extension {file_extension}")
            elif detected_mime in FALLBACK_MIME_TYPES:
                # Fallback-Match basierend auf Dateiendung
                allowed_extensions = FALLBACK_MIME_TYPES[detected_mime]
                if file_extension in allowed_extensions:
                    mime_valid = True
                    logger.debug(f"⚠️ Fallback MIME type match: {detected_mime} with extension {file_extension}")
                    # Bestimme den eigentlichen MIME-Type basierend auf Endung
                    if file_extension == ".pdf":
                        used_mime_type = "application/pdf"
                    elif file_extension in [".jpg", ".jpeg"]:
                        used_mime_type = "image/jpeg"
                    elif file_extension == ".png":
                        used_mime_type = "image/png"

            if not mime_valid:
                logger.warning(f"❌ Unsupported MIME type/extension: {detected_mime} with {file_extension}")
                logger.debug(f"Allowed MIME types: {list(ALLOWED_MIME_TYPES.keys())}")
                logger.debug(f"Fallback MIME types: {list(FALLBACK_MIME_TYPES.keys())}")
                return False, f"Dateityp nicht unterstützt: {detected_mime} mit Endung {file_extension}"
            
            # Spezifische Validierung nach erkanntem Dateityp
            if used_mime_type == "application/pdf":
                is_valid, error = await FileValidator._validate_pdf(content)
                if not is_valid:
                    return False, error
                    
            elif used_mime_type.startswith("image/"):
                is_valid, error = await FileValidator._validate_image(content)
                if not is_valid:
                    return False, error

            logger.info(f"✅ File validated successfully: {file.filename}")
            return True, None

        except Exception as e:
            logger.error(f"❌ File validation exception: {str(e)}")
            return False, f"Fehler bei der Dateivalidierung: {str(e)}"
    
    @staticmethod
    async def _validate_pdf(content: bytes) -> Tuple[bool, Optional[str]]:
        """Validiert PDF-Datei"""
        try:
            from io import BytesIO
            pdf_file = BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Prüfen ob PDF geöffnet werden kann
            if len(pdf_reader.pages) == 0:
                return False, "PDF-Datei enthält keine Seiten"
            
            # Maximale Seitenzahl prüfen
            if len(pdf_reader.pages) > 50:
                return False, "PDF-Datei hat zu viele Seiten (Maximum: 50)"
            
            # Prüfen ob Text extrahierbar ist (mindestens eine Seite)
            text_found = False
            for i, page in enumerate(pdf_reader.pages[:5]):  # Erste 5 Seiten prüfen
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        text_found = True
                        break
                except:
                    continue
            
            return True, None
            
        except Exception as e:
            return False, f"Ungültige PDF-Datei: {str(e)}"
    
    @staticmethod
    async def _validate_image(content: bytes) -> Tuple[bool, Optional[str]]:
        """Validiert Bilddatei"""
        try:
            from io import BytesIO
            image_file = BytesIO(content)
            
            with Image.open(image_file) as img:
                # Bildformat prüfen
                if img.format not in ['JPEG', 'PNG']:
                    return False, f"Bildformat '{img.format}' nicht unterstützt"
                
                # Bildgröße prüfen
                width, height = img.size
                if width < 100 or height < 100:
                    return False, "Bild zu klein (Mindestgröße: 100x100 Pixel)"
                
                if width > 8000 or height > 8000:
                    return False, "Bild zu groß (Maximalgröße: 8000x8000 Pixel)"
                
                # Überprüfung auf beschädigte Bilddaten
                img.verify()
                
            return True, None
            
        except Exception as e:
            return False, f"Ungültige Bilddatei: {str(e)}"
    
    @staticmethod
    def get_file_type(filename: str) -> str:
        """Bestimmt Dateityp basierend auf Endung"""
        if not filename:
            return "unknown"
        
        extension = os.path.splitext(filename.lower())[1]
        
        if extension == ".pdf":
            return "pdf"
        elif extension in [".jpg", ".jpeg", ".png"]:
            return "image"
        else:
            return "unknown" 