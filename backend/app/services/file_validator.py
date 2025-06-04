import magic
import os
from typing import Tuple, Optional
from PIL import Image
import PyPDF2
from fastapi import UploadFile, HTTPException

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
            print(f"📋 FileValidator: Validiere {file.filename}")
            
            # Dateiinhalt lesen
            content = await file.read()
            await file.seek(0)  # Zurück zum Anfang
            
            # Größenvalidierung
            file_size = len(content)
            print(f"📋 FileValidator: Dateigröße {file_size} bytes")
            
            if file_size < MIN_FILE_SIZE:
                print(f"❌ FileValidator: Datei zu klein ({file_size} < {MIN_FILE_SIZE})")
                return False, f"Datei zu klein. Mindestgröße: {MIN_FILE_SIZE} Bytes"
            
            if file_size > MAX_FILE_SIZE:
                print(f"❌ FileValidator: Datei zu groß ({file_size} > {MAX_FILE_SIZE})")
                return False, f"Datei zu groß. Maximalgröße: {MAX_FILE_SIZE // 1024 // 1024}MB"
            
            # MIME-Type über magic bestimmen
            detected_mime = magic.from_buffer(content, mime=True)
            print(f"📋 FileValidator: Erkannter MIME-Type: {detected_mime}")
            
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
                    print(f"✅ FileValidator: Direkter MIME-Type Match: {detected_mime} mit Endung {file_extension}")
            elif detected_mime in FALLBACK_MIME_TYPES:
                # Fallback-Match basierend auf Dateiendung
                allowed_extensions = FALLBACK_MIME_TYPES[detected_mime]
                if file_extension in allowed_extensions:
                    mime_valid = True
                    print(f"⚠️ FileValidator: Fallback MIME-Type Match: {detected_mime} mit Endung {file_extension}")
                    # Bestimme den eigentlichen MIME-Type basierend auf Endung
                    if file_extension == ".pdf":
                        used_mime_type = "application/pdf"
                    elif file_extension in [".jpg", ".jpeg"]:
                        used_mime_type = "image/jpeg"
                    elif file_extension == ".png":
                        used_mime_type = "image/png"
            
            if not mime_valid:
                print(f"❌ FileValidator: MIME-Type/Endung nicht unterstützt: {detected_mime} mit {file_extension}")
                print(f"   Erlaubte MIME-Types: {list(ALLOWED_MIME_TYPES.keys())}")
                print(f"   Fallback MIME-Types: {list(FALLBACK_MIME_TYPES.keys())}")
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
            
            print(f"✅ FileValidator: Datei {file.filename} erfolgreich validiert")
            return True, None
            
        except Exception as e:
            print(f"❌ FileValidator: Exception bei Validierung: {str(e)}")
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