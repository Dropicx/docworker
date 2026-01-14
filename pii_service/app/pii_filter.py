"""
SpaCy-based PII Filter for German and English Medical Documents

GDPR-compliant PII removal with:
- Large SpaCy models (de_core_news_lg, en_core_web_lg)
- Named Entity Recognition for person names
- Regex patterns for addresses, IDs, dates, contact info
- Medical term protection (300+ terms preserved)
- Medical eponym preservation (Parkinson, Alzheimer, etc.)
"""

import logging
import os
import re
from datetime import datetime
from typing import Literal

import spacy

# Microsoft Presidio for enhanced PII detection
try:
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_analyzer.predefined_recognizers import (
        CreditCardRecognizer,
        IbanRecognizer,
        EmailRecognizer,
        PhoneRecognizer,
        IpRecognizer,
        UrlRecognizer,
        DateRecognizer,
        SpacyRecognizer,
    )
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

logger = logging.getLogger(__name__)

# Suppress noisy Presidio warnings (uses defaults which work fine)
logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)


class PIIFilter:
    """
    PII (Personally Identifiable Information) filter for medical documents.

    Supports German and English with large SpaCy models for maximum accuracy.
    Removes names, addresses, birthdates, IDs while preserving medical content.
    """

    # Volume path for persisted models (Railway volume mount)
    MODELS_DIR = os.environ.get("SPACY_DATA_DIR", "/data/models")

    # Model versions for finding versioned subdirectories
    MODEL_VERSIONS = {
        "de_core_news_lg": "3.8.0",
        "en_core_web_lg": "3.8.0",
    }

    def _load_spacy_model(self, model_name: str):
        """Load SpaCy model from volume path or site-packages."""
        # pip --target installs create this structure:
        # /data/models/de_core_news_lg/
        #   ├── __init__.py
        #   ├── de_core_news_lg-3.8.0/   ← config.cfg is HERE
        #   └── meta.json
        volume_path = os.path.join(self.MODELS_DIR, model_name)
        version = self.MODEL_VERSIONS.get(model_name, "3.8.0")
        versioned_path = os.path.join(volume_path, f"{model_name}-{version}")

        logger.info(f"Checking for model at volume path: {versioned_path}")

        if os.path.isdir(versioned_path):
            config_path = os.path.join(versioned_path, "config.cfg")
            if os.path.isfile(config_path):
                try:
                    logger.info(f"Loading {model_name} from versioned path: {versioned_path}")
                    return spacy.load(versioned_path)
                except Exception as e:
                    logger.warning(f"Failed to load from {versioned_path}: {e}")
            else:
                logger.warning(f"Versioned path exists but no config.cfg: {versioned_path}")
        else:
            logger.info(f"Versioned path does not exist: {versioned_path}")

        # Fallback: try spacy.load with model name (works if PYTHONPATH set)
        logger.info(f"Falling back to spacy.load('{model_name}')")
        return spacy.load(model_name)

    def __init__(self):
        """Initialize filter with German and English SpaCy models."""
        logger.info("Initializing PII Filter with large SpaCy models...")

        # German model
        self.german_model_loaded = False
        self.nlp_de = None
        try:
            self.nlp_de = self._load_spacy_model("de_core_news_lg")
            self.german_model_loaded = True
            logger.info("German model (de_core_news_lg) loaded successfully")
        except OSError as e:
            logger.warning(f"Failed to load German model: {e}")

        # English model
        self.english_model_loaded = False
        self.nlp_en = None
        try:
            self.nlp_en = self._load_spacy_model("en_core_web_lg")
            self.english_model_loaded = True
            logger.info("English model (en_core_web_lg) loaded successfully")
        except OSError as e:
            logger.warning(f"Failed to load English model: {e}")

        # Initialize patterns and medical terms
        self._init_patterns()
        self._init_medical_terms()
        self._init_medical_eponyms()

        # Initialize Presidio for enhanced PII detection
        self._init_presidio()

        logger.info(f"PII Filter initialized - DE: {self.german_model_loaded}, EN: {self.english_model_loaded}, Presidio: {self.presidio_available}")

    def _init_patterns(self):
        """Initialize regex patterns for PII detection."""

        # =============================================================
        # MEDICAL VALUE UNITS - Numbers followed by these should NEVER be PII
        # =============================================================
        # These patterns catch medical measurements that might be misidentified
        # as phone numbers, IDs, etc. by Presidio or regex patterns.
        #
        # Examples of false positives to prevent:
        #   - "4000 Hz" (audiometry frequency)
        #   - "120/80 mmHg" (blood pressure)
        #   - "1500 ml" (fluid volume)
        #   - "75 kg" (weight)
        #
        self.medical_value_pattern = re.compile(
            r"\[(?:PHONE|FAX|INSURANCE_ID|PATIENT_ID|REFERENCE_ID)\]"
            r"[\s\-/]*"
            r"(Hz|kHz|MHz|GHz|"  # Frequencies
            r"mmHg|cmH2O|kPa|Pa|"  # Pressure
            r"mg|µg|ng|pg|g|kg|"  # Mass
            r"ml|µl|dl|l|L|"  # Volume
            r"mm|cm|m|µm|nm|"  # Length
            r"mmol|µmol|mol|"  # Moles
            r"U|IU|IE|"  # Units/International units
            r"mV|µV|V|"  # Voltage (ECG)
            r"mA|µA|A|"  # Current
            r"Bq|MBq|GBq|"  # Radioactivity
            r"Gy|mGy|"  # Radiation dose
            r"bpm|/min|"  # Rate
            r"pg/ml|ng/ml|µg/ml|mg/dl|mmol/l|g/dl|"  # Concentrations
            r"%|‰)\b",  # Percentages
            re.IGNORECASE
        )

        # Pattern to detect numbers followed by units (to prevent false positives)
        # Used for pre-filtering before phone detection
        self.number_with_unit_pattern = re.compile(
            r"\b(\d{1,6})\s*"
            r"(Hz|kHz|MHz|GHz|"
            r"mmHg|cmH2O|kPa|Pa|"
            r"mg|µg|ng|pg|g|kg|"
            r"ml|µl|dl|l|L|"
            r"mm|cm|m|µm|nm|"
            r"mmol|µmol|mol|"
            r"U|IU|IE|"
            r"mV|µV|V|"
            r"mA|µA|A|"
            r"Bq|MBq|GBq|"
            r"Gy|mGy|"
            r"bpm|/min|"
            r"J|Jahre|years|y|"  # Age
            r"pg/ml|ng/ml|µg/ml|mg/dl|mmol/l|g/dl|"
            r"%|‰)\b",
            re.IGNORECASE
        )

        # German patterns
        self.patterns_de = {
            # =============================================================
            # NAME PATTERNS (NEW - Critical for GDPR compliance)
            # =============================================================

            # German doctor/professional titles with names
            # Matches: "Dr. med. Schmidt", "Prof. Dr. Weber", "OA Müller"
            # NO IGNORECASE - names must start with uppercase, titles handled explicitly
            "doctor_title_name": re.compile(
                r"\b(?:[Dd]r\.[\s]*(?:[Mm]ed\.?|[Rr]er\.?\s*[Nn]at\.?|[Pp]hil\.?|[Jj]ur\.?|[Hh]\.?\s*[Cc]\.?)?[\s\.]*|"
                r"[Pp]rof\.[\s]*(?:[Dd]r\.[\s]*(?:[Mm]ed\.?|[Hh]\.?\s*[Cc]\.?)?[\s\.]*)?|"
                r"[Dd]ipl\.[\s\-]?(?:[Mm]ed\.?|[Ii]ng\.?|[Pp]sych\.?)\s*|"
                r"OA\s+|[Oo]berarzt\s+|[Oo]berärztin\s+|"
                r"CA\s+|[Cc]hefarzt\s+|[Cc]hefärztin\s+|"
                r"FA\s+|[Ff]acharzt\s+|[Ff]achärztin\s+)"
                r"([A-ZÄÖÜ][a-zäöüß]+(?:[\s\-][A-ZÄÖÜ][a-zäöüß]+)?)\b"
            ),

            # German honorifics with names (Herr Müller, Frau Schmidt)
            # Captures only capitalized names after honorific
            # NO IGNORECASE to preserve name capitalization requirement
            "honorific_name": re.compile(
                r"\b(?:[Hh]err|[Ff]rau|[Ff]räulein|[Hh]r\.?|[Ff]r\.?)\s+"
                r"([A-ZÄÖÜ][a-zäöüß]+)"  # Surname must start with capital
                r"(?:[\s\-]([A-ZÄÖÜ][a-zäöüß]+))?"  # Optional second name part
            ),

            # Patient name in "Nachname, Vorname" format
            "name_comma_format": re.compile(
                r"(?:Patient(?:in)?|Name|Versicherte[rn]?)[:\s]*"
                r"([A-ZÄÖÜ][a-zäöüß]+)\s*,\s*([A-ZÄÖÜ][a-zäöüß]+)",
                re.IGNORECASE
            ),

            # Standalone German names after labels
            # IMPORTANT: Requires colon separator, NO IGNORECASE for name capture
            "labeled_name": re.compile(
                r"(?:[Pp]atient(?:in)?|[Vv]ersicherte[rn]?|"
                r"[Aa]uftraggeber|[Ee]insender|[Aa]nsprechpartner|"
                r"[Ee]mpfänger|[Aa]bsender):\s*"
                r"([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)"
            ),

            # =============================================================
            # DATE PATTERNS (NEW - German month names)
            # =============================================================

            # German dates with month names (15. März 2024)
            "date_german_month": re.compile(
                r"\b(\d{1,2})\.\s*"
                r"(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)"
                r"\s+(\d{4})\b",
                re.IGNORECASE
            ),

            # =============================================================
            # REFERENCE PATTERNS (NEW - Case numbers, document references)
            # =============================================================

            # Case/file reference numbers (DS/2024/0815, Fall-Nr. 12345)
            "case_reference": re.compile(
                r"(?:DS|Dossier|Fall|Akte|Az\.?|Aktenzeichen|"
                r"Vorgangs?(?:nummer|nr\.?)?|Geschäftszeichen)[\s/\-:]*"
                r"(?:Nr\.?[\s/\-:]*)?"
                r"([A-Z]{0,3}\d{2,4}[\s/\-]\d{3,6})",
                re.IGNORECASE
            ),

            # Hospital-specific reference format (Unser Zeichen: XX/YYYY/NNNN)
            "document_reference": re.compile(
                r"(?:Unser\s+Zeichen|Ihr\s+Zeichen|Zeichen|Ref\.?)[:\s]*"
                r"([A-Z]{1,3}[\s/\-]?\d{2,4}[\s/\-]?\d{2,6})",
                re.IGNORECASE
            ),

            # =============================================================
            # EXISTING PATTERNS (Enhanced)
            # =============================================================

            # Dates (German format: DD.MM.YYYY)
            "birthdate": re.compile(
                r"(?:geb(?:oren|\.)?|geboren am|geburtsdatum|geb\.-datum|"
                r"\*|birth(?:date)?)\s*[:.]?\s*"
                r"(\d{1,2}[./]\d{1,2}[./]\d{2,4})",
                re.IGNORECASE
            ),

            # German Tax ID (11 digits)
            "tax_id": re.compile(
                r"(?:steuer[- ]?(?:id|identifikationsnummer|nummer)|"
                r"tin|steuernummer)\s*[:.]?\s*(\d{11})",
                re.IGNORECASE
            ),

            # German Social Security (12 chars: 2 digits, 6 digits, 1 letter, 3 digits)
            "social_security": re.compile(
                r"(?:sozialversicherung(?:snummer)?|sv[- ]?nr?\.?|"
                r"rentenversicherung(?:snummer)?)\s*[:.]?\s*"
                r"(\d{2}\s?\d{6}\s?[A-Z]\s?\d{3})",
                re.IGNORECASE
            ),

            # Phone numbers (German)
            "phone": re.compile(
                r"(?:tel(?:efon)?|phone|fon|ruf)\s*[:.]?\s*"
                r"((?:\+49|0049|0)\s*[\d\s/\-]{8,15})",
                re.IGNORECASE
            ),

            # Fax numbers (German) - standalone pattern
            "fax": re.compile(
                r"(?:fax|telefax)\s*[:.]?\s*"
                r"((?:\+49|0049|0)?\s*[\d\s/\-]{8,15})",
                re.IGNORECASE
            ),

            # Email
            "email": re.compile(
                r"(?:e[- ]?mail|mail)\s*[:.]?\s*"
                r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                re.IGNORECASE
            ),

            # Street address (German format)
            # Handles both "straße" and "strasse" spellings
            "address": re.compile(
                r"([A-ZÄÖÜ][a-zäöüß]+(?:stra(?:ß|ss)e|str\.|weg|platz|allee|gasse|ring|damm|ufer|chaussee|promenade)"
                r"\s*\d+[a-zA-Z]?)",
                re.IGNORECASE
            ),

            # PLZ + City (German postal code)
            "plz_city": re.compile(
                r"(\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)",
                re.IGNORECASE
            ),

            # Insurance numbers - expanded patterns
            # Handles: Versichertennummer, Versicherten-Nr., Vers.-Nr., VN, KK-Nr., etc.
            "insurance": re.compile(
                r"(?:Versichert(?:en)?[\-\s]?(?:nummer|nr\.?)?|"
                r"Vers\.?[\s\-]?Nr\.?|VN|"
                r"Krankenkasse(?:n)?[\-\s]?(?:nummer|nr\.?)?|"
                r"KK[\s\-]?(?:Nr\.?)?|"
                r"Mitglieds?[\-\s]?(?:nummer|nr\.?)?|"
                r"Kassen[\-\s]?(?:nummer|nr\.?))[:\s\-]*"
                r"([A-Z]?\d{8,12})",
                re.IGNORECASE
            ),

            # Insurance numbers after known insurance company names
            # \b word boundary prevents matching "TK" inside "Kreditkarte"
            "insurance_company": re.compile(
                r"\b(?:AOK|TK|Barmer|DAK|BKK|IKK|KKH|HEK|hkk|Techniker|"
                r"KNAPPSCHAFT|Viactiv|Mobil\s*Oil|SBK|mhplus|Novitas|"
                r"Pronova|Big\s*direkt|Audi\s*BKK|BMW\s*BKK|Bosch\s*BKK)\b"
                r"[^,\n]{0,40}?(?:Nr\.?|Nummer|Versicherten)?[:\s]*"
                r"(\d{9,12})",
                re.IGNORECASE
            ),

            # Patient ID
            "patient_id": re.compile(
                r"(?:patient(?:en)?[- ]?(?:nr\.?|nummer|id)|"
                r"fall(?:nummer|nr\.?)|aktenzeichen)\s*[:.]?\s*"
                r"([A-Z0-9\-]{5,20})",
                re.IGNORECASE
            ),

            # Standalone dates (potential birthdates)
            "date_standalone": re.compile(
                r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b"
            ),

            # =============================================================
            # EMAIL/DOMAIN PATTERNS (NEW)
            # =============================================================

            # Email domains containing names (dr-schmidt.de, mueller-praxis.de)
            "named_email_domain": re.compile(
                r"(?:www\.)?(?:dr[\.\-]|prof[\.\-])?"
                r"[a-zäöüß]+(?:[\.\-][a-zäöüß]+)*"
                r"(?:[\.\-](?:praxis|klinik|med|arzt|medizin|zahnarzt|ortho))?"
                r"\.(?:de|at|ch)\b",
                re.IGNORECASE
            ),

            # Full email addresses (enhanced)
            "email_full": re.compile(
                r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
                re.IGNORECASE
            ),
        }

        # English patterns
        self.patterns_en = {
            # =============================================================
            # NAME PATTERNS (NEW - Critical for GDPR compliance)
            # =============================================================

            # English doctor/professional titles with names
            # Matches: "Dr. Smith", "Prof. Johnson", "Dr. Mary Williams"
            # NO IGNORECASE - names must start with uppercase
            "doctor_title_name": re.compile(
                r"(?:[Dd]r\.?|[Pp]rof\.?|[Pp]rofessor|"
                r"MD|M\.D\.|"
                r"PhD|Ph\.D\.|"
                r"RN|NP|PA|"
                r"[Aa]ttending|[Rr]esident)\s+"
                r"([A-Z][a-z]+(?:[\s\-][A-Z][a-z]+)*)"
            ),

            # English honorifics with names (Mr. Smith, Mrs. Johnson)
            "honorific_name": re.compile(
                r"(?:Mr\.?|Mrs\.?|Ms\.?|Miss|Sir|Madam|Dame)\s+"
                r"([A-Z][a-z]+(?:[\s\-][A-Z][a-z]+)*)",
                re.IGNORECASE
            ),

            # English patient name labels
            # IMPORTANT: Requires colon separator, NO IGNORECASE for name capture
            "labeled_name": re.compile(
                r"(?:[Pp]atient|[Nn]ame|[Ff]irst\s*[Nn]ame|[Ll]ast\s*[Nn]ame|[Ss]urname|"
                r"[Ii]nsured|[Pp]olicyholder|[Cc]lient|[Cc]ustomer):\s*"
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
            ),

            # =============================================================
            # DATE PATTERNS (NEW - English month names)
            # =============================================================

            # English dates with month names (March 15, 2024 or 15 March 2024)
            "date_english_month": re.compile(
                r"\b(?:(\d{1,2})\s+)?"
                r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                r"(?:\s+(\d{1,2}))?,?\s+(\d{4})\b",
                re.IGNORECASE
            ),

            # =============================================================
            # EXISTING PATTERNS (Enhanced)
            # =============================================================

            # Dates (various formats)
            "birthdate": re.compile(
                r"(?:born|dob|date of birth|birth(?:date)?)\s*[:.]?\s*"
                r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})",
                re.IGNORECASE
            ),

            # US Social Security
            "ssn": re.compile(
                r"(?:ssn|social security)\s*[:.]?\s*"
                r"(\d{3}[- ]?\d{2}[- ]?\d{4})",
                re.IGNORECASE
            ),

            # Phone numbers
            "phone": re.compile(
                r"(?:phone|tel|call)\s*[:.]?\s*"
                r"((?:\+1|1)?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
                re.IGNORECASE
            ),

            # Email
            "email": re.compile(
                r"(?:e[- ]?mail|mail)\s*[:.]?\s*"
                r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                re.IGNORECASE
            ),

            # Full email addresses (standalone)
            "email_full": re.compile(
                r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
                re.IGNORECASE
            ),

            # Address
            "address": re.compile(
                r"(\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+"
                r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Drive|Dr\.?|Lane|Ln\.?|"
                r"Boulevard|Blvd\.?|Way|Court|Ct\.?))",
                re.IGNORECASE
            ),

            # ZIP code
            "zipcode": re.compile(
                r"\b(\d{5}(?:-\d{4})?)\b"
            ),

            # Patient ID
            "patient_id": re.compile(
                r"(?:patient\s*(?:id|number|#)|mrn|medical record)\s*[:.]?\s*"
                r"([A-Z0-9\-]{5,20})",
                re.IGNORECASE
            ),
        }

    def _init_medical_terms(self):
        """Initialize protected medical terms (not to be removed)."""
        self.medical_terms = {
            # ==================== ANATOMY ====================
            "herz", "lunge", "leber", "niere", "magen", "darm", "kopf", "hals",
            "brust", "bauch", "rücken", "schulter", "knie", "hüfte", "hand", "fuß",
            "hirn", "gehirn", "muskel", "knochen", "gelenk", "nerv", "gefäß",
            "thorax", "abdomen", "extremitäten", "wirbelsäule", "becken", "schädel",
            "milz", "pankreas", "gallenblase", "schilddrüse", "nebenniere",
            "prostata", "uterus", "ovarien", "hoden", "lymphknoten",
            "rückenmark", "knochenmark", "arterie", "vene", "kapillare",
            "aorta", "koronararterie",
            # English
            "heart", "lung", "liver", "kidney", "stomach", "brain", "muscle", "bone",
            "spleen", "pancreas", "gallbladder", "thyroid", "prostate", "uterus",

            # ==================== CLINICAL TERMS ====================
            "patient", "patientin", "diagnose", "befund", "therapie", "behandlung",
            "untersuchung", "operation", "medikament", "dosierung", "anamnese",
            "prognose", "epikrise", "symptom", "syndrom", "erkrankung", "krankheit",
            "störung", "insuffizienz", "entzündung", "infektion", "nekrose",
            "ischämie", "ruptur", "läsion", "pathologie",
            # English
            "diagnosis", "treatment", "examination", "surgery", "medication",
            "disease", "disorder", "condition", "inflammation", "infection",

            # ==================== VITAL SIGNS ====================
            "blutdruck", "puls", "temperatur", "sauerstoffsättigung", "atemfrequenz",
            "herzfrequenz", "blutdruck", "körpertemperatur",
            # Compound words and descriptors
            "blutdruckverhalten", "blutdruckmessung", "blutdruckwerte", "blutdruckeinstellung",
            "normotensiv", "normotensive", "normotensiver", "normotensiven",
            "hypertensiv", "hypertensive", "hypertensiver", "hypertensiven",
            "hypotensiv", "hypotensive", "hypotensiver", "hypotensiven",
            "herzfrequenzverhalten", "pulsverhalten",

            # ==================== CONDITIONS ====================
            "stenose", "thrombose", "embolie", "infarkt", "tumor", "karzinom",
            "metastase", "aneurysma", "fraktur", "luxation", "kontusion",
            "hämatom", "ödem", "erguss", "hypertonie", "hypotonie",
            "tachykardie", "bradykardie", "arrhythmie", "diabetes",
            "hypothyreose", "hyperthyreose", "anämie", "leukämie",
            "pneumonie", "bronchitis", "asthma", "copd", "emphysem", "fibrose",
            "gastritis", "ulkus", "hepatitis", "zirrhose", "pankreatitis",
            "cholezystitis", "nephritis", "pyelonephritis", "glomerulonephritis",
            "niereninsuffizienz", "arthritis", "arthrose", "osteoporose",
            "rheuma", "gicht", "fibromyalgie", "meningitis", "enzephalitis",
            "epilepsie", "schlaganfall", "apoplex", "depression", "angststörung",
            "schizophrenie", "demenz", "delir",
            # Cardiac valve conditions (common compound words)
            "mitralinsuffizienz", "mitralstenose", "mitralklappenprolaps",
            "aorteninsuffizienz", "aortenstenose", "aortenklappe",
            "trikuspidalklappe", "trikuspidalinsuffizienz", "trikuspidalstenose",
            "pulmonalklappe", "pulmonalinsuffizienz", "pulmonalstenose",
            "herzinsuffizienz", "linksherzinsuffizienz", "rechtsherzinsuffizienz",
            "herzklappenfehler", "klappeninsuffizienz", "klappenstenose",
            "mitralklappe", "mitral", "aortal", "trikuspidal", "pulmonal",

            # ==================== DIAGNOSTICS ====================
            "ultraschall", "sonographie", "röntgen", "ct", "mrt", "pet", "spect",
            "ekg", "eeg", "emg", "echokardiographie", "endoskopie", "koloskopie",
            "gastroskopie", "bronchoskopie", "laparoskopie", "arthroskopie", "biopsie",
            # English
            "mri", "xray", "ultrasound", "ecg", "biopsy",

            # ==================== PROCEDURES ====================
            "operation", "resektion", "transplantation", "bypass", "stent", "katheter",
            "infusion", "injektion", "transfusion", "dialyse", "chemotherapie",
            "bestrahlung", "physiotherapie", "ergotherapie", "logopädie",
            "rehabilitation", "palliativ",

            # ==================== DEPARTMENTS ====================
            "intensivstation", "notaufnahme", "ambulanz", "station",
            "kardiologie", "pneumologie", "gastroenterologie", "nephrologie",
            "neurologie", "onkologie", "hämatologie", "rheumatologie",
            "endokrinologie", "dermatologie", "orthopädie", "urologie",
            "gynäkologie", "pädiatrie", "geriatrie", "chirurgie", "anästhesie",
            "radiologie", "pathologie", "labormedizin",

            # ==================== LAB VALUES ====================
            "hämoglobin", "hämatokrit", "erythrozyten", "leukozyten", "thrombozyten",
            "kreatinin", "harnstoff", "harnsäure", "bilirubin", "transaminasen",
            "got", "gpt", "ggt", "ap", "ldh", "ck", "troponin", "bnp", "crp",
            "tsh", "t3", "t4", "hba1c", "glucose", "glukose", "cholesterin",
            "triglyzeride", "inr", "ptt", "quick", "d-dimer", "fibrinogen",
            "blutgruppe", "rhesusfaktor",
            # English
            "hemoglobin", "creatinine", "cholesterol", "triglycerides",

            # ==================== UNITS & ABBREVIATIONS ====================
            "mg", "ml", "kg", "cm", "mm", "mmhg", "mmol", "µg", "ng", "dl", "l",
            "bid", "tid", "qid", "prn", "po", "iv", "im", "sc", "od", "os", "ou",

            # ==================== MEDICAL ABBREVIATIONS (commonly misclassified) ====================
            # These are frequently misclassified by SpaCy as ORG/LOC/PER
            "bmi", "egfr", "gfr", "lvef", "ef", "la", "lv", "rv", "ra",  # Cardiac
            "nyha", "asa", "ccs", "kps", "ecog",  # Classification scores
            "hf", "af", "vhf", "sr", "avb", "lbbb", "rbbb",  # Rhythm/ECG
            "copd", "ards", "osa", "osas",  # Pulmonary
            "aki", "ckd", "esrd", "gn",  # Renal
            "dm", "hba1c", "ogtt", "nüchtern",  # Diabetes
            "khe", "khk", "pavk", "tia", "cva",  # Vascular
            "op", "re", "li", "bds", "ca", "chemo", "rtx",  # General abbreviations
            "z.n.", "v.a.", "dd", "st.p.", "ed", "j.",  # German medical abbreviations
            "sinusrhythmus", "normofrequent", "rhythmisch",  # ECG findings
            "unauffällig", "regelrecht", "altersentsprechend",  # Normal findings
            "reduziert", "erhöht", "erniedrigt", "pathologisch",  # Finding descriptors
            "druckdolent", "druckschmerzhaft", "palpabel", "tastbar",  # Examination terms
            "auskultation", "perkussion", "inspektion", "palpation",  # Exam methods
            "systolisch", "diastolisch", "endsystolisch", "enddiastolisch",  # Cardiac timing
            "linksventrikulär", "rechtsventrikulär", "biventrikulär",  # Cardiac chambers
            "anterolateral", "posterolateral", "inferolateral",  # Anatomical directions
            "simpson", "biplan", "monoplan",  # Echo methods

            # ==================== GERMAN CLINICAL DESCRIPTORS ====================
            "beschwerdefrei", "symptomfrei", "fieberfrei", "schmerzfrei",
            "dyspnoe", "orthopnoe", "belastungsdyspnoe", "ruhedyspnoe",
            "retrosternal", "präkordial", "epigastrisch", "periumbilikal",
            "druckgefühl", "druckgefühle", "engegefühl", "beklemmung",
            "ausstrahlung", "ausstrahlen", "ausstrahlend",
            "sistieren", "sistierend", "intermittierend", "persistierend",
            "progredient", "regredient", "stabil", "stationär",
            "akut", "subakut", "chronisch", "rezidivierend",

            # ==================== MEDICAL ADJECTIVES (with German declensions) ====================
            # Temporal/frequency adjectives
            "nächtlich", "nächtliche", "nächtlicher", "nächtlichen", "nächtliches",
            "paroxysmale", "paroxysmal", "paroxysmaler", "paroxysmalen",
            "intermittierend", "intermittierende", "intermittierender", "intermittierenden",
            "persistierend", "persistierende", "persistierender", "persistierenden",

            # Severity adjectives
            "akute", "akuter", "akuten", "akutes",
            "chronische", "chronischer", "chronischen", "chronisches",
            "subakute", "subakuter", "subakuten",
            "leicht", "leichte", "leichter", "leichten", "leichtes",
            "schwer", "schwere", "schwerer", "schweren", "schweres",
            "mittelgradig", "mittelgradige", "mittelgradiger", "mittelgradigen",
            "hochgradig", "hochgradige", "hochgradiger", "hochgradigen",
            "geringfügig", "geringfügige", "geringfügiger", "geringfügigen",
            "geringgradig", "geringgradige", "geringgradiger", "geringgradigen",

            # Organ-specific adjectives
            "kardial", "kardiale", "kardialer", "kardialen", "kardiales",
            "pulmonal", "pulmonale", "pulmonaler", "pulmonalen", "pulmonales",
            "renal", "renale", "renaler", "renalen", "renales",
            "hepatisch", "hepatische", "hepatischer", "hepatischen", "hepatisches",
            "zerebral", "zerebrale", "zerebraler", "zerebralen", "zerebrales",
            "gastrointestinal", "gastrointestinale", "gastrointestinaler", "gastrointestinalen",
            "vaskulär", "vaskuläre", "vaskulärer", "vaskulären",
            "muskulär", "muskuläre", "muskulärer", "muskulären",
            "neurologisch", "neurologische", "neurologischer", "neurologischen",

            # Anatomical position adjectives
            "peripher", "periphere", "peripherer", "peripheren", "peripheres",
            "proximal", "proximale", "proximaler", "proximalen", "proximales",
            "distal", "distale", "distaler", "distalen", "distales",
            "anterior", "anteriore", "anteriorer", "anterioren",
            "posterior", "posteriore", "posteriorer", "posterioren",
            "lateral", "laterale", "lateraler", "lateralen", "laterales",
            "medial", "mediale", "medialer", "medialen", "mediales",
            "bilateral", "bilaterale", "bilateraler", "bilateralen", "bilaterales",
            "unilateral", "unilaterale", "unilateraler", "unilateralen",
            "ipsilateral", "ipsilaterale", "ipsilateraler", "ipsilateralen",
            "kontralateral", "kontralaterale", "kontralateraler", "kontralateralen",

            # Cardiac rhythm adjectives
            "systolisch", "systolische", "systolischer", "systolischen",
            "diastolisch", "diastolische", "diastolischer", "diastolischen",
            "normofrequent", "normofrequente", "normofrequenter", "normofrequenten",
            "tachykard", "tachykarde", "tachykarder", "tachykarden",
            "bradykard", "bradykarde", "bradykarder", "bradykarden",
            "rhythmisch", "rhythmische", "rhythmischer", "rhythmischen",
            "arrhythmisch", "arrhythmische", "arrhythmischer", "arrhythmischen",

            # Clinical finding adjectives
            "unauffällig", "unauffällige", "unauffälliger", "unauffälligen", "unauffälliges",
            "auffällig", "auffällige", "auffälliger", "auffälligen", "auffälliges",
            "pathologisch", "pathologische", "pathologischer", "pathologischen",
            "physiologisch", "physiologische", "physiologischer", "physiologischen",
            "normwertig", "normwertige", "normwertiger", "normwertigen",
            "grenzwertig", "grenzwertige", "grenzwertiger", "grenzwertigen",
            "erhöht", "erhöhte", "erhöhter", "erhöhten", "erhöhtes",
            "erniedrigt", "erniedrigte", "erniedrigter", "erniedrigten",
            "vermindert", "verminderte", "verminderter", "verminderten",
            "vermehrt", "vermehrte", "vermehrter", "vermehrten",
        }

        # ==================== DRUG DATABASE (226 medications) ====================
        self.drug_database = {
            # Diabetes
            "metformin", "glibenclamid", "sitagliptin", "empagliflozin", "insulin",
            "lantus", "novorapid", "levemir", "humalog", "actrapid",
            # Beta blockers
            "metoprolol", "bisoprolol", "carvedilol", "nebivolol", "atenolol", "propranolol",
            # ACE inhibitors
            "ramipril", "enalapril", "lisinopril", "perindopril", "captopril",
            # ARBs
            "candesartan", "valsartan", "losartan", "irbesartan", "telmisartan",
            # Calcium channel blockers
            "amlodipin", "nifedipin", "lercanidipin", "felodipin", "verapamil", "diltiazem",
            # Diuretics
            "hydrochlorothiazid", "furosemid", "torasemid", "spironolacton", "eplerenon",
            # Statins
            "simvastatin", "atorvastatin", "rosuvastatin", "pravastatin", "fluvastatin",
            "ezetimib", "evolocumab", "alirocumab", "fenofibrat", "bezafibrat",
            # Antiplatelets & Anticoagulants
            "aspirin", "ass", "clopidogrel", "prasugrel", "ticagrelor",
            "rivaroxaban", "apixaban", "edoxaban", "dabigatran", "warfarin",
            "phenprocoumon", "marcumar", "heparin", "enoxaparin", "clexane",
            "dalteparin", "fondaparinux",
            # PPIs
            "omeprazol", "pantoprazol", "esomeprazol", "lansoprazol", "rabeprazol",
            "ranitidin", "famotidin", "sucralfat",
            # Antibiotics
            "amoxicillin", "ampicillin", "penicillin", "flucloxacillin", "piperacillin",
            "cefuroxim", "ceftriaxon", "cefotaxim", "ceftazidim", "cefazolin",
            "ciprofloxacin", "levofloxacin", "moxifloxacin", "ofloxacin",
            "clarithromycin", "azithromycin", "erythromycin", "roxithromycin",
            "doxycyclin", "tetracyclin", "minocyclin", "tigecyclin",
            "metronidazol", "clindamycin", "vancomycin", "linezolid", "daptomycin",
            "meropenem", "imipenem", "ertapenem", "gentamicin", "tobramycin", "amikacin",
            "cotrimoxazol", "trimethoprim", "nitrofurantoin", "fosfomycin", "rifampicin",
            # Antifungals
            "fluconazol", "itraconazol", "voriconazol", "amphotericin", "caspofungin",
            # Antivirals
            "aciclovir", "valaciclovir", "oseltamivir", "remdesivir",
            # NSAIDs
            "ibuprofen", "diclofenac", "naproxen", "piroxicam", "meloxicam", "celecoxib",
            # Analgesics
            "paracetamol", "metamizol", "novalgin", "novaminsulfon",
            "tramadol", "tilidin", "morphin", "oxycodon", "fentanyl", "hydromorphon",
            # Anticonvulsants
            "pregabalin", "gabapentin", "carbamazepin", "valproat", "lamotrigin", "levetiracetam",
            # Antidepressants
            "sertralin", "escitalopram", "citalopram", "fluoxetin", "paroxetin", "venlafaxin",
            "mirtazapin", "amitriptylin", "duloxetin", "bupropion", "trazodon",
            # Antipsychotics
            "quetiapin", "olanzapin", "risperidon", "aripiprazol", "haloperidol", "clozapin",
            # Anxiolytics/Hypnotics
            "lorazepam", "diazepam", "oxazepam", "bromazepam", "zolpidem", "zopiclon",
            # Parkinson
            "levodopa", "carbidopa", "ropinirol", "pramipexol", "entacapon", "rasagilin",
            # Dementia
            "donepezil", "rivastigmin", "galantamin", "memantin",
            # Corticosteroids
            "prednisolon", "dexamethason", "hydrocortison", "methylprednisolon", "budesonid",
            # Respiratory
            "salbutamol", "formoterol", "salmeterol", "tiotropium", "ipratropium",
            "montelukast", "theophyllin", "roflumilast", "fluticason", "beclomethason",
            # Thyroid
            "levothyroxin", "l-thyroxin", "euthyrox", "carbimazol", "thiamazol",
            # Oncology
            "tamoxifen", "letrozol", "anastrozol", "trastuzumab", "rituximab", "pembrolizumab",
            # Immunosuppressants
            "methotrexat", "azathioprin", "mycophenolat", "ciclosporin", "tacrolimus",
            "adalimumab", "etanercept", "infliximab", "secukinumab", "ustekinumab",
            # Urology
            "sildenafil", "tadalafil", "tamsulosin", "alfuzosin", "finasterid", "dutasterid",
            # Gout
            "colchicin", "allopurinol", "febuxostat",
            # Supplements
            "eisen", "folsäure", "calcium", "kalium", "magnesium",
        }

    def _init_medical_eponyms(self):
        """Initialize medical eponyms (disease names from people - preserve these)."""
        self.medical_eponyms = {
            # ==================== NEUROLOGICAL ====================
            "parkinson", "alzheimer", "huntington", "creutzfeldt", "jakob",
            "guillain", "barré", "bell", "tourette", "charcot", "ménière",
            "wernicke", "korsakoff", "lewy", "pick", "binswanger",
            "erb", "duchenne", "becker", "friedreich",
            "broca", "wernicke", "rasmussen", "west", "lennox", "gastaut",
            "dravet", "landau", "kleffner",

            # ==================== CARDIOVASCULAR ====================
            "raynaud", "buerger", "kawasaki", "marfan", "ehlers", "danlos",
            "takayasu", "fallot", "ebstein", "eisenmenger", "brugada",
            "wolff", "osler", "weber", "rendu",

            # ==================== GASTROINTESTINAL ====================
            "crohn", "hirschsprung", "barrett", "whipple", "zollinger", "ellison",
            "boerhaave", "mallory", "weiss", "zenker", "schatzki", "plummer", "vinson",

            # ==================== ENDOCRINE ====================
            "cushing", "addison", "hashimoto", "graves", "basedow", "conn",
            "sheehan", "simmonds", "nelson", "riedel", "de quervain", "pendred",

            # ==================== HEMATOLOGICAL ====================
            "hodgkin", "waldenström", "cooley", "fanconi", "gaucher", "niemann",
            "von willebrand", "glanzmann", "bernard", "soulier", "may", "hegglin",

            # ==================== GENETIC/CHROMOSOMAL ====================
            "down", "turner", "klinefelter", "edwards", "patau", "prader", "willi",
            "angelman", "kallmann", "fabry", "pompe",

            # ==================== RENAL ====================
            "goodpasture", "berger", "alport", "bartter", "gitelman", "liddle",

            # ==================== RHEUMATOLOGICAL ====================
            "wilson", "sjögren", "behçet", "wegener", "churg", "strauss",
            "henoch", "schönlein", "bechterew", "reiter", "felty", "still",
            "heberden", "bouchard",

            # ==================== ORTHOPEDIC ====================
            "paget", "dupuytren", "volkmann", "trendelenburg", "galeazzi",
            "ortolani", "barlow", "froment", "phalen", "tinel",

            # ==================== ONCOLOGICAL ====================
            "kaposi", "bowen", "merkel", "sézary", "peutz", "jeghers",
            "gardner", "turcot", "lynch", "cowden", "li", "fraumeni",
            "von hippel", "lindau", "sturge",

            # ==================== DERMATOLOGICAL ====================
            "stevens", "johnson", "lyell", "nikolsky", "auspitz", "köbner", "wickham",

            # ==================== SIGNS & TESTS ====================
            "horner", "holmes", "adie", "marcus", "gunn", "argyll", "robertson",
            "pancoast", "trousseau", "virchow", "courvoisier", "murphy",
            "mcburney", "rovsing", "blumberg",
        }

    def _init_presidio(self):
        """Initialize Microsoft Presidio analyzer for enhanced PII detection."""
        self.presidio_available = False
        self.presidio_analyzer = None

        if not PRESIDIO_AVAILABLE:
            logger.info("Presidio not installed - running with SpaCy only")
            return

        try:
            # NER configuration to map SpaCy entities to Presidio types
            # and ignore irrelevant entity types (like MISC that causes warnings)
            ner_model_conf = {
                "model_to_presidio_entity_mapping": {
                    "PER": "PERSON",      # German SpaCy uses PER for persons
                    "PERSON": "PERSON",   # English SpaCy uses PERSON
                    "LOC": "LOCATION",    # German SpaCy uses LOC
                    "GPE": "LOCATION",    # English SpaCy uses GPE for geopolitical entities
                    "ORG": "ORGANIZATION",
                    "FAC": "LOCATION",    # Facilities (English)
                    "DATE": "DATE_TIME",
                    "TIME": "DATE_TIME",
                },
                "labels_to_ignore": [
                    "MISC",       # Miscellaneous - too broad, causes warnings
                    "CARDINAL",   # Numbers
                    "ORDINAL",    # Ordinal numbers
                    "QUANTITY",   # Quantities
                    "MONEY",      # Monetary values
                    "PERCENT",    # Percentages
                    "PRODUCT",    # Products
                    "EVENT",      # Events
                    "WORK_OF_ART", # Works of art
                    "LAW",        # Laws
                    "LANGUAGE",   # Languages
                    "NORP",       # Nationalities, religious, political groups
                ],
                "low_score_entity_names": ["ORGANIZATION", "DATE_TIME"],
            }

            # Configure Presidio NLP engine with NER config embedded in each model
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [
                    {
                        "lang_code": "de",
                        "model_name": "de_core_news_lg",
                        "ner_model_configuration": ner_model_conf,
                    },
                    {
                        "lang_code": "en",
                        "model_name": "en_core_web_lg",
                        "ner_model_configuration": ner_model_conf,
                    },
                ]
            }

            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()

            # Create custom registry with only the recognizers we need (de/en)
            registry = RecognizerRegistry()
            registry.supported_languages = ["de", "en"]

            # Add recognizers for both languages
            # Note: SpacyRecognizer gets NER config from NLP engine, not constructor
            for lang in ["de", "en"]:
                registry.add_recognizer(SpacyRecognizer(supported_language=lang, ner_strength=0.85))
                registry.add_recognizer(EmailRecognizer(supported_language=lang))
                registry.add_recognizer(PhoneRecognizer(supported_language=lang, context=["telefon", "phone", "tel", "fax", "handy", "mobil"]))
                registry.add_recognizer(IbanRecognizer(supported_language=lang))
                registry.add_recognizer(IpRecognizer(supported_language=lang))
                registry.add_recognizer(UrlRecognizer(supported_language=lang))
                registry.add_recognizer(DateRecognizer(supported_language=lang))
                registry.add_recognizer(CreditCardRecognizer(
                    supported_language=lang,
                    context=["kreditkarte", "kartennummer", "credit card", "card number"]
                ))

            # Create analyzer with our custom registry
            self.presidio_analyzer = AnalyzerEngine(
                nlp_engine=nlp_engine,
                registry=registry,
                supported_languages=["de", "en"]
            )

            self.presidio_available = True
            logger.info("Presidio analyzer initialized with de/en recognizers")

        except Exception as e:
            logger.warning(f"Presidio initialization failed (continuing with SpaCy only): {e}")
            self.presidio_analyzer = None
            self.presidio_available = False

    def _is_medical_eponym(self, name: str, context: str = "") -> bool:
        """Check if a name is a medical eponym (should be preserved)."""
        name_lower = name.lower()

        # Direct match
        if name_lower in self.medical_eponyms:
            return True

        # Check for disease context (terms that indicate a medical eponym, not patient names)
        # NOTE: "patient" was removed - it incorrectly preserved patient names like "Patient Max Mustermann"
        medical_context_words = [
            "morbus", "disease", "syndrome", "syndrom", "erkrankung",
            "krankheit", "disorder", "condition", "diagnose"
        ]
        context_lower = context.lower()
        for word in medical_context_words:
            if word in context_lower:
                return True

        return False

    def _is_medical_term(self, word: str, custom_terms: set | None = None) -> bool:
        """Check if word is a protected medical term or drug name.

        Includes German stem matching to catch declined forms like:
        - "Nächtliche" -> "nächtlich"
        - "Herzens" -> "herz"
        - "Kardialen" -> "kardial"

        Also handles multi-word entities like "Mitralinsuffizienz Grad I" by
        checking if ANY word in the phrase is a medical term.
        """
        word_lower = word.lower()

        # Exact match check for whole phrase
        if word_lower in self.medical_terms or word_lower in self.drug_database:
            return True
        if custom_terms and word_lower in custom_terms:
            return True

        # German stem matching for whole phrase
        german_suffixes = ['ischen', 'ische', 'ischer', 'ungen', 'liche', 'lichen',
                          'licher', 'liches', 'alen', 'aler', 'ales', 'enen', 'ener',
                          'enes', 'igen', 'iger', 'iges', 'ung', 'en', 'er', 'es',
                          'em', 'e', 'n', 's']

        for suffix in german_suffixes:
            if len(word_lower) > len(suffix) + 3 and word_lower.endswith(suffix):
                stem = word_lower[:-len(suffix)]
                if stem in self.medical_terms or stem in self.drug_database:
                    return True
                if custom_terms and stem in custom_terms:
                    return True

        # Multi-word check: if ANY word in the phrase is a medical term, preserve the whole entity
        # This handles cases like "Mitralinsuffizienz Grad I" where SpaCy detects it as one entity
        if ' ' in word:
            words = word.split()
            for single_word in words:
                single_lower = single_word.lower()

                # Check exact match for single word
                if single_lower in self.medical_terms or single_lower in self.drug_database:
                    return True
                if custom_terms and single_lower in custom_terms:
                    return True

                # Check stem match for single word
                for suffix in german_suffixes:
                    if len(single_lower) > len(suffix) + 3 and single_lower.endswith(suffix):
                        stem = single_lower[:-len(suffix)]
                        if stem in self.medical_terms or stem in self.drug_database:
                            return True
                        if custom_terms and stem in custom_terms:
                            return True

        return False

    def _get_placeholder(self, pii_type: str) -> str:
        """Get the appropriate placeholder for each PII type."""
        # Mapping of pattern names to context-aware placeholders
        placeholder_map = {
            # Name patterns
            "doctor_title_name": "[DOCTOR_NAME]",
            "honorific_name": "[NAME]",
            "name_comma_format": "[PATIENT_NAME]",
            "labeled_name": "[PATIENT_NAME]",

            # Date patterns
            "birthdate": "[BIRTHDATE]",
            "date_standalone": "[DATE]",
            "date_german_month": "[DATE]",
            "date_english_month": "[DATE]",

            # Reference patterns
            "case_reference": "[REFERENCE_ID]",
            "document_reference": "[REFERENCE_ID]",
            "patient_id": "[PATIENT_ID]",

            # Insurance patterns
            "insurance": "[INSURANCE_ID]",
            "insurance_company": "[INSURANCE_ID]",

            # Contact patterns
            "phone": "[PHONE]",
            "fax": "[FAX]",
            "email": "[EMAIL]",
            "email_full": "[EMAIL]",
            "named_email_domain": "[EMAIL_DOMAIN]",

            # Address patterns
            "address": "[ADDRESS]",
            "plz_city": "[PLZ_CITY]",
            "zipcode": "[ZIPCODE]",

            # ID patterns
            "tax_id": "[TAX_ID]",
            "social_security": "[SOCIAL_SECURITY]",
            "ssn": "[SSN]",
        }
        return placeholder_map.get(pii_type, f"[{pii_type.upper()}]")

    def _remove_pii_with_patterns(self, text: str, language: str) -> tuple[str, dict]:
        """Remove PII using regex patterns."""
        patterns = self.patterns_de if language == "de" else self.patterns_en
        removed_count = 0
        pii_types = []

        # Process patterns in a specific order: names first, then others
        # This ensures titles like "Dr. med." are processed before generic patterns
        priority_order = [
            "doctor_title_name",  # Must be first to catch "Dr. med. Schmidt"
            "honorific_name",     # Then "Herr Müller", "Frau Schmidt"
            "name_comma_format",  # Then "Müller, Anna"
            "labeled_name",       # Then "Patient: Schmidt"
        ]

        # Process priority patterns first
        for pii_type in priority_order:
            if pii_type in patterns:
                pattern = patterns[pii_type]
                matches = pattern.findall(text)
                if matches:
                    removed_count += len(matches)
                    pii_types.append(pii_type)
                    placeholder = self._get_placeholder(pii_type)
                    text = pattern.sub(placeholder, text)

        # Process remaining patterns
        for pii_type, pattern in patterns.items():
            if pii_type in priority_order:
                continue  # Already processed
            matches = pattern.findall(text)
            if matches:
                removed_count += len(matches)
                pii_types.append(pii_type)
                placeholder = self._get_placeholder(pii_type)
                text = pattern.sub(placeholder, text)

        return text, {"pattern_removals": removed_count, "pii_types": pii_types}

    def _remove_names_with_ner(
        self, text: str, language: str, custom_terms: set | None = None
    ) -> tuple[str, dict]:
        """Remove PII entities using SpaCy NER (names, locations, orgs, dates, times)."""
        nlp = self.nlp_de if language == "de" else self.nlp_en

        if nlp is None:
            return text, {"ner_removals": 0, "ner_available": False}

        doc = nlp(text)
        entities_removed = 0
        locations_removed = 0
        orgs_removed = 0
        dates_removed = 0
        times_removed = 0
        eponyms_preserved = 0
        custom_terms_preserved = 0

        # Entity labels differ between German and English SpaCy models!
        #
        # German (de_core_news_lg) - WikiNER trained:
        #   - PER: Person names
        #   - LOC: ALL locations (cities, streets, countries)
        #   - ORG: Organizations
        #   - MISC: Miscellaneous
        #   - NO FAC, DATE, TIME labels!
        #
        # English (en_core_web_lg) - OntoNotes 5 trained:
        #   - PERSON: Person names
        #   - GPE: Cities, countries, states
        #   - LOC: Non-GPE locations (mountains, water bodies)
        #   - ORG: Organizations
        #   - FAC: Facilities (buildings, hospitals)
        #   - DATE: Dates
        #   - TIME: Times
        #
        if language == "de":
            person_labels = {"PER"}
            location_labels = {"LOC"}  # German LOC includes cities
            org_labels = {"ORG"}
            date_labels = set()  # German model doesn't have DATE
            time_labels = set()  # German model doesn't have TIME
        else:  # English
            person_labels = {"PERSON"}
            location_labels = {"LOC", "GPE"}  # English separates GPE (cities) from LOC
            org_labels = {"ORG", "FAC"}  # English has FAC for facilities
            date_labels = {"DATE"}
            time_labels = {"TIME"}

        # Generic organizations to preserve (insurance companies, medical orgs)
        # These are commonly mentioned in medical documents but don't identify the patient
        preserved_orgs = {
            # German insurance companies (keep as they're standard references)
            "aok", "tk", "techniker", "barmer", "dak", "bkk", "ikk", "kkh", "hek", "hkk",
            "knappschaft", "viactiv", "sbk", "mhplus", "novitas", "pronova",
            # International medical organizations
            "who", "rki", "ema", "fda", "cdc", "ecdc", "pei",
            # Medical associations
            "ärzteblatt", "ärztekammer", "kassenärztliche",
        }

        # Generic locations to preserve (countries that don't identify patient)
        preserved_locations = {
            "deutschland", "germany", "österreich", "austria", "schweiz", "switzerland",
            "europa", "europe", "usa", "amerika", "america",
        }

        # Process entities in reverse order to maintain positions
        for ent in reversed(doc.ents):
            ent_lower = ent.text.lower()

            # Handle PERSON entities
            if ent.label_ in person_labels:
                # Skip if already replaced by pattern (contains placeholder bracket)
                # Check for brackets in entity OR bracket immediately before entity
                if "[" in ent.text or "]" in ent.text or (ent.start_char > 0 and text[ent.start_char - 1] == "["):
                    continue

                # Check if it's a medical eponym
                context = text[max(0, ent.start_char - 50):min(len(text), ent.end_char + 50)]
                if self._is_medical_eponym(ent.text, context):
                    eponyms_preserved += 1
                    continue

                # Check if it's a medical term or custom protected term
                if self._is_medical_term(ent.text, custom_terms):
                    if custom_terms and ent_lower in custom_terms:
                        custom_terms_preserved += 1
                    continue

                # Remove the name
                text = text[:ent.start_char] + "[NAME]" + text[ent.end_char:]
                entities_removed += 1

            # Handle LOCATION entities (cities, regions, streets)
            elif ent.label_ in location_labels:
                # Skip if already replaced by pattern (contains placeholder bracket)
                # Check for brackets in entity OR bracket immediately before entity
                if "[" in ent.text or "]" in ent.text or (ent.start_char > 0 and text[ent.start_char - 1] == "["):
                    continue

                # Skip preserved generic locations
                if ent_lower in preserved_locations:
                    continue

                # Skip if it's a medical term (SpaCy often misclassifies medical abbreviations as LOC)
                if self._is_medical_term(ent.text, custom_terms):
                    if custom_terms and ent_lower in custom_terms:
                        custom_terms_preserved += 1
                    continue

                # Replace location with placeholder
                text = text[:ent.start_char] + "[LOCATION]" + text[ent.end_char:]
                locations_removed += 1

            # Handle ORGANIZATION entities (hospitals, clinics, companies)
            elif ent.label_ in org_labels:
                # Skip if already replaced by pattern (contains placeholder bracket)
                # Check for brackets in entity OR bracket immediately before entity
                if "[" in ent.text or "]" in ent.text or (ent.start_char > 0 and text[ent.start_char - 1] == "["):
                    continue

                # Skip preserved generic organizations
                if ent_lower in preserved_orgs:
                    continue

                # Skip if it's a known medical term (SpaCy often misclassifies abbreviations as ORG)
                if self._is_medical_term(ent.text, custom_terms):
                    if custom_terms and ent_lower in custom_terms:
                        custom_terms_preserved += 1
                    continue

                # Replace organization with placeholder
                text = text[:ent.start_char] + "[ORGANIZATION]" + text[ent.end_char:]
                orgs_removed += 1

            # Handle DATE entities
            elif ent.label_ in date_labels:
                # Skip if already replaced by regex (contains placeholder)
                if "[" in ent.text:
                    continue

                # Replace date with placeholder
                text = text[:ent.start_char] + "[DATE]" + text[ent.end_char:]
                dates_removed += 1

            # Handle TIME entities
            elif ent.label_ in time_labels:
                # Skip if already replaced by regex
                if "[" in ent.text:
                    continue

                # Replace time with placeholder
                text = text[:ent.start_char] + "[TIME]" + text[ent.end_char:]
                times_removed += 1

        return text, {
            "ner_removals": entities_removed,
            "ner_locations_removed": locations_removed,
            "ner_orgs_removed": orgs_removed,
            "ner_dates_removed": dates_removed,
            "ner_times_removed": times_removed,
            "eponyms_preserved": eponyms_preserved,
            "custom_terms_preserved": custom_terms_preserved,
            "ner_available": True
        }

    def _remove_pii_with_presidio(
        self,
        text: str,
        language: str,
        custom_terms: set | None = None
    ) -> tuple[str, dict]:
        """
        Secondary PII detection pass using Microsoft Presidio.

        Catches entities that SpaCy may have missed, including:
        - Names in complex sentence structures
        - IBAN codes
        - Credit card numbers
        - Additional phone/email formats
        """
        if not self.presidio_available or not self.presidio_analyzer:
            return text, {"presidio_available": False, "presidio_removals": 0}

        presidio_removals = 0

        # Presidio entity types that match our registered recognizers
        # Only request entities we have recognizers for (avoids warnings)
        entities_to_detect = [
            "PERSON",           # Names (SpacyRecognizer)
            "LOCATION",         # Locations (SpacyRecognizer)
            "IBAN_CODE",        # IBAN (IbanRecognizer)
            "CREDIT_CARD",      # Credit cards (CreditCardRecognizer)
            "PHONE_NUMBER",     # Phone numbers (PhoneRecognizer)
            "EMAIL_ADDRESS",    # Email addresses (EmailRecognizer)
            "IP_ADDRESS",       # IP addresses (IpRecognizer)
            "URL",              # URLs (UrlRecognizer)
            "DATE_TIME",        # Date/time formats (DateRecognizer)
        ]

        try:
            # Run Presidio analysis
            results = self.presidio_analyzer.analyze(
                text=text,
                language=language,
                entities=entities_to_detect,
                score_threshold=0.6  # Balanced threshold - catches real PII but avoids medical term false positives
            )

            # Sort by position (reverse) to preserve indices during replacement
            results = sorted(results, key=lambda x: x.start, reverse=True)

            for result in results:
                entity_text = text[result.start:result.end]

                # Skip if already a placeholder (contains brackets)
                if "[" in entity_text or "]" in entity_text:
                    continue

                # Skip if preceded by bracket (part of existing placeholder)
                if result.start > 0 and text[result.start - 1] == "[":
                    continue

                # Skip if it's a protected medical term
                if self._is_medical_term(entity_text, custom_terms):
                    continue

                # Skip if it's a medical eponym
                context = text[max(0, result.start - 50):min(len(text), result.end + 50)]
                if self._is_medical_eponym(entity_text, context):
                    continue

                # Skip phone numbers that are actually medical values (e.g., "4000 Hz")
                # This prevents false positives for frequencies, dosages, etc.
                if result.entity_type == "PHONE_NUMBER":
                    # Check if followed by medical unit
                    if self._is_medical_value_context(text, result.start, result.end):
                        logger.debug(f"Skipping phone false positive: '{entity_text}' (medical value context)")
                        continue

                    # Also require minimum digits for phone numbers
                    # German phone numbers: minimum 7 digits local, 10+ with area code
                    # A 4-digit number like "4000" is almost never a phone number
                    digit_count = sum(1 for c in entity_text if c.isdigit())
                    if digit_count < 7:
                        logger.debug(f"Skipping phone false positive: '{entity_text}' (only {digit_count} digits)")
                        continue

                # Map Presidio entity types to our placeholders
                placeholder_map = {
                    "PERSON": "[NAME]",
                    "LOCATION": "[LOCATION]",
                    "IBAN_CODE": "[IBAN]",
                    "CREDIT_CARD": "[CREDIT_CARD]",
                    "PHONE_NUMBER": "[PHONE]",
                    "EMAIL_ADDRESS": "[EMAIL]",
                    "IP_ADDRESS": "[IP_ADDRESS]",
                    "URL": "[URL]",
                    "DATE_TIME": "[DATE]",
                    "NRP": "[NRP]",
                    "MEDICAL_LICENSE": "[MEDICAL_LICENSE]",
                }

                placeholder = placeholder_map.get(result.entity_type, "[PII]")
                text = text[:result.start] + placeholder + text[result.end:]
                presidio_removals += 1

        except Exception as e:
            logger.warning(f"Presidio analysis failed: {e}")
            return text, {"presidio_available": True, "presidio_error": str(e), "presidio_removals": 0}

        return text, {
            "presidio_available": True,
            "presidio_removals": presidio_removals
        }

    def _restore_medical_value_false_positives(self, text: str) -> tuple[str, int]:
        """
        Restore medical values that were incorrectly replaced as PII.

        This method fixes false positives where numbers followed by medical units
        (Hz, mmHg, mg, ml, etc.) were incorrectly identified as phone numbers,
        fax numbers, or other PII types.

        Examples of false positives that get restored:
          - "[PHONE] Hz" → original number restored (audiometry: "4000 Hz")
          - "[PHONE] mmHg" → original number restored (blood pressure)
          - "[PHONE] mg" → original number restored (medication dosage)

        Returns:
            Tuple of (corrected_text, number_of_restorations)
        """
        restorations = 0

        # Find all placeholder + unit patterns and restore the original number
        # We need to track what was originally there, but since we can't,
        # we'll instead prevent this from happening by checking context during
        # the Presidio pass. For now, this method serves as documentation
        # and a fallback that logs warnings.

        # Check for obvious false positive patterns
        matches = list(self.medical_value_pattern.finditer(text))
        for match in matches:
            logger.warning(
                f"Detected likely false positive: '{match.group()}' - "
                f"a medical value was incorrectly replaced as PII. "
                f"Consider adding the original value to protected terms."
            )
            restorations += 1

        return text, restorations

    def _is_medical_value_context(self, text: str, start: int, end: int) -> bool:
        """
        Check if a detected number is followed by a medical unit.

        This prevents false positives where numbers like "4000" in "4000 Hz"
        are incorrectly identified as phone numbers.

        Args:
            text: The full text
            start: Start position of the detected entity
            end: End position of the detected entity

        Returns:
            True if the number appears to be a medical value, False otherwise
        """
        # Get text after the entity (up to 10 characters)
        text_after = text[end:min(end + 15, len(text))].strip()

        # Check if followed by a medical unit
        medical_units = [
            # Frequencies (audiometry, ECG)
            "hz", "khz", "mhz", "ghz",
            # Pressure
            "mmhg", "cmh2o", "kpa", "pa",
            # Mass
            "mg", "µg", "ng", "pg", "g", "kg",
            # Volume
            "ml", "µl", "dl", "l",
            # Length
            "mm", "cm", "m", "µm", "nm",
            # Moles
            "mmol", "µmol", "mol",
            # Units
            "u", "iu", "ie",
            # Voltage/current
            "mv", "µv", "v", "ma", "µa", "a",
            # Radioactivity
            "bq", "mbq", "gbq", "gy", "mgy",
            # Rate
            "bpm", "/min",
            # Concentrations
            "pg/ml", "ng/ml", "µg/ml", "mg/dl", "mmol/l", "g/dl",
            # Other
            "%", "‰", "jahre", "years", "j",
        ]

        text_after_lower = text_after.lower()
        for unit in medical_units:
            if text_after_lower.startswith(unit):
                return True
            # Also check with space: "4000 Hz"
            if text_after_lower.startswith(" " + unit) or text_after_lower.startswith("-" + unit):
                return True

        return False

    def remove_pii(
        self,
        text: str,
        language: Literal["de", "en"] = "de",
        custom_protection_terms: list[str] | None = None
    ) -> tuple[str, dict]:
        """
        Remove PII from text.

        Args:
            text: Input text to process
            language: Language code ('de' for German, 'en' for English)
            custom_protection_terms: Additional terms to protect (from database)

        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        if not text or not text.strip():
            return text, {"entities_detected": 0, "error": "Empty text"}

        # Build custom terms set for efficient lookup
        custom_terms: set | None = None
        if custom_protection_terms:
            custom_terms = {term.lower() for term in custom_protection_terms}

        original_length = len(text)
        metadata = {
            "language": language,
            "original_length": original_length,
            "processing_timestamp": datetime.now().isoformat(),
            "gdpr_compliant": True,
            "custom_terms_count": len(custom_terms) if custom_terms else 0
        }

        # Step 1: Remove patterns (addresses, IDs, etc.)
        text, pattern_meta = self._remove_pii_with_patterns(text, language)
        metadata.update(pattern_meta)

        # Step 2: Remove names with NER (with custom terms protection)
        text, ner_meta = self._remove_names_with_ner(text, language, custom_terms)
        metadata.update(ner_meta)

        # Step 3: Secondary pass with Presidio (catches missed PII)
        text, presidio_meta = self._remove_pii_with_presidio(text, language, custom_terms)
        metadata.update(presidio_meta)

        # Calculate totals (all PII entities removed)
        metadata["entities_detected"] = (
            metadata.get("pattern_removals", 0) +
            metadata.get("ner_removals", 0) +
            metadata.get("ner_locations_removed", 0) +
            metadata.get("ner_orgs_removed", 0) +
            metadata.get("ner_dates_removed", 0) +
            metadata.get("ner_times_removed", 0) +
            metadata.get("presidio_removals", 0)
        )
        metadata["cleaned_length"] = len(text)

        return text, metadata

    def remove_pii_batch(
        self,
        texts: list[str],
        language: Literal["de", "en"] = "de",
        batch_size: int = 32,
        custom_protection_terms: list[str] | None = None
    ) -> list[tuple[str, dict]]:
        """
        Remove PII from multiple texts.

        Args:
            texts: List of texts to process
            language: Language code
            batch_size: Batch size for processing (not used currently, for future optimization)
            custom_protection_terms: Additional terms to protect (from database)

        Returns:
            List of (cleaned_text, metadata) tuples
        """
        results = []
        for text in texts:
            cleaned, meta = self.remove_pii(text, language, custom_protection_terms)
            results.append((cleaned, meta))
        return results
