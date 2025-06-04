from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class DocumentType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing" 
    EXTRACTING_TEXT = "extracting_text"
    TRANSLATING = "translating"
    LANGUAGE_TRANSLATING = "language_translating"
    COMPLETED = "completed"
    ERROR = "error"

class SupportedLanguage(str, Enum):
    AFRIKAANS = "af"
    AMHARIC = "am"
    ARABIC = "ar"
    ARMENIAN = "hy"
    ASSAMESE = "as"
    ASTURIAN = "ast"
    AZERBAIJANI = "az"
    BELARUSIAN = "be"
    BENGALI = "bn"
    BOSNIAN = "bs"
    BULGARIAN = "bg"
    BURMESE = "my"
    CATALAN = "ca"
    CEBUANO = "ceb"
    CHINESE_SIMPLIFIED = "zho"
    CHINESE_TRADITIONAL = "zho"
    CROATIAN = "hr"
    CZECH = "cs"
    DANISH = "da"
    DUTCH = "nl"
    ENGLISH = "en"
    ESTONIAN = "et"
    FILIPINO = "tl"
    FINNISH = "fi"
    FRENCH = "fr"
    FULAH = "ff"
    GALICIAN = "gl"
    GANDA = "lg"
    GEORGIAN = "ka"
    GERMAN = "de"
    GREEK = "el"
    GUJARATI = "gu"
    HAUSA = "ha"
    HEBREW = "he"
    HINDI = "hi"
    HUNGARIAN = "hu"
    ICELANDIC = "is"
    IGBO = "ig"
    INDONESIAN = "id"
    IRISH = "ga"
    ITALIAN = "it"
    JAPANESE = "ja"
    JAVANESE = "jv"
    KABUVERDIANU = "kea"
    KAMBA = "kam"
    KANNADA = "kn"
    KAZAKH = "kk"
    KHMER = "km"
    KOREAN = "ko"
    KYRGYZ = "ky"
    LAO = "lo"
    LATVIAN = "lv"
    LINGALA = "ln"
    LITHUANIAN = "lt"
    LUO = "luo"
    LUXEMBOURGISH = "lb"
    MACEDONIAN = "mk"
    MALAY = "ms"
    MALAYALAM = "ml"
    MALTESE = "mt"
    MAORI = "mi"
    MARATHI = "mr"
    MONGOLIAN = "mn"
    NEPALI = "ne"
    NORTHERN_SOTHO = "ns"
    NORWEGIAN = "no"
    NYANJA = "ny"
    OCCITAN = "oc"
    ORIYA = "or"
    OROMO = "om"
    PASHTO = "ps"
    PERSIAN = "fa"
    POLISH = "pl"
    PORTUGUESE = "pt"
    PUNJABI = "pa"
    ROMANIAN = "ro"
    RUSSIAN = "ru"
    SERBIAN = "sr"
    SHONA = "sn"
    SINDHI = "sd"
    SLOVAK = "sk"
    SLOVENIAN = "sl"
    SOMALI = "so"
    SORANI_KURDISH = "ku"
    SPANISH = "es"
    SWAHILI = "sw"
    SWEDISH = "sv"
    TAJIK = "tg"
    TAMIL = "ta"
    TELUGU = "te"
    THAI = "th"
    TURKISH = "tr"
    UKRAINIAN = "uk"
    UMBUNDU = "umb"
    URDU = "ur"
    UZBEK = "uz"

