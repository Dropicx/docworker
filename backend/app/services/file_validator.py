import magic
import os
from typing import Tuple, Optional
from PIL import Image
import PyPDF2
from fastapi import UploadFile, HTTPException

# Erlaubte MIME-Types und Dateiendungen
ALLOWED_MIME_TYPES = {
    "application/pdf": [".pdf"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"]
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
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
            # Dateiinhalt lesen
            content = await file.read()
            await file.seek(0)  # Zurück zum Anfang
            
            # Größenvalidierung
            file_size = len(content)
            if file_size < MIN_FILE_SIZE:
                return False, f"Datei zu klein. Mindestgröße: {MIN_FILE_SIZE} Bytes"
            
            if file_size > MAX_FILE_SIZE:
                return False, f"Datei zu groß. Maximalgröße: {MAX_FILE_SIZE // 1024 // 1024}MB"
            
            # MIME-Type über magic bestimmen
            detected_mime = magic.from_buffer(content, mime=True)
            
            # Dateiendung prüfen
            filename_lower = file.filename.lower() if file.filename else ""
            file_extension = os.path.splitext(filename_lower)[1]
            
            # MIME-Type validieren
            if detected_mime not in ALLOWED_MIME_TYPES:
                return False, f"Dateityp nicht erlaubt: {detected_mime}"
            
            # Endung gegen MIME-Type prüfen
            allowed_extensions = ALLOWED_MIME_TYPES[detected_mime]
            if file_extension not in allowed_extensions:
                return False, f"Dateiendung '{file_extension}' passt nicht zum Dateityp '{detected_mime}'"
            
            # Spezifische Validierung nach Dateityp
            if detected_mime == "application/pdf":
                is_valid, error = await FileValidator._validate_pdf(content)
                if not is_valid:
                    return False, error
                    
            elif detected_mime.startswith("image/"):
                is_valid, error = await FileValidator._validate_image(content)
                if not is_valid:
                    return False, error
            
            return True, None
            
        except Exception as e:
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
                
                if width > 4000 or height > 4000:
                    return False, "Bild zu groß (Maximalgröße: 4000x4000 Pixel)"
                
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