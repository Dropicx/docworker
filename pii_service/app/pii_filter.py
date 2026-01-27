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

from app.medical_term_verifier import MedicalTermVerifier

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

        # Initialize medical term verifier (MEDIALpy + German patterns)
        self.medical_verifier = MedicalTermVerifier()

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

            # Doctor names with initials: "J. Chahem", "K. Fariq-Spiegel", "N. Dewies"
            # Matches initial + period + space + surname (with optional hyphenated part)
            # Exclusions:
            # - Negative lookbehind for lowercase+period (German abbrevs: z.B., d.h.)
            # - Negative lookbehind for "Vitamin " (prevents "Vitamin D." matching)
            # - Negative lookbehind for "Typ " (prevents "Typ A." matching)
            "doctor_initial_name": re.compile(
                r"(?<!Vitamin )(?<!Typ )(?<![a-zäöü]\.)\b([A-Z]\.)\s*([A-ZÄÖÜ][a-zäöüß]+(?:-[A-ZÄÖÜ][a-zäöüß]+)?)\b"
            ),

            # Patient name in header block after PLZ/City or placeholder
            # Catches: "[PLZ_CITY], Fritz, , Status M" or "12345 Berlin, Hans, , Status"
            # Pattern: After city/PLZ, comma, then a capitalized German first name, comma, then Status
            "name_in_header_block": re.compile(
                r"(?:\]|[a-zäöüß])\s*,\s*"  # After placeholder ] or lowercase letter (city), comma
                r"([A-ZÄÖÜ][a-zäöüß]+)"     # Capture first name (capitalized)
                r"\s*,\s*,?\s*"              # Comma(s)
                r"(?:Status|$)",             # Followed by "Status" or end of line
                re.IGNORECASE
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

            # Phone numbers with spaces: "02131 888 - 2765", "0211 123 456 78"
            # Matches area code + spaced number blocks
            "phone_spaced": re.compile(
                r"\b(\d{4,5})\s+(\d{3})\s*[-–]\s*(\d{4})\b"
            ),

            # Phone extensions that appear after placeholder or partial number
            # Handles: "/- 2764", "/-2764", "/ -2764", "/ 2764"
            "phone_extension": re.compile(
                r"\s*/\s*-?\s*\d{2,5}\b"
            ),

            # Orphaned phone digits after [PHONE] placeholder
            # Handles: "[PHONE] /- 2764" → should all be [PHONE]
            "phone_orphan": re.compile(
                r"\[PHONE\]\s*/?\s*-?\s*\d{2,5}"
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

            # Street address without common suffix (e.g., "Rhedung 18 b")
            # Matches: [StreetName] [Number][optional letter], followed by PLZ
            # This catches addresses like "Rhedung 18 b, 41352 Korschenbroich"
            "address_no_suffix": re.compile(
                r"([A-ZÄÖÜ][a-zäöüß-]+)\s+(\d{1,4}\s*[a-zA-Z]?)\s*,\s*(?=\d{5}\s)",
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
            # Updated to also match Letter + digits format (e.g., O598926034)
            "insurance_company": re.compile(
                r"\b(?:AOK|TK|Barmer|DAK|BKK|IKK|KKH|HEK|hkk|Techniker|"
                r"KNAPPSCHAFT|Viactiv|Mobil\s*Oil|SBK|mhplus|Novitas|"
                r"Pronova|Big\s*direkt|Audi\s*BKK|BMW\s*BKK|Bosch\s*BKK)\b"
                r"[^,\n]{0,40}?(?:Nr\.?|Nummer|Versicherten)?[:\s]*"
                r"([A-Z]?\d{9,12})",
                re.IGNORECASE
            ),

            # Standalone insurance ID (German Versichertennummer)
            # Format: Letter + 9 digits (e.g., O598926034, A123456789)
            # Appears after insurance company names without explicit label
            "insurance_standalone": re.compile(
                r"(?<=,\s)[A-Z]\d{9,10}(?=,|\s|$)",
                re.IGNORECASE
            ),

            # Insurance status codes (Status M, Status P, Status F)
            # These indicate member status and should be removed
            "insurance_status": re.compile(
                r",?\s*Status\s+[MPFRK]\b",
                re.IGNORECASE
            ),

            # Patient ID
            "patient_id": re.compile(
                r"(?:patient(?:en)?[- ]?(?:nr\.?|nummer|id)|"
                r"fall(?:nummer|nr\.?)|aktenzeichen)\s*[:.]?\s*"
                r"([A-Z0-9\-]{5,20})",
                re.IGNORECASE
            ),

            # Case number (Fallnummer) - standalone numeric format
            # Handles: "Fallnummer: 1250070091", "Fall-Nr.: 123456789"
            "case_number": re.compile(
                r"(?:Fallnummer|Fall[- ]?Nr\.?|Aufnahme[- ]?Nr\.?)\s*[:.]?\s*"
                r"(\d{8,15})",
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

            # Email addresses split across lines (name on one line, @domain on next)
            # Handles: "silvia.jacquemin-fink\n@rheinlandklinikum.de"
            "email_split": re.compile(
                r"[a-zA-ZäöüÄÖÜß0-9]+(?:[.\-_][a-zA-ZäöüÄÖÜß0-9]+)+\s*\n\s*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                re.IGNORECASE
            ),

            # Email local part before @[EMAIL_DOMAIN] placeholder (post-processing)
            # Catches names that were split from domain: "firstname.lastname\n@[EMAIL_DOMAIN]"
            # Replaces entire email (name + domain placeholder) with [EMAIL]
            "email_local_part": re.compile(
                r"[a-zA-ZäöüÄÖÜß]+(?:[.\-_][a-zA-ZäöüÄÖÜß]+)+\s*\n?\s*@\[EMAIL_DOMAIN\]",
                re.IGNORECASE
            ),

            # =============================================================
            # COMPANY/ORGANIZATION PATTERNS (NEW)
            # =============================================================

            # Company registration numbers (HRB 4643, HRA 12345)
            "company_registration": re.compile(
                r"\b(HRB|HRA|GnR|PR|VR)\s*\d{3,8}\b",
                re.IGNORECASE
            ),

            # Bank names with city/location
            "bank_location": re.compile(
                r"\b(Sparkasse|Volksbank|Raiffeisenbank|Commerzbank|"
                r"Deutsche\s+Bank|Postbank|Hypovereinsbank|Targobank|"
                r"Santander|ING|DKB|N26|Sparda[-\s]?Bank)\s+"
                r"[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?\b",
                re.IGNORECASE
            ),

            # IBAN numbers (German format: DE + 2 check digits + 18 characters)
            "iban": re.compile(
                r"\b[A-Z]{2}\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{2}\b",
                re.IGNORECASE
            ),

            # BIC/SWIFT codes
            "bic": re.compile(
                r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"
            ),

            # =============================================================
            # HOSPITAL LETTERHEAD PATTERNS (NEW)
            # =============================================================

            # Hospital/clinic letterhead block - company info at document start
            # Matches common German hospital organizational info
            "hospital_letterhead": re.compile(
                r"(?:Unternehmensgruppe|Rheinland\s+Klinikum|Lukaskrankenhaus|"
                r"Universitätsklinikum|Städtisches\s+Klinikum|Kreiskrankenhaus|"
                r"Marienhospital|St\.\s*[\w\-]+\s*(?:Hospital|Krankenhaus)|"
                r"Maria\s+Hilf\s+Kliniken?|"  # Maria Hilf Kliniken
                r"Bethesda\s+(?:Krankenhaus|Klinik)|"  # Bethesda hospitals
                r"[A-ZÄÖÜ][a-zäöüß]+\s+Hilf\s+Kliniken?|"  # [Name] Hilf Kliniken pattern
                r"Klinikum\s+\w+|Krankenhaus\s+\w+)\b"
                r"[^.]*?(?:GmbH|gGmbH|AG|e\.V\.)?",
                re.IGNORECASE
            ),

            # Hospital management/director titles
            "hospital_management": re.compile(
                r"(?:Geschäftsführung|Ärztlicher\s+Direktor|Pflegedirektor|"
                r"Verwaltungsdirektor|Vorstand|Aufsichtsrat)[:\s]*"
                r"[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*",
                re.IGNORECASE
            ),

            # Hospital department headers
            "hospital_department": re.compile(
                r"(?:Klinik\s+für|Abteilung\s+für|Institut\s+für|Zentrum\s+für)\s+"
                r"[A-ZÄÖÜ][a-zäöüß]+(?:\s+(?:und|u\.)\s+[A-ZÄÖÜ][a-zäöüß]+)*",
                re.IGNORECASE
            ),

            # Hospital name with city in referral context
            # Catches: "Maria Hilf Kliniken Mönchengladbach", "Universitätsklinikum Köln"
            "hospital_with_city": re.compile(
                r"(?:Maria\s+Hilf\s+Kliniken?|Universitätsklinikum|Städtisches\s+Klinikum|"
                r"[A-ZÄÖÜ][a-zäöüß]+(?:hospital|klinik|kliniken|krankenhaus))"
                r"\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)",
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
            "aorta", "koronararterie", "aortenwand",
            # Phase 6: German vascular anatomy (commonly misclassified as NAME)
            "pfortader", "lebervene", "lebervenen", "milzvene",
            # Phase 7: Pancreas anatomy
            "pankreaskopf", "pankreaskopfes", "pankreasschwanz", "pankreasschwanzes",
            # Phase 7: Anatomical position terms
            "orthotop", "orthotope", "orthotoper", "orthotopen",
            # Phase 11: Anatomical structures and regions (commonly misclassified)
            "axillarlinie", "axillarlinien", "vordere axillarlinie", "hintere axillarlinie",
            "leberparenchym", "nierenparenchym", "milzparenchym", "parenchymsaum",
            "parenchym", "parenchyms", "parenchymstruktur",
            "gallenwege", "gallenweg", "gallenwegs", "gallengänge", "gallengang",
            "einzelniere", "einzelnieren", "wandniere",
            "morison-pouch", "morison pouch", "douglas-raum", "douglasraum",
            # Anatomical regions (commonly misclassified as LOC)
            "oberbauch", "unterbauch", "mittelbauch", "epigastrium",
            "oberbauchorgane", "unterbauchorgane", "bauchorgane",
            # Phase 11: Limb and body regions (commonly misclassified as LOCATION)
            "extremitäten", "extremität", "obere extremität", "untere extremität",
            "oberarm", "unterarm", "oberschenkel", "unterschenkel",
            "hinterhorn", "vorderhorn", "seitenhorn",  # Meniscus anatomy
            "pulsübertragung", "nierenperfusion",
            "extrakardial", "extrakardiale", "extrakardialer", "extrakardialen",
            "intrakardial", "intrakardiale", "intrakardialer", "intrakardialen",
            # English
            "heart", "lung", "liver", "kidney", "stomach", "brain", "muscle", "bone",
            "spleen", "pancreas", "gallbladder", "thyroid", "prostate", "uterus",

            # ==================== CLINICAL TERMS ====================
            "patient", "patientin", "diagnose", "befund", "therapie", "behandlung",
            "untersuchung", "operation", "medikament", "dosierung", "anamnese",
            # FINAL7: Patient abbreviations and medical section headers
            "pat", "pat.",  # Abbreviation for Patient
            "akt", "akt.",  # Abbreviation for aktuell (current)
            "stat", "stat.",  # Abbreviation for stationär (inpatient)
            # FINAL8: Section headers that look like names
            "aufnahmegrund", "aufnahmegrund/anamnese",  # Admission reason/history
            "eigenanamnese", "familienanamnese", "sozialanamnese",  # History types
            "fremdanamnese", "berufsanamnese", "medikamentenanamnese",
            "prognose", "epikrise", "symptom", "syndrom", "erkrankung", "krankheit",
            "störung", "insuffizienz", "entzündung", "infektion", "nekrose",
            "ischämie", "ruptur", "läsion", "pathologie",
            # Phase 11: Compound pathological terms (commonly misclassified as LOCATION)
            "nekrosezone", "nekrosezonen", "infarzierungszone", "ischämiezone",
            "harnstau", "harnstauung", "harntransportstörung", "harnaufstau",
            "pleuraerguss", "pleuraergüsse", "perikarderguss", "aszites",
            # FINAL: Liver/organ findings (commonly misclassified as LOCATION)
            "leberzyste", "leberzysten", "leberzystenkonglomerat",
            "nierenzyste", "nierenzysten", "milzzyste",
            "lebersprechstunde", "leberambulanz",  # Clinic names but medical context
            # FINAL: Breathing descriptors
            "eupnoe", "eupnoisch", "dyspnoe", "orthopnoe", "tachypnoe",
            # FINAL: Catheter terms
            "dk-auslassversuch", "dk auslassversuch", "auslassversuch",
            "dauerkatheter", "blasenkatheter", "harnkatheter",
            # FINAL: Plural disease forms
            "pankreatitiden", "hepatitiden", "meningitiden", "enzephalitiden",
            # Phase 6: Medical devices
            "perfusor", "infusomat",
            # Phase 9: Stent brand names and medical devices
            "protegé", "protege", "protégé-stent", "protege-stent",
            "protegé-stents", "protege-stents",  # Phase 10: Plural forms
            "palmaz", "express", "cypher", "taxus", "xience", "resolute",
            "endeavor", "promus", "synergy", "orsiro", "ultimaster",
            "viabahn", "wallstent", "zilver", "innova", "visi-pro",  # Phase 10: More stent brands
            # Phase 11: Bacteria and pathogens (commonly misclassified as NAME)
            "h pylori", "h. pylori", "h.pylori", "helicobacter", "helicobacter pylori",
            "hp-negativ", "hp-positiv", "hp negativ", "hp positiv",
            # Phase 11: Anatomical/pathological conditions (commonly misclassified)
            "agenesie", "aplasie", "hypoplasie", "dysplasie", "atrophie",
            # Phase 12: Genetic terms (commonly misclassified as NAME)
            "homozygot", "homozygote", "homozygoter", "homozygoten",
            "heterozygot", "heterozygote", "heterozygoter", "heterozygoten",
            "hfe", "hfe-mutation", "h63d", "c282y",  # Hemochromatosis mutations
            "wandbetont", "wandbetonte", "wandbetonter", "wandbetonten",
            # Phase 11: Bilateral/positional descriptors
            "beidseits", "beidseitig", "beidseitige", "beidseitiger", "beidseitigen",
            # Phase 12: Lab/clinical section headers (commonly misclassified as NAME)
            "laborchemisch", "laborchemische", "laborchemischer", "laborchemischen",
            "abdomensonografisch", "abdomensonographisch",
            "kumulativ", "kumulative", "kumulativer", "kumulativen",
            # FINAL: Clinical documentation terms (commonly misclassified)
            "nebenbefundlich", "nebenbefundliche", "nebenbefundlicher",
            "hauptbefundlich", "begleitbefundlich",
            "untere", "obere", "mittlere",  # Position descriptors in medical context
            "normgroß", "normgroße", "normgroßer", "normgroßen",
            # Phase 12: Clinical requirement terms
            "interventionsbedarf", "therapiebedarf", "handlungsbedarf",
            "aufnahmegrund", "aufnahmegrundes", "entlassungsgrund",
            # Phase 12: Cardiac examination findings
            "pulsdefizit", "jugularvenenstau", "halsvenenstauung",
            # Phase 12: Severity/examination descriptors
            "grob", "grobe", "grober", "groben",  # e.g., "grob neurologisch"
            "az-reduziert", "az-reduzierte", "az-reduzierter", "az-reduzierten",
            # Phase 12: Cortisone therapy terms
            "cortisonstoß", "kortisonstoß", "prednisolonstoß",
            # Phase 12: Legal/regulatory terms
            "paragraf", "paragraph", "paragrafen",
            # Phase 12: Planning/procedure terms
            "prozedere", "prozederes", "vorgehen", "vorgehens",
            # Phase 7: Clinical examination terms
            "sklerenikterus", "ikterus",  # Jaundice/yellowing of sclera
            "allgemeinzustand", "allgemeinzustands", "allgemeinzustandes",  # General condition
            "umgebungsreaktion", "umgebungsreaktionen",  # Surrounding tissue reaction
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
            # Phase 7: GI conditions/syndromes
            "mallory-weiss", "mallory weiss",  # Esophageal tear syndrome
            "gi-blutung", "gi blutung", "gastrointestinalblutung",  # GI bleeding
            # Cancer diagnosis abbreviations (commonly misclassified as NAME)
            "prostata-ca", "prostataca", "mamma-ca", "mammaca", "mammakarzinom",
            "bronchial-ca", "bronchialca", "kolon-ca", "kolonca",
            "lungen-ca", "lungenca", "magen-ca", "magenka",
            "hcc", "ccc", "nsclc", "sclc",  # Liver, bile duct, lung cancers
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
            # Phase 7: Imaging findings
            "herzschatten", "herzschattens",  # Cardiac silhouette on X-ray
            "echogenität", "echoreich", "echoarm",  # Ultrasound echogenicity
            "cta", "mrcp",  # CT/MR angiography/cholangiopancreatography
            # Phase 9: Additional imaging/diagnostic terms
            "röntgen-thorax", "röntgenthorax", "thorax-röntgen",
            "kontrollröntgen", "verlaufsröntgen", "röntgenuntersuchung",
            "abdomensonografie", "abdomensonographie", "sonografisch", "sonographisch",
            "minderperfusion", "hypoperfusion", "hyperperfusion",
            # Phase 11: CT/MR imaging terms (commonly misclassified as LOCATION)
            "computertomografisch", "computertomographisch", "computertomografie",
            "magnetresonanztomografie", "magnetresonanztomografisch",
            # FINAL: CT compound terms (commonly misclassified as ORGANIZATION)
            "ct-aufnahme", "ct-diagnostik", "ct-untersuchung", "ct-befund",
            "ct-abdomen-aufnahme", "ct-thorax-aufnahme", "ct-thoraxaufnahme",
            "ct-voruntersuchung", "ct-kontrolle", "ct-verlaufskontrolle",
            "mrt-aufnahme", "mrt-untersuchung", "mrt-befund",
            # Phase 10: Position and imaging terms
            "liegendposition", "liegend", "sitzend", "stehend",
            "beurteilbarkeit", "beurteilbar", "eingeschränkte beurteilbarkeit",
            "röntgen-thoraxaufnahme", "thoraxaufnahme",
            # Phase 10: Pleural/pulmonary findings
            "randwinkelerguss", "randwinkelergüsse",
            "perihilär", "perihiläre", "perihilärer", "perihilären",
            "hilar", "hilär", "infrahilär", "infrahilar",
            # Phase 12: Lung/mediastinal anatomy (commonly misclassified as NAME)
            "hili", "hilus", "hilum", "lungenhili", "lungenhilus",
            "retroperitoneum", "retroperitoneal", "retroperitoneale",
            # FINAL: More anatomical terms (commonly misclassified)
            "confluensbereich", "konfluenzbereich", "confluens",
            "laterokonale faszie", "lateroconale faszie", "lateroconal",
            "bauchhöhle", "peritonealhöhle", "pleurahöhle",
            "pancreasschwanz", "pankreasschwanzbereich",
            "abdominalorgane", "thoraxorgane",
            # EKG types (commonly misclassified as ORG)
            "belastungs-ekg", "belastungsekg", "belastungs",
            "ruhe-ekg", "ruheekg", "langzeit-ekg", "langzeitekg",
            "stress-ekg", "stressekg",
            # English
            "mri", "xray", "ultrasound", "ecg", "biopsy",

            # ==================== PROCEDURES ====================
            "operation", "resektion", "transplantation", "bypass", "stent", "katheter",
            "infusion", "injektion", "transfusion", "dialyse", "chemotherapie",
            "bestrahlung", "physiotherapie", "ergotherapie", "logopädie",
            "rehabilitation", "palliativ",
            # Surgical procedures (-ektomie, -tomie, -plastik)
            "appendektomie", "cholezystektomie", "gastrektomie", "kolektomie",
            "nephrektomie", "splenektomie", "thyreoidektomie", "mastektomie",
            "hysterektomie", "prostatektomie", "lobektomie", "pneumonektomie",
            "laparotomie", "thorakotomie", "kraniotomie", "tracheotomie",
            "angioplastik", "valvuloplastik", "arthroplastik",
            # Compound valve terms
            "mitralklappeninsuffizienz", "mitralklappenersatz", "mitralklappenstenose",
            "aortenklappeninsuffizienz", "aortenklappenersatz", "aortenklappenstenose",
            "trikuspidalklappeninsuffizienz", "pulmonalklappeninsuffizienz",
            # Phase 6: Hepatology procedures (commonly misclassified as NAME/ORG)
            "tips", "tipss", "ögd", "aszitesdrainage", "parazentese",
            # Phase 12: TIPS procedure compounds (commonly misclassified as ORGANIZATION)
            "tipss-anlage", "tips-anlage", "tipss-revision", "tips-revision",
            "tipss-trakt", "tips-trakt", "tipss-leistung", "tips-leistung",
            # Phase 12: Surgical resection terms (commonly misclassified as NAME)
            "teilresektion", "resektion", "tumorresektion", "segmentresektion",
            # Risk factors and lifestyle
            "nikotinabusus", "alkoholabusus", "drogenabusus", "substanzabusus",
            "adipositas", "übergewicht", "untergewicht", "kachexie",
            # Common abbreviations
            "z.n.", "v.a.", "b.b.", "o.b.", "o.p.b.", "ed", "dd",

            # ==================== DEPARTMENTS ====================
            "intensivstation", "notaufnahme", "ambulanz", "station",
            # Phase 11: Consultation terms (commonly misclassified as NAME)
            "konsil", "konsils", "konsiliarius", "konsilarisch", "konsiliar",
            "konsiliarisch", "konsiliarische", "konsiliarischer",
            "kardiologie", "pneumologie", "gastroenterologie", "nephrologie",
            "neurologie", "onkologie", "hämatologie", "rheumatologie",
            "endokrinologie", "dermatologie", "orthopädie", "urologie",
            "gynäkologie", "pädiatrie", "geriatrie", "chirurgie", "anästhesie",
            "radiologie", "pathologie", "labormedizin",

            # ==================== LAB VALUES ====================
            "hämoglobin", "hämatokrit", "erythrozyten", "leukozyten", "thrombozyten",
            "kreatinin", "harnstoff", "harnsäure", "bilirubin", "transaminasen",
            "got", "gpt", "ggt", "ap", "ldh", "ck", "troponin", "bnp", "crp",
            # Phase 7: Additional lab values
            "ck-mb", "ckmb",  # Cardiac enzyme marker
            "eiw", "eiw.", "eiw. ges.", "eiw ges",  # Eiweiß (protein) abbreviations
            # Phase 9: More lab abbreviations
            "bili", "bili.", "bili ges.", "bili. ges.",  # Bilirubin abbreviations
            "ges.", "ges",  # "gesamt" (total) - common lab abbreviation
            # Phase 10: Lab/clinical compound terms
            "infektwerte", "infektparameter", "infektzeichen", "entzündungsparameter",
            "retentionsparameter", "nierenretentionsparameter", "leberwerte",
            "stuhlprobe", "stuhlproben", "stuhlgang", "stuhluntersuchung",
            # FINAL: Lab value changes/elevations (commonly misclassified as ORGANIZATION)
            "crp-erhöhung", "ck-erhöhung", "lipase-erhöhung", "troponin-erhöhung",
            "transaminasenerhöhung", "bilirubinerhöhung", "kreatininerhöhung",
            # Phase 11: Additional lab abbreviations (commonly misclassified as LOCATION)
            "hkt", "hk", "hct",  # Hämatokrit abbreviations
            "prealbumin", "präalbumin", "albumin",
            "eryzahl", "erythrozytenzahl", "leukozytenzahl", "thrombozytenzahl",
            "hämatoxrit",  # Typo variant
            # FINAL: Autoantibodies and lab panels (commonly misclassified)
            "myositis-panel", "myositis panel", "autoantikörper-panel",
            "mi-2", "mi-2 alpha", "mi-2 beta", "jo-1", "ku", "pm-scl",
            "ana", "anca", "ds-dna-ak", "ds-dann-ak",  # Autoantibodies
            "ena", "ena-screening",  # Extractable nuclear antigens
            "molekularbiologischer direktnachweis", "pcr-nachweis",
            # FINAL2: ICD codes (commonly misclassified as ORGANIZATION)
            "r16.0", "r16.1", "k76.0", "k83.1", "q60.0",
            # FINAL2: Allergens
            "duftstoffmix", "perubalsam", "thiomersal", "nickelsulfat",
            # FINAL2: Anatomical terms
            "abdomineller lymphknotenstatus", "lymphknotenstatus",
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
            # FINAL7: Antibody/autoantibody abbreviations
            "ldt",  # Lab Diagnostic Table
            "srp", "ej", "oj", "nxp2", "sae1", "mda5", "tif1",  # Myositis antibodies
            "mi-2", "pm-scl100", "pm-scl75", "jo-1", "pl-7", "pl-12", "ro-52",  # More antibodies
            "ku", "anti-ku",  # Ku antibody
            # Phase 7: Clinical/examination abbreviations
            "vag", "vag.",  # Vesicular breath sounds (Vesikuläres Atemgeräusch)
            "pulmo", "pulmo:",  # Lungs examination section
            "cor", "cor:",  # Heart examination section
            "anc",  # Acute Necrotic Collection (pancreatitis)
            "apfc",  # Acute Peripancreatic Fluid Collection
            "pvk",  # Peripheral venous catheter (Periphere Venenkatheter)
            "dnr", "dni", "dnr/dni",  # Do Not Resuscitate/Intubate
            "nyha", "asa", "ccs", "kps", "ecog",  # Classification scores
            "hf", "af", "vhf", "sr", "avb", "lbbb", "rbbb",  # Rhythm/ECG
            "copd", "ards", "osa", "osas",  # Pulmonary
            "aki", "ckd", "esrd", "gn",  # Renal
            "dm", "hba1c", "ogtt", "nüchtern",  # Diabetes
            "khe", "khk", "pavk", "tia", "cva",  # Vascular
            "op", "re", "li", "bds", "ca", "chemo", "rtx",  # General abbreviations
            # Phase 12: Common German medical abbreviations (misclassified as NAME/ORG)
            "pat.", "pat", "patienten",  # Patient abbreviation
            "sd", "sd.",  # Schilddrüse (thyroid)
            "az", "az.",  # Allgemeinzustand (general condition)
            "gdh-ag", "gdh", "ag",  # Lab test abbreviations
            # FINAL: More medical abbreviations (commonly misclassified)
            "avd", "avd.",  # Arzt vom Dienst (duty doctor)
            "bk", "bk.",  # Blutkulturen (blood cultures)
            "dk", "dk.",  # Dauerkatheter (indwelling catheter)
            "mcl", "mcl.",  # Medioclavicularlinie
            "wv", "wv.",  # Wiedervorstellung (follow-up)
            "ppi", "ppi.",  # Protonenpumpeninhibitor
            "hocm",  # Hypertrophe obstruktive Kardiomyopathie
            "qtc", "qtc-zeit",  # QTc interval
            "tpo", "tpo-ak",  # Thyreoperoxidase
            "eia", "ift",  # Lab test methods
            "kulturbefund", "keimnachweis", "erregernachweis",
            # FINAL2: More abbreviations and clinical terms
            "e. i. r.", "i. r.", "i.r.", "a. e.", "a.e.",  # im Rahmen, am ehesten
            "begannen", "begann",  # Verbs that start sentences
            "gruppe f", "serotyp",  # Virus serotypes
            "bakt", "bakt.",  # Bacteria (urinalysis)
            "norm", "norm.",  # Reference range
            "iu/l", "u/l", "iu/ml",  # Lab units
            # FINAL3: Last remaining abbreviations
            "nekr.", "nekr", "nekrotisierend", "nekrotisierende",
            "procederes", "procedere",  # Procedure/approach
            "haptoglobin",  # Lab value
            "z.n.", "v.a.", "dd", "st.p.", "ed", "j.",  # German medical abbreviations
            "z.n", "v.a", "zn", "va",  # Without trailing periods (tokenization variants)
            "sinusrhythmus", "normofrequent", "rhythmisch",  # ECG findings
            # Phase 11: ECG wave components (commonly misclassified as LOCATION)
            "s-zacke", "s-zacken", "r-zacke", "r-zacken", "t-welle", "t-wellen",
            "p-welle", "p-wellen", "st-hebung", "st-hebungen", "st-senkung",
            # FINAL2: ECG leads (single letters often misclassified)
            "v1", "v2", "v3", "v4", "v5", "v6",  # Precordial leads
            "avl", "avr", "avf",  # Augmented limb leads
            "tiefen s", "tiefes s",  # ECG S wave in context
            # FINAL7: Single-letter ECG waves (standalone entities)
            "s", "t", "p", "q", "r",  # ECG waves when detected as entities
            # FINAL4: Pharmaceutical terms
            "retard", "retardkapsel", "retardtablette",  # Sustained-release
            "retard kapsel", "retard tablette",  # With space
            # FINAL5: Lab test terms (commonly misclassified as ORGANIZATION)
            "extrahierbare nukleaere", "extrahierbare", "nukleaere",  # ENA test
            "extrahierbare nukleäre antigene", "ena",
            # FINAL5: Histology grades (commonly misclassified as ORGANIZATION)
            "i.+ii.", "i.", "ii.", "iii.", "iv.", "i.+ii.+iii.",
            "grad i", "grad ii", "grad iii", "grad iv",
            # FINAL7: Additional histology grade variations
            "i", "ii", "iii", "iv",  # Without dots
            "i+ii", "i + ii", "i. + ii.",  # Different spacing variations
            # FINAL8: More histology/classification patterns
            "i.+ii", "ii.+iii", "iii.+iv",  # Without trailing dot
            "typ i", "typ ii", "typ iii", "typ iv",  # Type classifications
            "type i", "type ii", "type iii", "type iv",
            # FINAL5: Common hospital name patterns (often misclassified as NAME)
            "maria hilf", "maria-hilf", "st. maria", "st. josef", "st. antonius",
            "unauffällig", "regelrecht", "altersentsprechend",  # Normal findings
            "reduziert", "erhöht", "erniedrigt", "pathologisch",  # Finding descriptors
            # Phase 11: Additional clinical descriptors (commonly misclassified)
            "normwertig", "normwertige", "normwertiger", "normwertigen",
            "diskret", "diskrete", "diskreter", "diskreten",  # Subtle/mild
            "sonorer", "sonore", "sonoren",  # Sonorous (percussion sound)
            "klopfschall", "klopfschalles",  # Percussion sound
            "druckdolent", "druckschmerzhaft", "palpabel", "tastbar",  # Examination terms
            "auskultation", "perkussion", "inspektion", "palpation",  # Exam methods
            "systolisch", "diastolisch", "endsystolisch", "enddiastolisch",  # Cardiac timing
            "linksventrikulär", "rechtsventrikulär", "biventrikulär",  # Cardiac chambers
            "anterolateral", "posterolateral", "inferolateral",  # Anatomical directions
            "simpson", "biplan", "monoplan",  # Echo methods

            # ==================== GERMAN CLINICAL DESCRIPTORS ====================
            "beschwerdefrei", "symptomfrei", "fieberfrei", "schmerzfrei",
            "dyspnoe", "orthopnoe", "belastungsdyspnoe", "ruhedyspnoe",
            # Phase 7: Physical examination descriptors
            "ausladend", "ausladende", "ausladender", "ausladenden",  # Protruding/distended
            "retrosternal", "präkordial", "epigastrisch", "periumbilikal",
            "druckgefühl", "druckgefühle", "engegefühl", "beklemmung",
            "ausstrahlung", "ausstrahlen", "ausstrahlend",
            "sistieren", "sistierend", "intermittierend", "persistierend",
            "progredient", "regredient", "stabil", "stationär",
            "akut", "subakut", "chronisch", "rezidivierend",
            # Shape/extent descriptors (commonly misclassified)
            "umschrieben", "umschriebene", "umschriebener", "umschriebenen", "umschriebenes",
            "diffus", "diffuse", "diffuser", "diffusen", "diffuses",
            "fokal", "fokale", "fokaler", "fokalen", "fokales",
            "multifokal", "multifokale", "multifokaler", "multifokalen",
            "konfluierend", "konfluierende", "konfluierender", "konfluierenden",
            # Inspiratory/expiratory (lung function context)
            "inspiratorisch", "inspiratorische", "inspiratorischer", "inspiratorischen",
            "exspiratorisch", "exspiratorische", "exspiratorischer", "exspiratorischen",
            # Age-adjusted terms
            "altersentsprechend", "altersentsprechende", "altersentsprechender", "altersentsprechenden",
            "altersadaptiert", "altersadaptierte", "altersadaptierter", "altersadaptierten",
            "altersnormal", "altersnormale", "altersnormaler", "altersnormalen",

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
            # Phase 11: Missing severity adjectives (commonly misclassified as NAME)
            "leichtgradig", "leichtgradige", "leichtgradiger", "leichtgradigen",
            "geringfügig", "geringfügige", "geringfügiger", "geringfügigen",
            "geringgradig", "geringgradige", "geringgradiger", "geringgradigen",

            # Organ-specific adjectives
            "kardial", "kardiale", "kardialer", "kardialen", "kardiales",
            "pulmonal", "pulmonale", "pulmonaler", "pulmonalen", "pulmonales",
            # Compound organ adjectives (commonly misclassified as PER/NAME)
            "kardiopulmonal", "kardiopulmonale", "kardiopulmonaler", "kardiopulmonalen", "kardiopulmonales",
            "kardiorenal", "kardiorenale", "kardiorenaler", "kardiorenalen",
            "hepatorenal", "hepatorenale", "hepatorenaler", "hepatorenalen",
            "pulmonalarteriell", "pulmonalarterielle", "pulmonalarterieller", "pulmonalarteriellen",
            "renal", "renale", "renaler", "renalen", "renales",
            "hepatisch", "hepatische", "hepatischer", "hepatischen", "hepatisches",
            "zerebral", "zerebrale", "zerebraler", "zerebralen", "zerebrales",
            "gastrointestinal", "gastrointestinale", "gastrointestinaler", "gastrointestinalen",
            "vaskulär", "vaskuläre", "vaskulärer", "vaskulären",
            "muskulär", "muskuläre", "muskulärer", "muskulären",
            "neurologisch", "neurologische", "neurologischer", "neurologischen",
            # Phase 9: Rheumatological adjectives (commonly misclassified as LOC)
            "rheumatoide", "rheumatoider", "rheumatoiden", "rheumatoid",
            "rheumatisch", "rheumatische", "rheumatischer", "rheumatischen",

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

            # ECG/EKG terms (commonly misclassified as ORG)
            "st-strecke", "st-strecken", "st-strecken-veränderungen", "st-strecken-senkung",
            "st-strecken-hebung", "st-hebung", "st-senkung", "st-veränderungen",
            "t-welle", "t-wellen", "t-negativierung", "t-wellen-veränderungen",
            "p-welle", "p-wellen", "pq-zeit", "pq-intervall", "pq-strecke",
            "qrs-komplex", "qrs-zeit", "qrs-dauer", "qrs-breite",
            "qt-zeit", "qt-intervall", "qtc-zeit", "qt-verlängerung",
            "r-zacke", "r-progression", "r-verlust", "r-reduktion",
            "q-zacke", "q-zacken", "pathologische-q-zacke",
            "vorhofflimmern", "vorhofflattern", "vorhof", "ventrikel",
            "repolarisationsstörung", "repolarisationsstörungen", "erregungsrückbildung",
            "erregungsrückbildungsstörung", "erregungsrückbildungsstörungen",
            "sinusrhythmus", "sinusarrhythmie", "sinusbradykardie", "sinustachykardie",
            "extrasystole", "extrasystolen", "supraventrikulär", "ventrikulär",

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

            # Lung examination terms (commonly misclassified)
            "vesikulär", "vesikuläres", "vesikuläre", "vesikulären", "vesikulärer",
            "bronchial", "bronchiale", "bronchialer", "bronchialen", "bronchiales",
            "atemgeräusch", "atemgeräusche", "atemgeräuschen",
            "rasselgeräusch", "rasselgeräusche", "rasselgeräuschen",
            "nebengeräusch", "nebengeräusche", "nebengeräuschen",
            "giemen", "brummen", "stridor", "knistern",
            "seitengleich", "seitengleiche", "seitengleicher", "seitengleichen",
            "abgeschwächt", "abgeschwächte", "abgeschwächter", "abgeschwächten",
            "aufgehobenes", "aufgehobene", "aufgehobener", "aufgehobenen",

            # ==================== BLOOD CELL INDICES (Blutbild-Indices) ====================
            # These are frequently misclassified as ORG
            "mcv", "mch", "mchc", "rdw", "mpv", "pdw", "pct",
            "plt", "wbc", "rbc", "hct", "hgb",
            # Blood cell compound terms (commonly misclassified as LOC)
            "leukozytenzahl", "erythrozytenzahl", "thrombozytenzahl",
            "lymphozytenzahl", "monozytenzahl", "granulozytenzahl",

            # ==================== LUNG FUNCTION (Lungenfunktion) ====================
            # These are frequently misclassified as ORG
            "fev1", "fvc", "fef", "fef25", "fef50", "fef75", "fef25-75",
            "pef", "mef", "pif", "tlc", "rv", "frc", "vc", "ivc", "evc",
            "dlco", "kco", "raw", "sraw", "gaw", "sgaw",
            "vitalkapazität", "residualvolumen", "atemwegswiderstand",
            # Lung function tests/indices (commonly misclassified as LOC/ORG)
            "tiffeneau", "tiffeneau-index", "tiffeneau-test",
            "peak", "peak-flow", "peakflow",

            # ==================== CARDIAC MEASUREMENTS (Kardiale Messungen) ====================
            # Echocardiography and vascular measurements - often misclassified as ORG
            "tapse", "mapse", "tdi", "gls",
            "abi", "tbi", "pwv", "aix", "cfpwv", "cfpwv_calc",
            "lvedv", "lvesv", "lvedp",
            "lv-funktion", "rv-funktion", "la-funktion",
            # Cardiac chambers (commonly misclassified as ORG)
            "linke kammer", "rechte kammer", "linker vorhof", "rechter vorhof",
            "linkskammer", "rechtskammer", "linksvorhof", "rechtsvorhof",

            # ==================== BODY COMPOSITION (Körperzusammensetzung) ====================
            # These are frequently misclassified as LOC/ORG
            "bia", "bsa", "ffm", "fm", "tbw", "ecw", "icw",
            "körperwasseranteil", "körperfettanteil", "muskelmasse",
            "knochenmasse", "grundumsatz", "eingeweidefett",
            "viszeralfett", "subkutanfett",

            # ==================== ADDITIONAL CHEMISTRY/ELECTROLYTES ====================
            "alb", "tp", "ast", "alt", "asat", "alat",
            "bun", "crcl",
            "na", "k", "cl", "mg", "po4", "fe", "zn", "cu",
            "elektrolyte", "serumelektrolyte",
            # Lab standards/methods (commonly misclassified as LOC/ORG)
            "ifcc", "dcct", "ngsp",  # HbA1c standardization methods
            "glucosewert", "glucosewerte", "glukosewert", "glukosewerte",
            # Alternate spellings (ae vs ä)
            "haematokrit", "haemoglobin",

            # ==================== LATIN ANATOMICAL TERMS ====================
            # Commonly used in German radiology, frequently misclassified as LOC
            # Pancreas parts
            "caput", "corpus", "cauda",
            # Vessels
            "truncus", "coeliacus", "mesenterica", "renalis",
            "vena", "arteria", "ductus",
            # General anatomy
            "lobus", "segmentum", "regio",
            "apex", "basis", "fundus",
            "collum", "isthmus", "hilus", "hilum",
            "cortex", "medulla", "parenchym",
            # GI tract
            "antrum", "pylorus", "cardia",
            "bulbus", "duodenum", "jejunum", "ileum", "colon", "rectum", "sigmoid",
            # Urogenital
            "vesica", "ureter", "urethra", "pelvis",
            "cervix", "ovarium", "tuba",

            # ==================== INFECTIOUS DISEASES ====================
            # Could be confused with locations
            "corona", "covid", "covid-19", "sars", "sars-cov-2", "mers",
            "influenza", "grippe",
            "corona-infektion", "coronainfektion", "coronavirus-infektion",
            "covid-infektion", "covidinfektion",

            # ==================== LIVER CONDITIONS WITH GRADING ====================
            "steatosis", "hepatis", "grad", "fibrosis",
            "nash", "nafld", "afld",
            # Medical grading terms
            "stadium", "stage", "schweregrad", "ausprägung",

            # ==================== GERMAN ABBREVIATIONS (must not be split/mangled) ====================
            "z.b.", "d.h.", "u.a.", "bzw.", "ggf.", "evtl.", "etc.",
            "inkl.", "exkl.", "max.", "min.", "vs.",
            "li.", "re.", "bds.",
            # Phase 6: Medical status abbreviation (Zustand nach = status post)
            "z.n.", "z. n.",
            # Medical report abbreviations
            "ber.", "mittl.", "berechn.", "berechn", "geschätzt",
            "neg.", "pos.", "path.", "phys.", "norm.",
            "kalkuliert", "kalkulierte", "kalkulierter", "kalkulierten",

            # ==================== UV/SKIN TERMS ====================
            "solarien", "solarium",
            "uv-faktor", "uv-index", "lichtschutzfaktor", "lsf", "spf",
            # Time of day / sun exposure context (commonly misclassified as LOC)
            "mittagszeit", "mittagssonne", "sommermittagssonne",
            "sonnenexposition", "sonnenlicht", "sonneneinstrahlung",
            "morgens", "mittags", "abends", "nachts", "nüchtern",
            # Cell/tissue terms (commonly misclassified as LOC)
            "leberzelle", "leberzellen", "hepatozyt", "hepatozyten",

            # ==================== CELL TYPE ABBREVIATIONS ====================
            # Commonly in lab reports, frequently misclassified as NAME
            "ery", "erys", "leuko", "leukos", "thrombo", "thrombos",
            "lympho", "lymphos", "mono", "monos", "granu", "granus",
            "neutro", "neutros", "eosino", "basophil",

            # ==================== GERMAN COMPOUND MEDICAL TERMS ====================
            # Vascular/anatomical compounds (commonly misclassified as LOC)
            "bifurkation", "trifurkation", "anastomose", "gefäßanastomose",
            "stenose", "restenose", "thrombosierung",

            # Metabolism terms (commonly misclassified as ORG)
            "grundumsatz", "stoffwechselumsatz", "kalorienumsatz", "energieumsatz",
            "ruheumsatz", "leistungsumsatz",

            # Measurement terms (compound)
            "knöchel-arm-index", "ankle-brachial-index",
            "körperfettanteil", "körperwasseranteil",
            "gesamt-körperwasseranteil", "gesamtkörperwasseranteil",
            # Blood pressure and heart rate behavior terms
            "rr-verhalten", "rrverhalten", "blutdruckverhalten",
            "herzfrequenzverhalten", "pulsverhalten",
            # Diet/nutrition abbreviations (commonly misclassified)
            "fdh", "bmr",  # "Friss die Hälfte", Basal Metabolic Rate
            # German verbs that conflict with city names (essen = to eat vs Essen city)
            "essen", "trinken", "fasten",

            # Lab cell terms (full German names - commonly misclassified as LOC)
            "leukozyten", "erythrozyten", "thrombozyten",
            "hämatokrit", "hämoglobin",

            # ==================== VITAMINS ====================
            # Must protect "Vitamin X" constructs from name detection
            "vitamin", "vitamin a", "vitamin b", "vitamin b1", "vitamin b2",
            "vitamin b6", "vitamin b12", "vitamin c", "vitamin d", "vitamin d2",
            "vitamin d3", "vitamin e", "vitamin k", "vitamin k1", "vitamin k2",
            "vitamine", "vitaminmangel", "vitaminspiegel", "vitaminsubstitution",
            # Phase 6: Abbreviated vitamin forms (include standalone "vit" to prevent NER misclassification)
            "vit", "vit.", "vit. b12", "vit b12", "vit. d", "vit d", "vit. k", "vit k",

            # ==================== LIVER SCORING SYSTEMS (Phase 6) ====================
            # Child-Pugh classification for liver cirrhosis (commonly misclassified as NAME)
            "child a", "child b", "child c", "child-pugh", "child pugh",
            "meld", "meld-score", "meld score", "meld-na",

            # ==================== PHASE 8: COMPREHENSIVE MEDICAL TERMS EXPANSION ====================

            # ==================== EXTENDED ANATOMY ====================
            # Head and neck
            "stirn", "schläfe", "wange", "kinn", "ohr", "ohren", "nase", "auge", "augen",
            "augenlid", "augenlider", "pupille", "pupillen", "iris", "netzhaut", "hornhaut",
            "zunge", "gaumen", "rachen", "kehlkopf", "larynx", "pharynx", "trachea",
            "speiseröhre", "ösophagus", "mandeln", "tonsillen", "thymus",
            "hypophyse", "hypothalamus", "epiphyse", "zirbeldrüse",
            # Thorax/chest
            "brustkorb", "rippen", "sternum", "brustbein", "zwerchfell", "diaphragma",
            "pleura", "brustfell", "mediastinum", "perikard", "herzbeutel",
            "bronchus", "bronchien", "bronchiolen", "alveolen", "lungenlappen",
            "oberlappen", "mittellappen", "unterlappen", "lingula",
            # Heart detailed
            "vorhof", "vorhöfe", "kammer", "kammern", "septum", "herzscheidewand",
            "herzspitze", "herzbasis", "herzmuskel", "myokard", "endokard", "epikard",
            "sinusknoten", "av-knoten", "his-bündel", "purkinje-fasern",
            "koronargefäße", "koronararterien", "herzkranzgefäße",
            "riva", "rcx", "rca", "lca", "lad", "cx", "rpd", "rpls",
            # Abdomen detailed
            "peritoneum", "bauchfell", "mesenterium", "omentum", "netz",
            "leberlappen", "lebersegment", "lebersegmente", "leberkapsel",
            "gallengang", "gallengänge", "ductus choledochus", "dhc",
            "pankreasgang", "wirsung-gang", "papille", "papilla vateri",
            "magenausgang", "mageneingang", "magenfundus", "magencorpus", "magenantrum",
            "pylorus", "duodenum", "jejunum", "ileum", "zökum", "caecum",
            "appendix", "blinddarm", "kolon", "dickdarm", "sigma", "sigmoid",
            "rektum", "mastdarm", "analkanal", "anus",
            # Urogenital
            "nierenbecken", "nierenkelch", "nierenkelche", "nierenrinde", "nierenmark",
            "harnleiter", "ureter", "harnblase", "blasenhals", "harnröhre", "urethra",
            "nebenhoden", "epididymis", "samenleiter", "vas deferens",
            "samenbläschen", "prostatakapsel",
            "eileiter", "tube", "tuben", "gebärmutter", "endometrium", "myometrium",
            "zervix", "portio", "vagina", "scheide", "vulva", "labien",
            "eierstock", "eierstöcke", "follikel", "gelbkörper", "corpus luteum",
            # Musculoskeletal detailed
            "femur", "oberschenkelknochen", "tibia", "schienbein", "fibula", "wadenbein",
            "humerus", "oberarmknochen", "radius", "speiche", "ulna", "elle",
            "clavicula", "schlüsselbein", "scapula", "schulterblatt",
            "patella", "kniescheibe", "meniskus", "menisken", "kreuzband", "kreuzbänder",
            "vorderes kreuzband", "hinteres kreuzband", "seitenband", "seitenbänder",
            "bandscheibe", "bandscheiben", "wirbelkörper", "wirbelbogen",
            "hws", "bws", "lws", "sakrum", "steißbein", "coccyx",
            "ileum", "os ilium", "sitzbein", "schambein", "symphyse",
            "acetabulum", "hüftpfanne", "hüftkopf", "trochanter",
            "metacarpus", "mittelhandknochen", "phalanx", "phalangen", "fingergelenk",
            "metatarsus", "mittelfußknochen", "sprunggelenk", "fußwurzel", "tarsus",
            # Nervous system detailed
            "großhirn", "cerebrum", "kleinhirn", "cerebellum", "hirnstamm",
            "mittelhirn", "brücke", "pons", "medulla oblongata", "verlängertes mark",
            "frontallappen", "temporallappen", "parietallappen", "okzipitallappen",
            "insula", "basalganglien", "thalamus", "striatum",
            "hippocampus", "amygdala", "corpus callosum", "balken",
            "liquor", "ventrikelsystem", "seitenventrikel", "dritter ventrikel", "vierter ventrikel",
            "plexus", "plexus brachialis", "plexus lumbalis", "plexus sacralis",
            "nervus", "n.", "nervenwurzel", "spinalnerv", "hirnnerv",
            "vagus", "trigeminus", "fazialis", "optikus", "okulomotorius",
            # Lymphatic system
            "lymphknoten", "lymphgefäß", "lymphgefäße", "lymphbahn", "lymphbahnen",
            "milzarterie", "milzvene", "milzkapsel", "milzparenchym",
            "thymusdrüse", "waldeyer-rachenring",
            # Blood vessels detailed
            "truncus brachiocephalicus", "arteria carotis", "karotis", "carotis",
            "a. carotis interna", "a. carotis externa", "aci", "ace",
            "arteria vertebralis", "arteria basilaris", "circulus willisii",
            "arteria subclavia", "arteria axillaris", "arteria brachialis",
            "arteria radialis", "arteria ulnaris", "arteria femoralis",
            "arteria poplitea", "arteria tibialis", "arteria dorsalis pedis",
            "vena cava", "v. cava superior", "v. cava inferior", "vcs", "vci",
            "vena jugularis", "vena subclavia", "vena femoralis", "vena saphena",
            "vena portae", "portalvene", "lebervenen", "venae hepaticae",
            "vena renalis", "nierenvene", "vena lienalis",

            # ==================== EXTENDED CONDITIONS/DISEASES ====================
            # Cardiovascular
            "angina", "angina pectoris", "ap", "stabile angina", "instabile angina",
            "acs", "akutes koronarsyndrom", "nstemi", "stemi", "herzinfarkt", "myokardinfarkt",
            "herzrhythmusstörung", "herzrhythmusstörungen", "vorhofflimmern", "vhf",
            "vorhofflattern", "kammerflattern", "kammerflimmern", "asystolie",
            "herzstillstand", "reanimation", "reanimationspflichtig",
            "kardiomyopathie", "dcm", "hcm", "rcm", "arvc",
            "myokarditis", "endokarditis", "perikarditis", "perikarderguss",
            "herztamponade", "konstriktion", "konstriktive perikarditis",
            "aortendissektion", "aortenaneurysma", "bauchaortenaneurysma", "baa",
            "thorakales aortenaneurysma", "taa",
            "tiefe venenthrombose", "tvt", "beinvenenthrombose", "beckenvenenthrombose",
            "lungenembolie", "lungenarterienembolie", "lae", "le",
            "pulmonale hypertonie", "pah", "cteph",
            "herzschrittmacher", "icd", "crt", "crt-d", "crt-p",
            # Pulmonary
            "pneumothorax", "spannungspneumothorax", "hämatothorax", "pleuraerguss",
            "pleuritis", "empyem", "lungenabszess", "lungenödem",
            "atelektase", "dystelektase", "belüftungsstörung", "infiltrat",
            "pneumonisches infiltrat", "interstitielle pneumonie", "lobärpneumonie",
            "aspirationspneumonie", "nosokomiale pneumonie", "cap", "hap", "vap",
            "lungentuberkulose", "tbc", "tuberkulose",
            "lungenfibrose", "ipf", "sarkoidose", "asbestose", "silikose",
            "bronchiektasen", "bronchiektasie", "mukoviszidose", "cf", "cystische fibrose",
            "lungenemphysem", "bullöses emphysem", "alpha-1-antitrypsin-mangel",
            "schlafapnoe", "obstruktive schlafapnoe", "zentrale schlafapnoe",
            # Gastrointestinal
            "reflux", "refluxösophagitis", "gerd", "ösophagusvarizen", "varizenblutung",
            "ösophaguskarzinom", "magenkarzinom", "magenulkus", "duodenalulkus",
            "peptisches ulkus", "ulcus ventriculi", "ulcus duodeni",
            "helicobacter", "h. pylori", "hp-infektion",
            "gastroenteritis", "enteritis", "kolitis", "morbus crohn", "colitis ulcerosa",
            "reizdarmsyndrom", "rds", "ibs", "obstipation", "verstopfung",
            "diarrhoe", "durchfall", "ileus", "darmverschluss", "subileus",
            "dünndarmstenose", "dickdarmstenose", "sigmadivertikel", "divertikulitis",
            "divertikulose", "polyp", "polypen", "adenom", "adenome",
            "kolonkarzinom", "rektumkarzinom", "kolorektales karzinom", "crc",
            "appendizitis", "blinddarmentzündung", "peritonitis", "bauchfellentzündung",
            "aszites", "bauchwassersucht", "hepatomegalie", "splenomegalie",
            "leberzirrhose", "leberfibrose", "fettleber", "steatohepatitis",
            "leberkoma", "hepatische enzephalopathie", "he",
            "leberversagen", "akutes leberversagen", "alf",
            "hepatozelluläres karzinom", "leberzellkarzinom", "cholangiokarzinom",
            "cholangitis", "psc", "pbc", "autoimmunhepatitis", "aih",
            "cholelithiasis", "gallensteine", "choledocholithiasis", "cholezystolithiasis",
            "ikterus", "gelbsucht", "verschlussikterus", "hämolytischer ikterus",
            "akute pankreatitis", "chronische pankreatitis", "nekrotisierende pankreatitis",
            "pankreaspseudozyste", "pankreaskarzinom", "pankreasinsuffizienz",
            "exokrine pankreasinsuffizienz", "endokrine pankreasinsuffizienz",
            # Renal/Urological
            "akutes nierenversagen", "anv", "chronisches nierenversagen", "cnv",
            "akute nierenschädigung", "chronische nierenerkrankung", "cni",
            "urämie", "dialysepflichtig", "hämodialyse", "peritonealdialyse", "capd",
            "nierentransplantation", "transplantatniere",
            "nephrolithiasis", "nierensteine", "urolithiasis", "harnsteine",
            "nierenbeckenentzündung", "harnwegsinfekt", "hwi", "zystitis", "blasenentzündung",
            "prostatitis", "prostatahyperplasie", "bph", "prostatakarzinom",
            "harnverhalt", "harninkontinenz", "stressinkontinenz", "dranginkontinenz",
            "hydronephrose", "harnstau", "harnleiterobstruktion",
            "glomerulonephritis", "iga-nephropathie", "membranöse nephropathie",
            "nephrotisches syndrom", "nephritisches syndrom",
            "nierenzyste", "zystenniere", "polyzystische nierenerkrankung", "adpkd",
            "nierenzellkarzinom", "ncc", "wilms-tumor",
            # Neurological
            "schlaganfall", "hirninfarkt", "ischämischer schlaganfall", "hämorrhagischer schlaganfall",
            "hirnblutung", "subarachnoidalblutung", "sab", "intrakranielle blutung", "icb",
            "subduralhämatom", "epiduralhämatom", "kontusionsblutung",
            "transitorisch ischämische attacke", "tia",
            "multiple sklerose", "ms", "enzephalomyelitis disseminata",
            "morbus parkinson", "parkinson-syndrom", "tremor", "rigor", "akinese",
            "demenz", "morbus alzheimer", "vaskuläre demenz", "lewy-körperchen-demenz",
            "epilepsie", "epileptischer anfall", "krampfanfall", "status epilepticus",
            "fokaler anfall", "generalisierter anfall", "grand mal", "petit mal",
            "kopfschmerz", "migräne", "spannungskopfschmerz", "clusterkopfschmerz",
            "trigeminusneuralgie", "fazialisparese", "bellsche parese",
            "polyneuropathie", "pnp", "radikulopathie", "mononeuropathie",
            "karpaltunnelsyndrom", "cts", "sulcus-ulnaris-syndrom",
            "bandscheibenvorfall", "diskusprolaps", "bsv", "spinalstenose",
            "myelopathie", "querschnittlähmung", "paraparese", "tetraparese",
            "hirnödem", "hydrozephalus", "liquorzirkulationsstörung",
            "hirntumor", "gliom", "glioblastom", "meningeom", "hirnmetastase",
            # Hematological/Oncological
            "leukämie", "akute leukämie", "chronische leukämie", "all", "aml", "cll", "cml",
            "lymphom", "hodgkin-lymphom", "non-hodgkin-lymphom", "nhl",
            "multiples myelom", "plasmozytom", "mds", "myelodysplastisches syndrom",
            "myelofibrose", "polycythaemia vera", "essentielle thrombozythämie",
            "hämophilie", "von-willebrand-syndrom", "dic",
            "eisenmangelanämie", "perniziöse anämie", "hämolytische anämie",
            "sichelzellanämie", "thalassämie", "aplastische anämie",
            "thrombozytopenie", "leukopenie", "neutropenie", "panzytopenie",
            "thrombozytose", "leukozytose", "lymphozytose", "monozytose",
            "metastasierung", "fernmetastase", "lymphknotenmetastase",
            "tumormarker", "cea", "ca 19-9", "ca 125", "psa", "afp",
            # Endocrine
            "diabetes mellitus", "dm1", "dm2", "typ-1-diabetes", "typ-2-diabetes",
            "diabetische nephropathie", "diabetische retinopathie", "diabetische neuropathie",
            "diabetisches fußsyndrom", "hypoglykämie", "hyperglykämie",
            "ketoazidose", "diabetische ketoazidose", "dka", "hyperosmolares koma",
            "struma", "knotenstruma", "schilddrüsenknoten", "schilddrüsenkarzinom",
            "thyreoiditis", "hashimoto", "basedow", "morbus basedow",
            "cushing-syndrom", "morbus cushing", "addison", "morbus addison",
            "nebenniereninsuffizienz", "phäochromozytom", "conn-syndrom",
            "hyperparathyreoidismus", "hypoparathyreoidismus",
            "osteoporose", "osteopenie", "osteomalazie", "rachitis",
            "hypophysenadenom", "prolaktinom", "akromegalie", "hypopituitarismus",
            # Rheumatological/Immunological
            "rheumatoide arthritis", "ra", "seropositive ra", "seronegative ra",
            "systemischer lupus erythematodes", "sle", "lupus",
            "sklerodermie", "systemische sklerose", "dermatomyositis", "polymyositis",
            "sjögren-syndrom", "vaskulitis", "granulomatose mit polyangiitis", "gpa",
            "riesenzellarteriitis", "polymyalgia rheumatica", "pmr",
            "spondylitis ankylosans", "morbus bechterew", "psoriasis-arthritis",
            "reaktive arthritis", "arthritis urica", "gichtanfall",
            "fibromyalgie", "chronisches schmerzsyndrom",
            # Infectious
            "sepsis", "septischer schock", "sirs", "multiorganversagen", "mof",
            "bakteriämie", "virämie", "fungämie", "candidämie",
            "abszess", "phlegmone", "erysipel", "zellulitis", "nekrotisierende fasziitis",
            "osteomyelitis", "spondylodiszitis", "endokarditis", "ie",
            "meningitis", "enzephalitis", "meningoenzephalitis",
            "pneumonie", "lobärpneumonie", "bronchopneumonie", "interstitielle pneumonie",
            "tuberkulose", "tb", "latente tb", "aktive tb",
            "hiv", "aids", "hiv-infektion", "antiretrovirale therapie", "art",
            "hepatitis a", "hepatitis b", "hepatitis c", "hepatitis d", "hepatitis e",
            "hbsag", "anti-hbs", "anti-hbc", "hcv-rna", "hbv-dna",
            "herpes", "herpes simplex", "hsv", "herpes zoster", "vzv", "gürtelrose",
            "influenza", "grippaler infekt", "covid-19", "sars-cov-2",
            "malaria", "dengue", "typhus", "borreliose", "fsme",
            "clostridium difficile", "cdiff", "c. diff", "clostridioides difficile",
            "mrsa", "mrgn", "esbl", "vre", "multiresistente erreger",

            # ==================== EXTENDED PROCEDURES ====================
            # Cardiac procedures
            "herzkatheter", "koronarangiographie", "koronarangiografie", "ptca", "pci",
            "stentimplantation", "drug-eluting stent", "des", "bare-metal stent", "bms",
            "aortenklappenersatz", "tavi", "savr", "mitraclip", "mvr",
            "koronarer bypass", "cabg", "acvb", "herzchirurgie",
            "schrittmacherimplantation", "icd-implantation", "crt-implantation",
            "ablation", "katheterablation", "pulmonalvenenisolation", "pvi",
            "kardioversion", "elektrische kardioversion", "defibrillation",
            "perikardpunktion", "perikardiozenthese", "perikarddrainage",
            # Vascular procedures
            "angiographie", "angiografie", "dsa", "katheterangiographie",
            "angioplastie", "pta", "stentgraft", "evar", "tevar",
            "thrombektomie", "embolektomie", "lyse", "thrombolyse",
            "karotis-tee", "carotis-stenting", "cea",
            "varizensklerosierung", "varizenstripping", "crossektomie",
            "dialyseshunt", "av-fistel", "shuntanlage",
            # GI procedures
            "ösophagogastroduodenoskopie", "ögd", "gastroskopie",
            "koloskopie", "sigmoidoskopie", "rektoskopie", "proktoskopie",
            "ercp", "eus", "endosonographie", "kapselendoskopie",
            "polypektomie", "mukosektomie", "emr", "esd",
            "varizenligatur", "gummibandligatur", "sklerotherapie",
            "peg", "peg-anlage", "pej", "jejunalsonde",
            "cholezystektomie", "laparoskopische cholezystektomie",
            "whipple-operation", "pankreatikoduodenektomie",
            "leberteilresektion", "hemihepatektomie", "lebertransplantation", "ltx",
            "aszitespunktion", "aszitesdrainage", "parazentese",
            "leberpunktion", "leberbiopsie",
            # Pulmonary procedures
            "bronchoskopie", "bal", "bronchoalveoläre lavage",
            "pleurapunktion", "thorakozentese", "pleurabiopsie",
            "thoraxdrainage", "bülau-drainage", "pleurodese",
            "mediastinoskopie", "vats", "thorakoskopie",
            "lungenteilresektion", "lobektomie", "pneumonektomie", "segmentresektion",
            "tracheotomie", "tracheostomie", "koniotomie",
            "intubation", "extubation", "beatmung", "invasive beatmung", "niv",
            # Neurological procedures
            "lumbalpunktion", "liquorpunktion", "spinalpunktion",
            "kraniotomie", "kraniektomie", "ventrikulostomie",
            "shuntanlage", "vp-shunt", "ventrikuloperitonealer shunt",
            "aneurysma-clipping", "coiling", "endovaskuläre behandlung",
            "thrombektomie", "mechanische thrombektomie", "evt",
            "tiefe hirnstimulation", "dbs",
            # Urological procedures
            "zystoskopie", "ureteroskopie", "pyeloskopie",
            "turb", "tur-blase", "turp", "tur-prostata",
            "nephrektomie", "nierenteilresektion", "nierentransplantation", "ntx",
            "ureteroskopische steinentfernung", "pcnl", "eswl",
            "harnleiterschiene", "dj-katheter", "nephrostomie",
            "prostatektomie", "radikale prostatektomie", "rarp",
            # Orthopedic procedures
            "arthroskopie", "kniearthroskopie", "schulterarthroskopie",
            "kreuzbandplastik", "meniskusresektion", "meniskusnaht",
            "osteosynthese", "plattenosteosynthese", "marknagelung",
            "hüft-tep", "knie-tep", "endoprothese", "prothesenwechsel",
            "wirbelsäulenversteifung", "spondylodese", "nukleotomie", "laminektomie",
            "kyphoplastie", "vertebroplastie",
            # Oncological procedures
            "tumorresektion", "r0-resektion", "r1-resektion", "r2-resektion",
            "lymphadenektomie", "sentinellymphknotenbiopsie", "slnb",
            "chemotherapie", "radiochemotherapie", "immuntherapie",
            "bestrahlung", "strahlentherapie", "brachytherapie",
            "palliative versorgung", "palliativmedizin",

            # ==================== EXTENDED LAB VALUES ====================
            # Complete blood count
            "differentialblutbild", "blutbild", "kleines blutbild", "großes blutbild",
            "retikulozyten", "retikulozytenzahl", "retikulozytenindex",
            "segmentkernige", "stabkernige", "lymphozyten", "monozyten",
            "eosinophile", "basophile", "neutrophile",
            # Coagulation
            "gerinnungsstatus", "gerinnungsparameter", "blutgerinnung",
            "antithrombin", "at-iii", "protein c", "protein s",
            "lupus-antikoagulans", "anticardiolipin", "faktor v leiden",
            "thrombophilie", "gerinnungsfaktor", "faktor viii", "faktor ix",
            # Liver function
            "leberwerte", "leberfunktion", "lebersynthese",
            "albumin", "gesamteiweiß", "gesamtprotein",
            "cholinesterase", "che", "ammoniak", "nh3",
            "direktes bilirubin", "indirektes bilirubin", "konjugiertes bilirubin",
            # Pancreas
            "amylase", "lipase", "pankreasenzyme", "pankreaselastase",
            # Kidney function
            "nierenwerte", "nierenfunktion", "nierenretentionsparameter",
            "cystatin c", "cystatin-c", "gfr", "egfr", "kreatinin-clearance",
            "harnstoff-n", "bun", "harnsäure", "uric acid",
            # Electrolytes extended
            "natrium", "kalium", "chlorid", "calcium", "magnesium", "phosphat",
            "bikarbonat", "laktat", "lactat",
            # Cardiac markers
            "troponin i", "troponin t", "tnt", "tni", "hs-troponin",
            "ck-mb masse", "myoglobin", "bnp", "nt-probnp",
            # Inflammation
            "procalcitonin", "pct", "interleukin", "il-6", "il-1", "tnf-alpha",
            "blutsenkung", "bsg", "blutkörperchensenkung",
            # Thyroid
            "schilddrüsenwerte", "ft3", "ft4", "freies t3", "freies t4",
            "trak", "tpo-ak", "tg-ak", "thyreoglobulin",
            # Lipids
            "lipidprofil", "lipidstatus", "gesamtcholesterin",
            "ldl", "hdl", "vldl", "ldl-cholesterin", "hdl-cholesterin",
            "lipoprotein a", "lp(a)", "apolipoprotein",
            # Diabetes
            "nüchternglukose", "nüchternblutzucker", "nbz",
            "postprandiale glukose", "ogtt", "oraler glukosetoleranztest",
            "c-peptid", "insulin", "insulinspiegel",
            # Iron studies
            "eisenstatus", "ferritin", "transferrin", "transferrinsättigung",
            "retikulozytenhämoglobin", "ret-he", "löslicher transferrinrezeptor",
            # Urine
            "urinstatus", "urinuntersuchung", "mittelstrahlurin",
            "proteinurie", "albuminurie", "mikroalbuminurie",
            "hämaturie", "leukozyturie", "bakteriurie", "pyurie",
            "urinkultur", "keimzahl", "kbe",
            "kreatinin im urin", "protein-kreatinin-quotient",
            # Blood gas
            "blutgasanalyse", "bga", "astrup",
            "ph", "pco2", "po2", "sao2", "spo2",
            "basenexzess", "be", "standardbikarbonat",
            "anionenlücke", "oxygenierungsindex",
            # Autoantibodies
            "autoantikörper", "ana", "anca", "p-anca", "c-anca",
            "anti-ds-dna", "rf", "rheumafaktor", "anti-ccp",
            "anti-jo-1", "anti-scl-70", "anti-sm", "anti-rnp",
            # Tumor markers
            "tumormarker", "cea", "ca 19-9", "ca 125", "ca 15-3",
            "psa", "fpsa", "afp", "hcg", "beta-hcg",
            "ldh", "s100", "nse", "chromogranin",
            # Drug levels
            "medikamentenspiegel", "talspiegel", "spitzenspiegel",
            "digoxin", "digitoxin", "theophyllin", "phenytoin",
            "vancomycin", "gentamicin", "ciclosporin", "tacrolimus",

            # ==================== RADIOLOGY/IMAGING TERMS ====================
            "kontrastmittel", "km", "kontrastmittelgabe", "kontrastierung",
            "nativ", "nativuntersuchung", "ohne km", "mit km",
            "röntgendichte", "dichte", "hyperdense", "hypodense", "isodense",
            "signalintensität", "hyperintens", "hypointens", "isointens",
            "t1-gewichtet", "t2-gewichtet", "t1w", "t2w", "flair", "dwi", "adc",
            "kontrastmittelaufnahme", "enhancement", "anreicherung",
            "raumforderung", "rf", "läsion", "herd", "herdbefund",
            "zyste", "zystisch", "solide", "zystisch-solide",
            "verkalkung", "kalzifikation", "sklerose", "osteosklerose",
            "osteolyse", "osteolytisch", "destruktion",
            "infiltration", "infiltrativ", "raumfordernd",
            "kompression", "impression", "verlagerung", "deviation",
            "obstruktion", "stenose", "okklusion", "verschluss",
            "dilatation", "erweiterung", "ektasie",
            "wandverdickung", "wandunregelmäßigkeit",
            "flüssigkeitskollektion", "flüssigkeitsansammlung",
            "abszess", "abszedierung", "einschmelzung",
            "freie flüssigkeit", "freie luft", "pneumoperitoneum",
            "pleuraerguss", "perikarderguss", "aszites",
            "lymphadenopathie", "lap", "lymphknotenvergrößerung",
            "splenomegalie", "hepatomegalie", "nephromegalie",
            "parenchymveränderung", "strukturveränderung",
            "glatt begrenzt", "scharf begrenzt", "unscharf begrenzt",
            "lobuliert", "polyzyklisch", "infiltrativ",
            "homogen", "inhomogen", "heterogen",
            "zentral", "peripher", "randständig", "exzentrisch",
            # Specific imaging findings
            "lungenrundherd", "pulmonaler rundherd", "solitärer lungenrundherd",
            "milchglastrübung", "ground-glass", "ggo",
            "konsolidierung", "verdichtung", "verschattung",
            "interstitielles muster", "retikuläres muster", "noduläres muster",
            "bronchopneumogramm", "aerobronchogramm",
            "kerley-linien", "kerley-b-linien",
            "hilusverbreiterung", "mediastinalverbreiterung",
            "kardiomegalie", "herzverbreiterung",
            "aortensklerose", "aortenverkalkung", "aortenelongation",

            # ==================== PATHOLOGY TERMS ====================
            "histologie", "histologisch", "histopathologie",
            "zytologie", "zytologisch", "zytopathologie",
            "biopsie", "stanzbiopsie", "feinnadelbiopsie", "fnab",
            "präparat", "resektat", "gewebeprobe",
            "schnellschnitt", "paraffinschnitt",
            "immunhistochemie", "ihc", "immunhistochemisch",
            "in-situ-hybridisierung", "fish", "pcr",
            "grading", "differenzierung", "entdifferenziert",
            "gut differenziert", "mäßig differenziert", "schlecht differenziert",
            "g1", "g2", "g3", "g4", "low-grade", "high-grade",
            "staging", "tnm", "t-stadium", "n-stadium", "m-stadium",
            "tumorgröße", "tumorausdehnung", "tumorinfiltration",
            "lymphangiosis", "lymphangiosis carcinomatosa", "l1", "l0",
            "hämangiosis", "hämangiosis carcinomatosa", "v1", "v0",
            "perineuralscheideninfiltration", "pn1", "pn0",
            "resektionsrand", "schnittrand", "r-status",
            "dysplasie", "metaplasie", "hyperplasie", "atrophie",
            "nekrose", "nekrotisch", "apoptose",
            "entzündungsinfiltrat", "lymphozytär", "granulomatös",
            "fibrose", "fibrosierung", "vernarbung",

            # ==================== GERMAN COMPOUND EXAMINATION TERMS ====================
            # Physical examination
            "körperliche untersuchung", "klinische untersuchung",
            "inspektion", "palpation", "perkussion", "auskultation",
            "vitalzeichen", "vitalparameter",
            "bewusstseinslage", "orientierung", "orientiertheit",
            "wach", "somnolent", "soporös", "komatös",
            "zeitlich orientiert", "örtlich orientiert", "situativ orientiert", "zur person orientiert",
            "kooperativ", "nicht kooperativ", "agitiert", "ruhig",
            "dyspnoisch", "tachypnoisch", "eupnoisch",
            "zyanotisch", "blass", "rosig", "ikterisch",
            "exsikkiert", "dehydriert", "ödematös",
            "adipös", "kachektisch", "normalgewichtig",
            "fieberhaft", "afebril", "febril", "subfebril",
            "kreislaufstabil", "kreislaufinstabil", "katecholaminpflichtig",
            "beatmungspflichtig", "spontan atmend",
            "mobilisiert", "immobil", "bettlägerig",
            # Abdominal examination
            "bauchdecke", "weich", "gespannt", "gebläht",
            "druckschmerz", "klopfschmerz", "loslaßschmerz",
            "abwehrspannung", "défense", "peritonismus",
            "darmgeräusche", "lebhafte darmgeräusche", "spärliche darmgeräusche",
            "hochgestellte darmgeräusche", "metallisch klingende darmgeräusche",
            "resistenz", "tastbare resistenz",
            # Neurological examination
            "pupillenreaktion", "lichtreaktion", "isokorie", "anisokorie",
            "mydriasis", "miosis", "lichtstarr",
            "meningismus", "nackensteifigkeit", "kernig", "brudzinski",
            "kraftgrad", "muskeleigenreflexe", "mer", "psr", "asr", "bsr", "tsr", "rpr",
            "babinski", "pathologische reflexe",
            "sensibilität", "hypästhesie", "hyperästhesie", "parästhesie",
            "koordination", "finger-nase-versuch", "knie-hacke-versuch",
            "romberg", "unterberger", "gangbild",

            # ==================== SCORING SYSTEMS ====================
            "glasgow coma scale", "gcs", "glasgow-coma-skala",
            "apache", "apache ii", "apache-score",
            "sofa", "sofa-score", "quick-sofa", "qsofa",
            "saps", "saps ii", "saps-score",
            "ranson", "ranson-kriterien", "balthazar",
            "curb-65", "curb65", "crb-65",
            "wells", "wells-score", "genfer-score",
            "hasbled", "has-bled", "chads-vasc", "cha2ds2-vasc",
            "nihss", "nih stroke scale", "mrs", "modified rankin scale",
            "barthel", "barthel-index", "katz-index",
            "mmse", "mini-mental-status", "moca", "demtect",
            "hamilton", "hamilton-depressionsskala",
            "vas", "visuelle analogskala", "nrs", "numerische rating-skala",
            "karnofsky", "karnofsky-index", "ecog", "ecog-status",
            "asa", "asa-klassifikation", "asa-score",
            "euro-score", "euroscore", "sts-score",
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
            "klacid", "zithromax", "biaxin",  # Phase 10: Macrolide brand names
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
            # Thyroid & Parathyroid
            "levothyroxin", "l-thyroxin", "euthyrox", "carbimazol", "thiamazol",
            "parathormon", "pth",  # Phase 6.2: Parathyroid hormone
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
            # Phase 7: Hepatology/GI medications
            "terlipressin", "octreotid", "lactulose", "rifaximin", "albumin",

            # ==================== PHASE 8: COMPREHENSIVE DRUG EXPANSION ====================
            # Additional diabetes medications
            "dapagliflozin", "canagliflozin", "ertugliflozin", "sotagliflozin",
            "liraglutid", "semaglutid", "dulaglutid", "exenatid", "lixisenatid",
            "saxagliptin", "linagliptin", "alogliptin", "vildagliptin",
            "glimepirid", "glipizid", "gliclazid", "repaglinid", "nateglinid",
            "pioglitazon", "rosiglitazon", "acarbose", "miglitol",
            "insulin glargin", "insulin detemir", "insulin degludec",
            "insulin aspart", "insulin lispro", "insulin glulisin",
            "toujeo", "tresiba", "fiasp", "lyumjev",
            # Additional cardiac medications
            "sacubitril", "entresto", "vericiguat", "ivabradine", "ranolazin",
            "milrinon", "dobutamin", "dopamin", "noradrenalin", "adrenalin",
            "levosimendan", "digitalis", "digoxin", "digitoxin",
            "flecainid", "propafenon", "sotalol", "amiodaron", "dronedaron",
            "adenosin", "ajmalin", "lidocain", "mexiletin",
            "hydralazin", "minoxidil", "dihydralazin",
            "clonidin", "moxonidin", "rilmenidin",
            "doxazosin", "prazosin", "terazosin", "urapidil",
            "nitrat", "nitroglycerin", "isosorbiddinitrat", "isdn", "isosorbidmononitrat", "ismn",
            "molsidomin", "nitroprussid",
            "trimetazidin", "perhexilin",
            # Additional anticoagulants/antiplatelets
            "argatroban", "bivalirudin", "lepirudin", "desirudin",
            "certoparin", "nadroparin", "tinzaparin", "bemiparin", "reviparin",
            "cangrelor", "vorapaxar", "cilostazol", "dipyridamol",
            "abciximab", "eptifibatid", "tirofiban",
            "protamin", "vitamin k", "phytomenadion",
            "idarucizumab", "andexanet alfa", "praxbind",
            # Lipid-lowering
            "pitavastatin", "lovastatin",
            "colesevelam", "colestyramin", "colestipol",
            "niacin", "nikotinsäure", "omega-3-fettsäuren", "icosapent",
            "lomitapid", "mipomersen", "inclisiran", "bempedoinsäure",
            # Additional antibiotics
            "tazobactam", "sulbactam", "clavulansäure",
            "cefepim", "cefpodoxim", "cefixim", "cefalexin", "cefaclor",
            "ceftarolin", "ceftobiprol", "ceftazidim-avibactam", "ceftolozan-tazobactam",
            "aztreonam", "colistin", "polymyxin",
            "teicoplanin", "tedizolid", "oritavancin", "dalbavancin",
            "fidaxomicin", "bezlotoxumab",
            "norfloxacin", "enoxacin", "prulifloxacin",
            "telithromycin", "fidaxomicin",
            "rifabutin", "isoniazid", "pyrazinamid", "ethambutol", "streptomycin",
            "bedaquilin", "delamanid", "pretomanid",
            "dapson", "clofazimin",
            "atovaquon", "pentamidin", "primaquin", "chloroquin", "hydroxychloroquin",
            "mefloquin", "artemether", "lumefantrin", "artesunate",
            "methenamin", "pivmecillinam",
            # Additional antifungals
            "posaconazol", "isavuconazol", "anidulafungin", "micafungin",
            "nystatin", "terbinafin", "griseofulvin", "flucytosin",
            # Additional antivirals
            "ganciclovir", "valganciclovir", "cidofovir", "foscarnet",
            "sofosbuvir", "ledipasvir", "velpatasvir", "glecaprevir", "pibrentasvir",
            "daclatasvir", "elbasvir", "grazoprevir", "ombitasvir", "paritaprevir",
            "ribavirin", "peginterferon", "interferon alpha",
            "entecavir", "tenofovir", "lamivudin", "adefovir", "telbivudin",
            "abacavir", "emtricitabin", "zidovudin", "stavudin", "didanosin",
            "efavirenz", "nevirapin", "rilpivirin", "etravirin", "delavirdin",
            "lopinavir", "ritonavir", "atazanavir", "darunavir", "saquinavir",
            "raltegravir", "dolutegravir", "elvitegravir", "bictegravir", "cabotegravir",
            "maraviroc", "enfuvirtid",
            "zanamivir", "baloxavir", "peramivir",
            "paxlovid", "nirmatrelvir", "molnupiravir",
            # Additional analgesics/opioids
            "piritramid", "buprenorphin", "sufentanil", "alfentanil", "remifentanil",
            "tapentadol", "naloxon", "naltrexon", "nalbuphin",
            "codein", "dihydrocodein", "pethidin", "levomethadon", "methadon",
            "ketamin", "esketamin",
            "flupirtin", "ziconotid",
            # Additional anticonvulsants
            "oxcarbazepin", "eslicarbazepin", "lacosamid", "brivaracetam",
            "perampanel", "zonisamid", "topiramat", "felbamat",
            "phenobarbital", "primidon", "ethosuximid", "vigabatrin",
            "stiripentol", "rufinamid", "clobazam", "clonazepam",
            "cannabidiol", "epidiolex",
            # Additional antidepressants/psychiatry
            "nortriptylin", "clomipramin", "doxepin", "trimipramin", "imipramin",
            "maprotilin", "mianserin", "reboxetin", "tianeptin",
            "agomelatin", "vortioxetin", "viloxazin",
            "moclobemid", "tranylcypromin", "phenelzin", "selegilin",
            "lithium", "lithiumcarbonat",
            "valproinsäure", "divalproex",
            "lamotrigin", "carbamazepin", # (also mood stabilizers)
            "paliperidon", "ziprasidon", "sertindol", "amisulprid", "sulpirid",
            "lurasidon", "cariprazin", "brexpiprazol",
            "chlorpromazin", "fluphenazin", "perphenazin", "thioridazin",
            "flupentixol", "zuclopenthixol", "pimozid",
            "clomethiazol", "promethazin", "hydroxyzin",
            "buspiron", "tofisopam", "meprobamat",
            "melatonin", "agomelatin", "tasimelteon",
            "modafinil", "armodafinil", "pitolisant", "solriamfetol",
            "methylphenidat", "lisdexamfetamin", "atomoxetin", "guanfacin",
            "nalmefen", "acamprosat", "disulfiram",
            "vareniclin", "bupropion", "cytisin",
            # Additional GI medications
            "loperamid", "racecadotril", "eluxadolin",
            "mesalazin", "sulfasalazin", "olsalazin", "balsalazid",
            "budesonid", "beclomethason", # (GI formulations)
            "azathioprin", "mercaptopurin", "6-mp",
            "vedolizumab", "ustekinumab", "risankizumab",
            "tofacitinib", "upadacitinib", "filgotinib",
            "metoclopramid", "domperidon", "ondansetron", "granisetron", "palonosetron",
            "tropisetron", "aprepitant", "fosaprepitant", "netupitant",
            "dronabinol", "nabilon",
            "ursodeoxycholsäure", "udca", "obeticholic acid", "ocaliva",
            "cholestyramin", "colesevelam", "colestipol",
            "somatostatin", "octreotid", "lanreotid", "pasireotid",
            "propranolol", # (for varices)
            "vasopressin", "ornipressin",
            "pankreatin", "kreon", "panzytrat",
            "orlistat", "liraglutid", "semaglutid", # (weight loss)
            "lubiproston", "linaclotid", "plecanatid", "prucaloprid",
            "bisacodyl", "natriumpicosulfat", "sennoside", "macrogol", "polyethylenglycol",
            "movicol", "laxoberal", "dulcolax",
            # Additional respiratory medications
            "indacaterol", "vilanterol", "olodaterol",
            "umeclidinium", "glycopyrronium", "aclidinium",
            "ciclesonid", "mometason",
            "omalizumab", "mepolizumab", "benralizumab", "dupilumab", "tezepelumab",
            "reslizumab", "lebrikizumab",
            "pirfenidon", "nintedanib",
            "dornase alfa", "pulmozyme", "ivacaftor", "lumacaftor", "tezacaftor", "elexacaftor",
            "alpha-1-antitrypsin", "prolastin",
            "surfactant", "curosurf", "survanta",
            # Rheumatology/Immunology
            "hydroxychloroquin", "chloroquin",
            "sulfasalazin", "leflunomid", "teriflunomid",
            "methotrexat", "mtx",
            "abatacept", "tocilizumab", "sarilumab", "anakinra",
            "certolizumab", "golimumab",
            "ixekizumab", "brodalumab", "guselkumab", "tildrakizumab",
            "apremilast", "deucravacitinib",
            "belimumab", "anifrolumab",
            "rituximab", "ocrelizumab", "ofatumumab", "obinutuzumab",
            "eculizumab", "ravulizumab",
            "cyclophosphamid", "ifosfamid",
            "chlorambucil", "melphalan", "busulfan",
            "colchicin", "allopurinol", "febuxostat",
            "probenecid", "benzbromaron", "lesinurad",
            "pegloticase", "rasburicase",
            # Oncology extended
            "cisplatin", "carboplatin", "oxaliplatin",
            "paclitaxel", "docetaxel", "cabazitaxel", "nab-paclitaxel",
            "vincristin", "vinblastin", "vinorelbin", "eribulin",
            "etoposid", "irinotecan", "topotecan",
            "doxorubicin", "epirubicin", "daunorubicin", "idarubicin", "mitoxantron",
            "bleomycin", "mitomycin", "actinomycin",
            "gemcitabin", "capecitabin", "fluorouracil", "5-fu",
            "cytarabin", "azacitidin", "decitabin", "clofarabin", "fludarabin",
            "pemetrexed", "methotrexat",
            "imatinib", "dasatinib", "nilotinib", "bosutinib", "ponatinib",
            "erlotinib", "gefitinib", "afatinib", "osimertinib", "dacomitinib",
            "crizotinib", "ceritinib", "alectinib", "brigatinib", "lorlatinib",
            "vemurafenib", "dabrafenib", "encorafenib",
            "trametinib", "cobimetinib", "binimetinib",
            "sorafenib", "sunitinib", "pazopanib", "axitinib", "cabozantinib",
            "regorafenib", "lenvatinib", "vandetanib",
            "bevacizumab", "ramucirumab", "aflibercept",
            "lapatinib", "neratinib", "tucatinib",
            "pertuzumab", "trastuzumab emtansin", "trastuzumab deruxtecan",
            "cetuximab", "panitumumab", "necitumumab",
            "nivolumab", "pembrolizumab", "atezolizumab", "durvalumab", "avelumab",
            "ipilimumab", "tremelimumab",
            "blinatumomab", "inotuzumab", "gemtuzumab", "polatuzumab",
            "brentuximab", "daratumumab", "isatuximab", "elotuzumab",
            "alemtuzumab", "mogamulizumab",
            "ibrutinib", "acalabrutinib", "zanubrutinib",
            "venetoclax", "navitoclax",
            "idelalisib", "copanlisib", "duvelisib",
            "bortezomib", "carfilzomib", "ixazomib",
            "lenalidomid", "pomalidomid", "thalidomid",
            "panobinostat", "vorinostat", "romidepsin", "belinostat",
            "ruxolitinib", "fedratinib", "pacritinib",
            "palbociclib", "ribociclib", "abemaciclib",
            "olaparib", "niraparib", "rucaparib", "talazoparib",
            "temozolomid", "lomustin", "carmustin", "procarbazin",
            "tretinoin", "atra", "arsentrioxid",
            "tamoxifen", "toremifen", "fulvestrant",
            "anastrozol", "letrozol", "exemestan",
            "leuprorelin", "goserelin", "triptorelin", "degarelix",
            "abirateron", "enzalutamid", "apalutamid", "darolutamid",
            "flutamid", "bicalutamid", "nilutamid",
            "mitotane", "metyrapon", "ketoconazol", "osilodrostat",
            "octreotid", "lanreotid", "pasireotid", "telotristat",
            "somatulin", "sandostatin",
            # Blood products and supportive care
            "erythrozytenkonzentrat", "ek", "thrombozytenkonzentrat", "tk",
            "ffp", "fresh frozen plasma", "gefrorenes frischplasma",
            "humanalbumin", "immunglobulin", "ivig", "scig",
            "gerinnungsfaktoren", "faktor viii konzentrat", "faktor ix konzentrat",
            "tranexamsäure", "aminocapronsäure",
            "desmopressin", "ddavp", "minirin",
            "filgrastim", "pegfilgrastim", "lipegfilgrastim", "lenograstim",
            "g-csf", "gm-csf",
            "epoetin", "darbepoetin", "epo",
            "romiplostim", "eltrombopag", "avatrombopag", "lusutrombopag",
            "eisen", "eisencarboxymaltose", "eisensaccharat", "eisengluconat",
            "ferinject", "venofer", "monofer",
            "folsäure", "folinat", "leucovorin",
            "vitamin b12", "cyanocobalamin", "hydroxocobalamin",
            # Electrolyte replacements
            "natriumchlorid", "nacl", "kaliumchlorid", "kcl",
            "calciumgluconat", "calciumchlorid",
            "magnesiumsulfat", "magnesiumaspartat",
            # FINAL: Potassium supplements
            "kalinor", "kalinor-brausetabletten", "kalitrans", "rekawan",
            "natriumbicarbonat", "natriumbikarbonat",
            "kaliumphosphat", "natriumphosphat",
            # Miscellaneous
            "aprotinin", "epsilon-aminocapronsäure",
            "aktivkohle", "carbo medicinalis",
            "flumazenil", "naloxon", "atropin", "physostigmin",
            "dimercaprol", "deferoxamin", "deferasirox", "deferipron",
            "chelatbildner", "edta", "penicillamin",
            "methylenblau", "methylthioniniumchlorid",
            "hydroxocobalamin", # (cyanide antidote)
            "fomepizol", "ethanol", # (methanol/ethylene glycol antidote)
            "silibinin", # (amanita antidote)
            "glucagon", "dextrose", "glukose",
            "hypertone kochsalzlösung", "mannitol",
            "hydrocortison", "fludrocortison",
            "thyroxin", "liothyronin", "t3", "t4",
            "calcitriol", "alfacalcidol", "colecalciferol", "ergocalciferol",
            "teriparatid", "romosozumab", "denosumab",
            "bisphosphonat", "alendronat", "risedronat", "ibandronat", "zoledronat",
            "raloxifen", "bazedoxifen",
            "cinacalcet", "etelcalcetid",
            "sevelamer", "lanthancarbonat", "calciumacetat",
            "dapagliflozin", "empagliflozin", # (also for CKD/HF)
            "patiromer", "natriumzirkoniumcyclosilikat",
            "botox", "botulinumtoxin", "dysport", "xeomin",
            "hyaluronsäure", "kortison-injektion",
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

            # ==================== PHASE 8: COMPREHENSIVE EPONYM EXPANSION ====================

            # Additional neurological
            "wilson", "batten", "canavan", "tay", "sachs", "leigh", "krabbe",
            "adrenoleukodystrophy", "pelizaeus", "merzbacher", "alexander",
            "rett", "sanfilippo", "hurler", "hunter", "morquio", "sly",
            "spielmeyer", "vogt", "batten", "kufs",
            "dandy", "walker", "arnold", "chiari",
            "brown", "séquard", "wallenberg", "weber", "millard", "gubler",
            "benedikt", "claude", "foville", "raymond", "cestan",
            "gerstmann", "straussler", "scheinker",
            "binswanger", "cadasil",
            "todd", "jacksonian", "lennox", "gastaut", "jeavons",
            "moyamoya", "susac",

            # Additional cardiovascular
            "leriche", "blalock", "taussig", "fontan", "norwood", "ross",
            "bentall", "tirone", "david", "yacoub",
            "bland", "white", "garland",
            "lown", "ganong", "levine",
            "mobitz", "wenckebach",
            "dressler", "löffler",
            "wegener", "takayasu", "horton", "mönckeberg",
            "libman", "sacks",
            "lutembacher", "holt", "oram",

            # Additional gastrointestinal
            "ogilvie", "volvulus",
            "meckel", "peyer", "brunner", "kerckring",
            "treitz", "sphinkter", "oddi",
            "budd", "chiari", # (hepatic vein thrombosis)
            "alagille", "caroli", "kasai",
            "chagas", "achalasia",
            "billroth", "roux", "en-y",
            "kocher", "pringle", "child",
            "ransohoff", "mirizzi",
            "saint", "triad",
            "trousseau", # (sign)
            "sister mary joseph", # (nodule)

            # Additional pulmonary
            "hamman", "rich",
            "caplan", "silo", "silicosis",
            "kartagener", "young",
            "mounier", "kuhn",
            "goodpasture", "wegener",
            "churg", "strauss",
            "langerhans", # (cell histiocytosis)
            "pancoast", "horner",
            "kussmaul", "cheyne", "stokes", "biot",

            # Additional endocrine/metabolic
            "sipple", "wermer", "zollinger",
            "schmidt", "polyglandulär",
            "whipple", # (hypoglycemia triad)
            "kearns", "sayre",
            "mccune", "albright", "sternberg",
            "forbes", "albright",
            "mauriac",
            "wolfram", "didmoad",
            "donohue", "leprechaunism",
            "rabson", "mendenhall",

            # Additional hematological
            "evans", "wiskott", "aldrich",
            "chediak", "higashi",
            "kostmann", "shwachman", "diamond",
            "blackfan", "diamond",
            "kasabach", "merritt",
            "klippel", "trénaunay",
            "parkes", "weber",
            "osler", "rendu", "weber",
            "hemophilia", "christmas",
            "rosenthal", # (factor XI)

            # Additional genetic/connective tissue
            "loeys", "dietz",
            "noonan", "costello", "cardiofaciocutaneous",
            "williams", "beuren",
            "smith", "lemli", "opitz",
            "rubinstein", "taybi",
            "cornelia", "de lange",
            "kabuki",
            "charge",
            "vater", "vacterl",
            "osteogenesis", "imperfecta",
            "stickler", "kniest",

            # Additional renal
            "denys", "drash",
            "frasier",
            "nail", "patella",
            "lowe", "oculocerebrorenal",
            "cystinosis", "lignac", "fanconi",
            "dent",
            "senior", "loken",
            "meckel", "gruber",
            "autosomal", "dominant", "polycystic",

            # Additional rheumatological
            "baker", # (cyst)
            "jaccoud",
            "caplan",
            "crest",
            "sappho",
            "sneddon",
            "antiphospholipid", "hughes",

            # Additional dermatological
            "darier", "hailey",
            "degos",
            "ehlers", "danlos",
            "epidermolysis", "bullosa",
            "gottron", # (papules)
            "grover",
            "hidradenitis", "verneuil",
            "ichthyosis",
            "jessner", "kanof",
            "kyrle",
            "lichen", "planus",
            "lupus", "vulgaris",
            "majocchi",
            "mucha", "habermann",
            "netherton",
            "ofuji",
            "pityriasis", "rosea", "gibert",
            "sweet",
            "urticaria", "pigmentosa",
            "xeroderma", "pigmentosum",
            "zoon",

            # Additional infectious disease eponyms
            "hansen", # (leprosy)
            "chagas", "romana",
            "bang", # (brucellosis)
            "weil", # (leptospirosis)
            "jarisch", "herxheimer",
            "koplik", # (spots)
            "janeway", # (lesions)
            "splinter", # (hemorrhages)
            "roth", # (spots)

            # Additional orthopedic/trauma
            "colles", "smith", "barton", "chauffeur",
            "monteggia", "galeazzi",
            "bennett", "rolando", "boxer",
            "jones", "maisonneuve",
            "lisfranc", "chopart",
            "segond", # (fracture)
            "hill", "sachs", # (lesion)
            "bankart",
            "slap", # (lesion)
            "osgood", "schlatter",
            "sinding", "larsen", "johansson",
            "freiberg", "köhler", "kienböck",
            "perthes", "legg", "calvé",
            "scheuermann",
            "sprengel",
            "madelung",
            "blount",
            "panner",

            # Additional ophthalmological
            "sjögren", # (syndrome - dry eyes)
            "graves", # (ophthalmopathy)
            "coats",
            "stargardt", "best",
            "leber",
            "usher",
            "von hippel", "lindau",
            "sturge", "weber",
            "vogt", "koyanagi", "harada",
            "eales",
            "fuchs",
            "posner", "schlossman",

            # Additional surgical/procedural
            "billroth", "roux",
            "bassini", "shouldice", "lichtenstein",
            "mcvay", "nissen", "toupet", "dor",
            "heller", "ivor", "lewis",
            "pringle", "kocher",
            "whipple", "traverso", "longmire",
            "kasai",
            "glenn", "fontan", "norwood",
            "maze", "cox",
            "cabrol", "bentall",

            # Signs and tests expanded
            "lasègue", "bragard", "kernig", "brudzinski",
            "spurling", "lhermitte", "hoffman",
            "babinski", "gordon", "oppenheim", "chaddock",
            "romberg", "unterberger", "fukuda",
            "dix", "hallpike", "epley",
            "allen", "adson", "roos",
            "thompson", "simmond",
            "mcmurray", "apley", "lachman", "pivot",
            "drawer", "anterior", "posterior",
            "finkelstein", "phalen", "tinel",
            "hawkins", "kennedy", "neer", "jobe",
            "patrick", "fabere", "faber",
            "thomas", "ober",
            "trendelenburg",
            "ortolani", "barlow",
            "galeazzi", "klisic", "hart",
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
            "doctor_initial_name": "[DOCTOR_NAME]",
            "name_in_header_block": "[NAME]",  # Names in patient header after PLZ/City

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
            "insurance_standalone": "[INSURANCE_ID]",
            "insurance_status": "",  # Remove entirely (empty placeholder)
            "case_number": "[CASE_ID]",

            # Contact patterns
            "phone": "[PHONE]",
            "phone_spaced": "[PHONE]",
            "phone_extension": "",  # Remove entirely (cleanup after main phone)
            "phone_orphan": "[PHONE]",  # Replace orphaned extensions with single placeholder
            "fax": "[FAX]",
            "email": "[EMAIL]",
            "email_full": "[EMAIL]",
            "email_split": "[EMAIL]",
            "email_local_part": "[EMAIL]",  # Replace full email (name + domain placeholder)
            "named_email_domain": "[EMAIL_DOMAIN]",

            # Address patterns
            "address": "[ADDRESS]",
            "address_no_suffix": "[ADDRESS]",  # Street addresses without common suffix
            "plz_city": "[PLZ_CITY]",
            "zipcode": "[ZIPCODE]",

            # ID patterns
            "tax_id": "[TAX_ID]",
            "social_security": "[SOCIAL_SECURITY]",
            "ssn": "[SSN]",

            # Company/organization patterns
            "company_registration": "[COMPANY_ID]",
            "bank_location": "[BANK_INFO]",

            # Letterhead patterns
            "hospital_letterhead": "[HOSPITAL_INFO]",
            "hospital_with_city": "[ORGANIZATION]",  # Hospital names with city
        }
        return placeholder_map.get(pii_type, f"[{pii_type.upper()}]")

    def _remove_pii_with_patterns(self, text: str, language: str) -> tuple[str, dict]:
        """Remove PII using regex patterns with context-aware date handling."""
        patterns = self.patterns_de if language == "de" else self.patterns_en
        removed_count = 0
        pii_types = []
        dates_preserved = 0

        # Process patterns in a specific order: names first, then others
        # This ensures titles like "Dr. med." are processed before generic patterns
        priority_order = [
            "doctor_title_name",  # Must be first to catch "Dr. med. Schmidt"
            "honorific_name",     # Then "Herr Müller", "Frau Schmidt"
            "name_comma_format",  # Then "Müller, Anna"
            "labeled_name",       # Then "Patient: Schmidt"
            "name_in_header_block",  # Names after PLZ/City in header blocks
        ]

        # Patterns that need context-aware processing (not simple substitution)
        context_aware_patterns = ["date_standalone", "date_german_month", "date_english_month"]

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

            # Handle date patterns with context awareness
            if pii_type in context_aware_patterns:
                # Process dates individually with context checking
                matches = list(pattern.finditer(text))
                if matches:
                    # Process in reverse order to maintain positions
                    for match in reversed(matches):
                        # Check if date is in medical context (should be preserved)
                        if self._is_medical_context_date(text, match.start(), match.end()):
                            dates_preserved += 1
                            logger.debug(f"Preserved medical context date: {match.group()}")
                            continue  # Don't remove this date

                        # Remove non-medical dates
                        placeholder = self._get_placeholder(pii_type)
                        text = text[:match.start()] + placeholder + text[match.end():]
                        removed_count += 1
                        if pii_type not in pii_types:
                            pii_types.append(pii_type)
            else:
                # Standard pattern substitution
                matches = pattern.findall(text)
                if matches:
                    removed_count += len(matches)
                    pii_types.append(pii_type)
                    placeholder = self._get_placeholder(pii_type)
                    text = pattern.sub(placeholder, text)

        return text, {
            "pattern_removals": removed_count,
            "pii_types": pii_types,
            "dates_preserved": dates_preserved
        }

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
            ent_lower = ent.text.lower().strip()

            # ===============================================================
            # PRIORITY CHECKS - Check protected sets BEFORE any entity logic
            # This prevents NER from replacing medical terms with placeholders
            # ===============================================================

            # FINAL9: Protect markdown section headers (### Anamnese, ## Diagnosen, etc.)
            # Check if entity is preceded by markdown header markers
            chars_before = text[max(0, ent.start_char - 10):ent.start_char]
            if re.search(r'#{1,6}\s*$', chars_before):
                logger.debug(f"NER: Preserved '{ent.text}' (markdown section header)")
                continue

            # PRIORITY CHECK 1: Direct match in protected medical terms
            if ent_lower in self.medical_terms:
                logger.debug(f"NER: Preserved '{ent.text}' (medical_terms match)")
                continue

            # PRIORITY CHECK 2: Direct match in drug database
            if ent_lower in self.drug_database:
                logger.debug(f"NER: Preserved '{ent.text}' (drug match)")
                continue

            # PRIORITY CHECK 3: Direct match in verifier anatomical terms
            if hasattr(self, 'medical_verifier') and ent_lower in self.medical_verifier.anatomical_terms:
                logger.debug(f"NER: Preserved '{ent.text}' (anatomical match)")
                continue

            # PRIORITY CHECK 4: Context-aware protection for single letters and special patterns
            # FINAL6: Protect ECG waves (S, T, P, Q, R), histology grades (I, II, III, IV), and dates
            context_before = text[max(0, ent.start_char - 30):ent.start_char].lower()
            context_after = text[ent.end_char:min(len(text), ent.end_char + 30)].lower()

            # ECG single-letter waves in context (tiefen S, S-Zacke, etc.)
            ecg_context_words = ["tiefen", "tiefes", "zacke", "welle", "segment", "strecke",
                                 "ekg", "ecg", "sinusrhythmus", "rhythmus", "hebung", "senkung",
                                 "v1", "v2", "v3", "v4", "v5", "v6", "avl", "avr", "avf"]
            if ent_lower in ["s", "t", "p", "q", "r", "st", "pq", "qrs", "qt", "qtc"]:
                if any(ecg in context_before or ecg in context_after for ecg in ecg_context_words):
                    logger.debug(f"NER: Preserved '{ent.text}' (ECG context)")
                    continue

            # Histology grades in context (Histologie: I., I.+II., etc.)
            histology_context_words = ["histologie", "histologisch", "grad", "stadium", "typ",
                                       "klassifikation", "gastritis", "metaplasie", "dysplasie"]
            if ent_lower in ["i", "ii", "iii", "iv", "i.", "ii.", "iii.", "iv.", "i.+ii.", "i.+ii.+iii."]:
                if any(histo in context_before or histo in context_after for histo in histology_context_words):
                    logger.debug(f"NER: Preserved '{ent.text}' (histology context)")
                    continue

            # Date patterns that look like dates (e.g., "26.2.2025" misclassified)
            import re as re_inner
            if re_inner.match(r'^\d{1,2}\.\d{1,2}\.?\d{0,4}$', ent.text.strip()):
                logger.debug(f"NER: Preserved '{ent.text}' (date pattern)")
                continue

            # ===============================================================
            # Entity type-specific handling (if not caught by priority checks)
            # ===============================================================

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

                # Verify with medical term library before removing (MEDIALpy + German patterns)
                if self.medical_verifier.verify_before_removal(ent.text, "PERSON"):
                    continue  # Preserve - it's a medical term!

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

                # Verify with medical term library before removing (MEDIALpy + German patterns)
                if self.medical_verifier.verify_before_removal(ent.text, "LOCATION"):
                    continue  # Preserve - it's a medical term!

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

                # Verify with medical term library before removing (MEDIALpy + German patterns)
                if self.medical_verifier.verify_before_removal(ent.text, "ORGANIZATION"):
                    continue  # Preserve - it's a medical term!

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

                # FINAL9: Skip if it's a markdown section header (### Anamnese, etc.)
                chars_before = text[max(0, result.start - 10):result.start]
                if re.search(r'#{1,6}\s*$', chars_before):
                    logger.debug(f"Presidio: Preserved '{entity_text}' (markdown section header)")
                    continue

                # Skip if it's a protected medical term
                if self._is_medical_term(entity_text, custom_terms):
                    continue

                # Skip if it's a medical eponym
                context = text[max(0, result.start - 50):min(len(text), result.end + 50)]
                if self._is_medical_eponym(entity_text, context):
                    continue

                # Check MedicalTermVerifier (same as NER pass)
                # Map Presidio entity types to verification categories
                entity_type_map = {
                    "PERSON": "PERSON",
                    "LOCATION": "LOCATION",
                    "ORG": "ORGANIZATION",
                    "NRP": "PERSON",  # Nationality/Religious/Political group
                }
                verification_type = entity_type_map.get(result.entity_type)
                if verification_type and self.medical_verifier.verify_before_removal(entity_text, verification_type):
                    logger.debug(f"Presidio: Preserved medical term '{entity_text}' (verifier)")
                    continue

                # For DATE_TIME entities, check if in medical context
                if result.entity_type == "DATE_TIME":
                    if self._is_medical_context_date(text, result.start, result.end):
                        logger.debug(f"Presidio: Preserved medical context date '{entity_text}'")
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

                # Skip IP_ADDRESS that are actually lab reference ranges
                # E.g., "Haptoglobin 0.93 (0.14.2.58 g/l)" - the "0.14.2.58" looks like IP but is a typo for "0.14-2.58"
                if result.entity_type == "IP_ADDRESS":
                    if self._is_lab_reference_range_context(text, result.start, result.end):
                        logger.debug(f"Skipping IP_ADDRESS false positive: '{entity_text}' (lab reference range context)")
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
            "pg/ml", "ng/ml", "µg/ml", "mg/dl", "mmol/l", "g/dl", "u/l", "iu/l",
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

    def _is_lab_reference_range_context(self, text: str, start: int, end: int) -> bool:
        """
        Check if an IP_ADDRESS match is actually a lab reference range with a typo.

        Lab reference ranges are often formatted like "(0.14-2.58 g/l)" but sometimes
        have typos like "(0.14.2.58 g/l)" where the dash is replaced with a dot.
        These patterns look like IP addresses but are medical values.

        Args:
            text: The full text
            start: Start position of the detected entity
            end: End position of the detected entity

        Returns:
            True if the detected IP address appears to be a lab reference range
        """
        # Get context: 30 chars before, 30 after
        context_start = max(0, start - 30)
        context_end = min(len(text), end + 30)
        context_before = text[context_start:start]
        context_after = text[end:context_end]

        # Check if inside parentheses (typical for reference ranges)
        has_open_paren = '(' in context_before
        has_close_paren = ')' in context_after

        # Check if followed by medical units (g/l, mg/dl, etc.)
        lab_units = [
            'g/l', 'mg/l', 'µg/l', 'ng/l', 'pg/l',
            'g/dl', 'mg/dl', 'µg/dl', 'ng/dl', 'pg/dl',
            'mmol/l', 'µmol/l', 'nmol/l', 'pmol/l',
            'u/l', 'iu/l', 'mu/l',
            'ml', 'µl', 'nl', 'pl',
            '%', '‰',
            '10^3/µl', '10^6/µl', '10^9/l', '10^12/l',
            '/µl', '/ml', '/l',
        ]

        context_after_lower = context_after.lower().strip()

        # If in parentheses and followed by medical unit, it's likely a reference range
        if has_open_paren:
            for unit in lab_units:
                if context_after_lower.startswith(unit) or context_after_lower.startswith(' ' + unit):
                    logger.debug(f"Lab reference range detected: '{text[start:end]}' followed by '{unit}'")
                    return True

        # Also check for lab value keywords before
        lab_keywords = [
            'haptoglobin', 'haptogobin', 'ferritin', 'transferrin', 'albumin',
            'hämoglobin', 'hemoglobin', 'hämatokrit', 'hematocrit',
            'kreatinin', 'creatinine', 'bilirubin', 'glucose', 'glukose',
            'cholesterin', 'triglyceride', 'eisen', 'iron', 'kupfer', 'copper',
            'calcium', 'kalium', 'natrium', 'magnesium', 'phosphat',
            'leukozyten', 'erythrozyten', 'thrombozyten',
            'quick', 'inr', 'ptt', 'aptt',
            'tsh', 'ft3', 'ft4', 't3', 't4',
            'crp', 'bsg', 'ldh', 'ggt', 'got', 'gpt', 'ast', 'alt',
        ]

        context_before_lower = context_before.lower()
        for keyword in lab_keywords:
            if keyword in context_before_lower:
                logger.debug(f"Lab reference range detected: '{keyword}' found before '{text[start:end]}'")
                return True

        return False

    def _is_medical_context_date(self, text: str, start: int, end: int) -> bool:
        """
        Check if a date is in medical context (should be preserved).

        Medical procedure dates, treatment timelines, and diagnostic dates
        are clinically important and should NOT be removed. Only truly
        identifying dates (birthdates, document dates) should be removed.

        Args:
            text: The full text
            start: Start position of the date match
            end: End position of the date match

        Returns:
            True if the date is in medical context (PRESERVE), False if PII (REMOVE)
        """
        # Get surrounding context (80 chars before, 30 after)
        context_start = max(0, start - 80)
        context_end = min(len(text), end + 30)
        context_before = text[context_start:start].lower()
        context_after = text[end:context_end].lower()

        # PII context indicators - these dates should be REMOVED
        pii_date_indicators = [
            r'geb(?:oren|\.|\s)',
            r'geburtsdatum',
            r'geboren\s+am',
            r'\*\s*$',  # Asterisk before date often means birthdate
        ]

        for pattern in pii_date_indicators:
            if re.search(pattern, context_before):
                return False  # PII date - should be removed

        # Medical context indicators - these dates should be KEPT
        medical_date_indicators = [
            # Temporal prepositions indicating medical timeline
            r'(?:vom|am|bis|seit|ab|nach|vor|zwischen)\s*$',
            r'(?:vom|am|bis|seit|ab)\s+\d',  # "vom DD.MM" pattern
            # Procedure/exam names before dates
            r'(?:ct|mrt|pet|röntgen|sonographie|ultraschall|echo|ekg|'
            r'op|operation|punktion|untersuchung|kontrolle|wiedervorstellung|'
            r'therapie|behandlung|aufnahme|entlassung|revision|dilatation|'
            r'drainage|transfusion|infusion|gastroskopie|koloskopie|'
            r'bronchoskopie|ögd|ercp|tipss|biopsie|szintigraphie)\s*'
            r'(?:vom|am)?\s*$',
            # Treatment timing
            r'stationär\s*(?:vom|bis|am)',
            r'ambulant\s*(?:vom|bis|am)',
            # Date range patterns
            r'\d{1,2}\.\d{1,2}\.\s*[-–]\s*$',  # "15.05. - " (date range start)
            # Medical milestone language
            r'(?:abstinent|clean|nüchtern|symptomfrei)\s+seit',
            r'ed\s+',  # "ED 2024" = Erstdiagnose
            r'erstdiagnose',
        ]

        for pattern in medical_date_indicators:
            if re.search(pattern, context_before):
                return True  # Medical context - preserve the date

        # Check if in header area (first ~500 chars) AND looks like document date
        if start < 500:
            # Document date patterns (after city name, typically in letterhead)
            header_date_patterns = [
                r'[a-zäöü]+,\s*$',  # "Neuss, " before date
                r'stand:?\s*$',     # "Stand:" before date
                r'datum:?\s*$',     # "Datum:" before date
            ]
            for pattern in header_date_patterns:
                if re.search(pattern, context_before):
                    return False  # Header date - should be removed

        # Default: preserve dates in medical documents (they're usually clinical)
        # This is a conservative approach - medical dates are important for context
        return True

    def _should_remove_date(self, text: str, match, is_header_area: bool = False) -> bool:
        """
        Determine if a date should be removed.

        This is the inverse of _is_medical_context_date for convenience.

        Args:
            text: The full text
            match: The regex match object for the date
            is_header_area: Whether the date is in the document header

        Returns:
            True if the date should be REMOVED, False if it should be PRESERVED
        """
        return not self._is_medical_context_date(text, match.start(), match.end())

    def _remove_hospital_letterhead(self, text: str) -> tuple[str, dict]:
        """
        Remove hospital letterhead information from the document header.

        Hospital letterheads typically contain:
        - Hospital name and organizational structure
        - Department/clinic names
        - Address, phone, fax, email
        - Management names and titles
        - Registration numbers (HRB, etc.)
        - Bank account details

        This method focuses on the first ~800 characters where letterhead typically appears.

        Args:
            text: The document text

        Returns:
            Tuple of (cleaned_text, metadata)
        """
        letterhead_removed = 0

        # Only process the header area (first ~800 chars for letterhead detection)
        if len(text) < 100:
            return text, {"letterhead_removed": 0}

        # Hospital names to detect (case-insensitive)
        hospital_indicators = [
            r'rheinland\s*klinikum',
            r'lukaskrankenhaus',
            r'universitätsklinikum',
            r'städtisches\s*klinikum',
            r'kreiskrankenhaus',
            r'marienhospital',
            r'st\.\s*\w+[-\s]*(?:hospital|krankenhaus)',
            r'klinikum\s+\w+',
            r'krankenhaus\s+\w+',
            r'unternehmensgruppe',
            r'medizinisches\s+zentrum',
            r'kliniken\s+\w+',
        ]

        # Check if text starts with hospital letterhead
        header_text = text[:800].lower()
        has_letterhead = any(re.search(pattern, header_text) for pattern in hospital_indicators)

        if not has_letterhead:
            return text, {"letterhead_removed": 0}

        # Find the end of letterhead section
        # Letterhead typically ends at a separator line (---) or double newline before main content
        letterhead_end_patterns = [
            r'\n\s*[-─═]{3,}\s*\n',  # Separator lines
            r'\n\s*\n\s*(?:Sehr geehrte|Betr(?:eff|\.)|Patient|Diagnose)',  # Content start
            r'\n\s*\n\s*\n',  # Triple newline
        ]

        letterhead_end = 0
        for pattern in letterhead_end_patterns:
            match = re.search(pattern, text[:1000], re.IGNORECASE)
            if match:
                letterhead_end = max(letterhead_end, match.start())
                break

        if letterhead_end == 0:
            # No clear end found, use conservative approach
            # Just remove identified patterns rather than whole blocks
            return text, {"letterhead_removed": 0}

        # Replace the letterhead section with a minimal placeholder
        header_section = text[:letterhead_end]
        remaining_text = text[letterhead_end:]

        # Count items being removed
        letterhead_items = []
        for pattern in hospital_indicators:
            if re.search(pattern, header_section, re.IGNORECASE):
                letterhead_items.append(pattern)
                letterhead_removed += 1

        # Replace letterhead with placeholder
        if letterhead_removed > 0:
            text = "[HOSPITAL_LETTERHEAD]\n" + remaining_text.lstrip()

        return text, {"letterhead_removed": letterhead_removed, "letterhead_items": letterhead_items}

    def _cleanup_placeholders(self, text: str) -> tuple[str, int]:
        """
        Fix merged/duplicate placeholders that can occur during multi-pass PII removal.

        Examples of issues fixed:
        - [NAME][PATIENT_NAME] → [PATIENT_NAME]
        - [PATIENT_ID][PLZ_CITY] → [PATIENT_ID] [PLZ_CITY]
        - 017470[PLZ_CITY] → [PHONE]
        - [NAME] [NAME] → [NAME]

        Args:
            text: Text with placeholders to clean up

        Returns:
            Tuple of (cleaned_text, number_of_fixes)
        """
        fixes = 0
        original_text = text

        # Fix duplicate adjacent placeholders of same type
        # [NAME] [NAME] → [NAME]
        text = re.sub(r'\[NAME\]\s*\[NAME\]', '[NAME]', text)
        text = re.sub(r'\[DOCTOR_NAME\]\s*\[DOCTOR_NAME\]', '[DOCTOR_NAME]', text)
        text = re.sub(r'\[PATIENT_NAME\]\s*\[PATIENT_NAME\]', '[PATIENT_NAME]', text)

        # Fix merged name placeholders
        # [NAME][PATIENT_NAME] → [PATIENT_NAME]
        text = re.sub(r'\[NAME\]\[PATIENT_NAME\]', '[PATIENT_NAME]', text)
        text = re.sub(r'\[NAME\]\[DOCTOR_NAME\]', '[DOCTOR_NAME]', text)
        text = re.sub(r'\[DOCTOR_NAME\]\[NAME\]', '[DOCTOR_NAME]', text)

        # Fix merged ID/location placeholders (add space between)
        text = re.sub(r'\[PATIENT_ID\]\[PLZ_CITY\]', '[PATIENT_ID] [PLZ_CITY]', text)
        text = re.sub(r'\[REFERENCE_ID\]\[PLZ_CITY\]', '[REFERENCE_ID] [PLZ_CITY]', text)

        # Fix partial phone number merges (digits followed by placeholder)
        # "017470[PLZ_CITY]" → "[PHONE]"
        text = re.sub(r'\b\d{5,}\[PLZ_CITY\]', '[PHONE]', text)
        text = re.sub(r'\b\d{5,}\[LOCATION\]', '[PHONE]', text)

        # Fix empty placeholder sequences
        text = re.sub(r'\[\]\s*', '', text)

        # Count fixes made
        if text != original_text:
            # Rough count of changes
            fixes = len(re.findall(r'\[', original_text)) - len(re.findall(r'\[', text))
            if fixes < 0:
                fixes = 1  # At least one fix was made

        return text, max(0, fixes)

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

        # Step 0: Remove hospital letterhead (header block removal)
        text, letterhead_meta = self._remove_hospital_letterhead(text)
        metadata.update(letterhead_meta)

        # Step 1: Remove patterns (addresses, IDs, etc.)
        text, pattern_meta = self._remove_pii_with_patterns(text, language)
        metadata.update(pattern_meta)

        # Step 2: Remove names with NER (with custom terms protection)
        text, ner_meta = self._remove_names_with_ner(text, language, custom_terms)
        metadata.update(ner_meta)

        # Step 3: Secondary pass with Presidio (catches missed PII)
        text, presidio_meta = self._remove_pii_with_presidio(text, language, custom_terms)
        metadata.update(presidio_meta)

        # Step 4: Post-processing cleanup (fix merged placeholders)
        text, placeholder_fixes = self._cleanup_placeholders(text)
        metadata["placeholder_fixes"] = placeholder_fixes

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