# Sprachname-Mapping für die UI
LANGUAGE_NAMES = {
    SupportedLanguage.AFRIKAANS: "Afrikaans",
    SupportedLanguage.AMHARIC: "Amharic",
    SupportedLanguage.ARABIC: "Arabic",
    SupportedLanguage.ARMENIAN: "Armenian",
    SupportedLanguage.ASSAMESE: "Assamese",
    SupportedLanguage.ASTURIAN: "Asturian",
    SupportedLanguage.AZERBAIJANI: "Azerbaijani",
    SupportedLanguage.BELARUSIAN: "Belarusian",
    SupportedLanguage.BENGALI: "Bengali",
    SupportedLanguage.BOSNIAN: "Bosnian",
    SupportedLanguage.BULGARIAN: "Bulgarian",
    SupportedLanguage.BURMESE: "Burmese",
    SupportedLanguage.CATALAN: "Catalan",
    SupportedLanguage.CEBUANO: "Cebuano",
    SupportedLanguage.CHINESE_SIMPLIFIED: "Chinese (Simplified)",
    SupportedLanguage.CHINESE_TRADITIONAL: "Chinese (Traditional)",
    SupportedLanguage.CROATIAN: "Croatian",
    SupportedLanguage.CZECH: "Czech",
    SupportedLanguage.DANISH: "Danish",
    SupportedLanguage.DUTCH: "Dutch",
    SupportedLanguage.ENGLISH: "English",
    SupportedLanguage.ESTONIAN: "Estonian",
    SupportedLanguage.FILIPINO: "Filipino",
    SupportedLanguage.FINNISH: "Finnish",
    SupportedLanguage.FRENCH: "French",
    SupportedLanguage.FULAH: "Fulah",
    SupportedLanguage.GALICIAN: "Galician",
    SupportedLanguage.GANDA: "Ganda",
    SupportedLanguage.GEORGIAN: "Georgian",
    SupportedLanguage.GERMAN: "German",
    SupportedLanguage.GREEK: "Greek",
    SupportedLanguage.GUJARATI: "Gujarati",
    SupportedLanguage.HAUSA: "Hausa",
    SupportedLanguage.HEBREW: "Hebrew",
    SupportedLanguage.HINDI: "Hindi",
    SupportedLanguage.HUNGARIAN: "Hungarian",
    SupportedLanguage.ICELANDIC: "Icelandic",
    SupportedLanguage.IGBO: "Igbo",
    SupportedLanguage.INDONESIAN: "Indonesian",
    SupportedLanguage.IRISH: "Irish",
    SupportedLanguage.ITALIAN: "Italian",
    SupportedLanguage.JAPANESE: "Japanese",
    SupportedLanguage.JAVANESE: "Javanese",
    SupportedLanguage.KABUVERDIANU: "Kabuverdianu",
    SupportedLanguage.KAMBA: "Kamba",
    SupportedLanguage.KANNADA: "Kannada",
    SupportedLanguage.KAZAKH: "Kazakh",
    SupportedLanguage.KHMER: "Khmer",
    SupportedLanguage.KOREAN: "Korean",
    SupportedLanguage.KYRGYZ: "Kyrgyz",
    SupportedLanguage.LAO: "Lao",
    SupportedLanguage.LATVIAN: "Latvian",
    SupportedLanguage.LINGALA: "Lingala",
    SupportedLanguage.LITHUANIAN: "Lithuanian",
    SupportedLanguage.LUO: "Luo",
    SupportedLanguage.LUXEMBOURGISH: "Luxembourgish",
    SupportedLanguage.MACEDONIAN: "Macedonian",
    SupportedLanguage.MALAY: "Malay",
    SupportedLanguage.MALAYALAM: "Malayalam",
    SupportedLanguage.MALTESE: "Maltese",
    SupportedLanguage.MAORI: "Maori",
    SupportedLanguage.MARATHI: "Marathi",
    SupportedLanguage.MONGOLIAN: "Mongolian",
    SupportedLanguage.NEPALI: "Nepali",
    SupportedLanguage.NORTHERN_SOTHO: "Northern Sotho",
    SupportedLanguage.NORWEGIAN: "Norwegian",
    SupportedLanguage.NYANJA: "Nyanja",
    SupportedLanguage.OCCITAN: "Occitan",
    SupportedLanguage.ORIYA: "Oriya",
    SupportedLanguage.OROMO: "Oromo",
    SupportedLanguage.PASHTO: "Pashto",
    SupportedLanguage.PERSIAN: "Persian",
    SupportedLanguage.POLISH: "Polish",
    SupportedLanguage.PORTUGUESE: "Portuguese",
    SupportedLanguage.PUNJABI: "Punjabi",
    SupportedLanguage.ROMANIAN: "Romanian",
    SupportedLanguage.RUSSIAN: "Russian",
    SupportedLanguage.SERBIAN: "Serbian",
    SupportedLanguage.SHONA: "Shona",
    SupportedLanguage.SINDHI: "Sindhi",
    SupportedLanguage.SLOVAK: "Slovak",
    SupportedLanguage.SLOVENIAN: "Slovenian",
    SupportedLanguage.SOMALI: "Somali",
    SupportedLanguage.SORANI_KURDISH: "Sorani Kurdish",
    SupportedLanguage.SPANISH: "Spanish",
    SupportedLanguage.SWAHILI: "Swahili",
    SupportedLanguage.SWEDISH: "Swedish",
    SupportedLanguage.TAJIK: "Tajik",
    SupportedLanguage.TAMIL: "Tamil",
    SupportedLanguage.TELUGU: "Telugu",
    SupportedLanguage.THAI: "Thai",
    SupportedLanguage.TURKISH: "Turkish",
    SupportedLanguage.UKRAINIAN: "Ukrainian",
    SupportedLanguage.UMBUNDU: "Umbundu",
    SupportedLanguage.URDU: "Urdu",
    SupportedLanguage.UZBEK: "Uzbek",
    SupportedLanguage.VIETNAMESE: "Vietnamese",
    SupportedLanguage.WELSH: "Welsh",
    SupportedLanguage.WOLOF: "Wolof",
    SupportedLanguage.XHOSA: "Xhosa",
    SupportedLanguage.YORUBA: "Yoruba",
    SupportedLanguage.ZULU: "Zulu"
}

class ProcessingOptions(BaseModel):
    target_language: Optional[SupportedLanguage] = Field(None, description="Zielsprache für Übersetzung (optional)")

class UploadResponse(BaseModel):
    processing_id: str = Field(..., description="Eindeutige ID für die Verarbeitung")
    filename: str = Field(..., description="Ursprünglicher Dateiname")
    file_type: DocumentType = Field(..., description="Typ der hochgeladenen Datei")
    file_size: int = Field(..., description="Dateigröße in Bytes")
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    message: str = Field(default="Datei erfolgreich hochgeladen")

class ProcessingProgress(BaseModel):
    processing_id: str
    status: ProcessingStatus
    progress_percent: int = Field(ge=0, le=100)
    current_step: str
    message: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class TranslationResult(BaseModel):
    processing_id: str
    original_text: str = Field(..., description="Ursprünglicher extrahierter Text")
    translated_text: str = Field(..., description="Übersetzter Text in einfacher Sprache")
    language_translated_text: Optional[str] = Field(None, description="In andere Sprache übersetzter Text")
    target_language: Optional[SupportedLanguage] = Field(None, description="Zielsprache der Übersetzung")
    document_type_detected: str = Field(..., description="Erkannter Dokumenttyp")
    confidence_score: float = Field(ge=0, le=1, description="Vertrauensgrad der Übersetzung")
    language_confidence_score: Optional[float] = Field(None, description="Vertrauensgrad der Sprachübersetzung")
    processing_time_seconds: float = Field(..., description="Verarbeitungszeit in Sekunden")
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    error: str
    message: str
    processing_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, str] = Field(default_factory=dict)
    memory_usage: Optional[Dict[str, Any]] = None 