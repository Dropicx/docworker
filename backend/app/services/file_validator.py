import logging
import os

from fastapi import UploadFile
import magic
from PIL import Image
import PyPDF2

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
    """Comprehensive file validation service for medical document uploads.

    Validates uploaded files for type safety, size constraints, and content integrity.
    Supports PDF documents and images (JPEG, PNG) with intelligent MIME type detection
    and fallback handling for inconsistent browser/OS file type reporting.

    **Validation Layers**:
        1. Size validation (1KB - 50MB range)
        2. MIME type detection with python-magic library
        3. Extension verification with fallback matching
        4. Content-specific validation (PDF structure, image integrity)

    **Supported File Types**:
        - PDF: application/pdf (.pdf), max 50 pages
        - JPEG: image/jpeg (.jpg, .jpeg)
        - PNG: image/png (.png)
        - Image constraints: 100x100 to 8000x8000 pixels

    **Fallback MIME Handling**:
        Some systems misreport MIME types (text/plain, octet-stream).
        The validator uses extension-based fallback for reliable detection.

    Example:
        >>> validator = FileValidator()
        >>> is_valid, error = await validator.validate_file(upload_file)
        >>> if is_valid:
        ...     print("File is valid")
        ... else:
        ...     print(f"Validation failed: {error}")

    Note:
        All methods are static - no instance state required.
        Designed for FastAPI UploadFile integration.
    """

    @staticmethod
    async def validate_file(file: UploadFile) -> tuple[bool, str | None]:
        """Validate uploaded file for type, size, and content integrity.

        Performs comprehensive validation including MIME type detection, size checks,
        and format-specific validation (PDF structure or image integrity). Uses
        python-magic for reliable MIME detection with extension-based fallback.

        Args:
            file: FastAPI UploadFile object containing uploaded file data

        Returns:
            Tuple[bool, Optional[str]]: Validation result tuple containing:
                - bool: True if file is valid and safe to process
                - Optional[str]: Error message if validation failed, None if valid

        Example:
            >>> from fastapi import UploadFile
            >>> file = UploadFile(filename="report.pdf", file=pdf_bytes)
            >>> is_valid, error = await FileValidator.validate_file(file)
            >>> if not is_valid:
            ...     raise HTTPException(400, detail=error)

        Note:
            **Size Constraints**:
            - Minimum: 1KB (prevents empty/corrupt files)
            - Maximum: 50MB (accommodates high-res phone photos)

            **MIME Type Fallback**:
            - Direct match: Magic library detection
            - Fallback match: Extension-based when MIME misreported
            - Common fallbacks: text/plain, octet-stream → check extension

            **Content Validation**:
            - PDF: Checks page count (max 50), structure integrity
            - Image: Verifies format, dimensions, data corruption
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
    async def _validate_pdf(content: bytes) -> tuple[bool, str | None]:
        """Validate PDF file structure and constraints.

        Checks PDF file integrity, page count limits, and text extractability.
        Ensures PDF is processable by OCR and translation pipeline.

        Args:
            content: Raw PDF file content as bytes

        Returns:
            Tuple[bool, Optional[str]]: Validation result tuple containing:
                - bool: True if PDF is valid, False otherwise
                - Optional[str]: Error message if invalid, None if valid

        Example:
            >>> pdf_bytes = open("report.pdf", "rb").read()
            >>> is_valid, error = await FileValidator._validate_pdf(pdf_bytes)
            >>> if not is_valid:
            ...     print(f"PDF validation failed: {error}")

        Note:
            **Validation Checks**:
            - PDF structure: Must be readable by PyPDF2
            - Page count: Must have at least 1 page, max 50 pages
            - Content: Validates first 5 pages for text extraction

            **Performance**:
            - Only checks first 5 pages for text (optimization)
            - Empty PDFs (scanned images) still pass - OCR handles them
        """
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
            for _i, page in enumerate(pdf_reader.pages[:5]):  # Erste 5 Seiten prüfen
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        break
                except:
                    continue

            return True, None

        except Exception as e:
            return False, f"Ungültige PDF-Datei: {str(e)}"

    @staticmethod
    async def _validate_image(content: bytes) -> tuple[bool, str | None]:
        """Validate image file format, dimensions, and data integrity.

        Checks image format support, dimension constraints, and data corruption.
        Ensures image is processable by OCR vision models.

        Args:
            content: Raw image file content as bytes

        Returns:
            Tuple[bool, Optional[str]]: Validation result tuple containing:
                - bool: True if image is valid, False otherwise
                - Optional[str]: Error message if invalid, None if valid

        Example:
            >>> img_bytes = open("scan.jpg", "rb").read()
            >>> is_valid, error = await FileValidator._validate_image(img_bytes)
            >>> if is_valid:
            ...     print("Image ready for OCR processing")

        Note:
            **Format Support**:
            - JPEG: Standard medical scan format
            - PNG: Lossless medical document format
            - Other formats (TIFF, BMP): Not supported

            **Dimension Constraints**:
            - Minimum: 100x100 pixels (too small for OCR)
            - Maximum: 8000x8000 pixels (memory/processing limits)

            **Integrity Check**:
            - Uses PIL.Image.verify() to detect corruption
            - Catches truncated files, invalid headers, corrupted data
        """
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
        """Determine file type from filename extension.

        Maps file extensions to standardized type identifiers used throughout
        the application. Simple extension-based detection for routing to
        appropriate processing pipelines.

        Args:
            filename: Original filename including extension

        Returns:
            str: Standardized file type identifier:
                - "pdf": PDF documents
                - "image": JPEG or PNG images
                - "unknown": Unsupported or missing extension

        Example:
            >>> FileValidator.get_file_type("report.pdf")
            'pdf'
            >>> FileValidator.get_file_type("scan.jpg")
            'image'
            >>> FileValidator.get_file_type("document.docx")
            'unknown'
            >>> FileValidator.get_file_type("")
            'unknown'

        Note:
            This is a simple helper for routing, not validation.
            Actual validation uses MIME type detection in validate_file().
        """
        if not filename:
            return "unknown"

        extension = os.path.splitext(filename.lower())[1]

        if extension == ".pdf":
            return "pdf"
        if extension in [".jpg", ".jpeg", ".png"]:
            return "image"
        return "unknown"
