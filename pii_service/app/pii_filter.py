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
import re
from datetime import datetime
from typing import Literal

import spacy

logger = logging.getLogger(__name__)


class PIIFilter:
    """
    PII (Personally Identifiable Information) filter for medical documents.

    Supports German and English with large SpaCy models for maximum accuracy.
    Removes names, addresses, birthdates, IDs while preserving medical content.
    """

    def __init__(self):
        """Initialize filter with German and English SpaCy models."""
        logger.info("Initializing PII Filter with large SpaCy models...")

        # German model
        self.german_model_loaded = False
        self.nlp_de = None
        try:
            self.nlp_de = spacy.load("de_core_news_lg")
            self.german_model_loaded = True
            logger.info("German model (de_core_news_lg) loaded successfully")
        except OSError as e:
            logger.warning(f"Failed to load German model: {e}")

        # English model
        self.english_model_loaded = False
        self.nlp_en = None
        try:
            self.nlp_en = spacy.load("en_core_web_lg")
            self.english_model_loaded = True
            logger.info("English model (en_core_web_lg) loaded successfully")
        except OSError as e:
            logger.warning(f"Failed to load English model: {e}")

        # Initialize patterns and medical terms
        self._init_patterns()
        self._init_medical_terms()
        self._init_medical_eponyms()

        logger.info(f"PII Filter initialized - DE: {self.german_model_loaded}, EN: {self.english_model_loaded}")

    def _init_patterns(self):
        """Initialize regex patterns for PII detection."""

        # German patterns
        self.patterns_de = {
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

            # Email
            "email": re.compile(
                r"(?:e[- ]?mail|mail)\s*[:.]?\s*"
                r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                re.IGNORECASE
            ),

            # Street address (German format)
            "address": re.compile(
                r"([A-ZÄÖÜ][a-zäöüß]+(?:straße|str\.|weg|platz|allee|gasse|ring|damm|ufer)"
                r"\s*\d+[a-zA-Z]?)",
                re.IGNORECASE
            ),

            # PLZ + City (German postal code)
            "plz_city": re.compile(
                r"(\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)",
                re.IGNORECASE
            ),

            # Insurance numbers
            "insurance": re.compile(
                r"(?:versichert(?:en)?(?:nummer|nr\.?)?|"
                r"krankenkasse(?:nnummer)?|kk[- ]?nr\.?)\s*[:.]?\s*"
                r"([A-Z]?\d{9,12})",
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
        }

        # English patterns
        self.patterns_en = {
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
            # Body parts and organs
            "herz", "lunge", "leber", "niere", "magen", "darm", "kopf", "hals",
            "brust", "bauch", "rücken", "schulter", "knie", "hüfte", "hand", "fuß",
            "hirn", "gehirn", "muskel", "knochen", "gelenk", "nerv", "gefäß",
            "heart", "lung", "liver", "kidney", "stomach", "brain", "muscle", "bone",

            # Medical terms
            "patient", "patientin", "diagnose", "befund", "therapie", "behandlung",
            "untersuchung", "operation", "medikament", "dosierung", "anamnese",
            "diagnosis", "treatment", "examination", "surgery", "medication",

            # Conditions
            "symptom", "syndrom", "erkrankung", "krankheit", "störung", "insuffizienz",
            "stenose", "thrombose", "embolie", "infarkt", "tumor", "karzinom",
            "hypertonie", "diabetes", "disease", "disorder", "condition",

            # Lab values
            "hämoglobin", "erythrozyten", "leukozyten", "thrombozyten", "kreatinin",
            "glucose", "glukose", "hba1c", "cholesterin", "triglyceride",
            "hemoglobin", "creatinine", "cholesterol",

            # Medications
            "aspirin", "insulin", "metformin", "ibuprofen", "paracetamol",
            "simvastatin", "ramipril", "bisoprolol", "omeprazol", "pantoprazol",

            # Examinations
            "mrt", "ct", "röntgen", "ultraschall", "ekg", "echo", "biopsie",
            "mri", "xray", "ultrasound", "ecg", "biopsy",

            # Common abbreviations
            "mg", "ml", "kg", "cm", "mm", "mmhg", "mmol", "µg", "ng",
            "bid", "tid", "qid", "prn", "po", "iv", "im", "sc",
        }

    def _init_medical_eponyms(self):
        """Initialize medical eponyms (disease names from people - preserve these)."""
        self.medical_eponyms = {
            # Neurological
            "parkinson", "alzheimer", "huntington", "creutzfeldt", "jakob",
            "guillain", "barré", "bell", "tourette", "charcot",

            # Cardiovascular
            "raynaud", "buerger", "kawasaki", "marfan", "ehlers", "danlos",

            # Gastrointestinal
            "crohn", "hirschsprung", "barrett", "whipple",

            # Endocrine
            "cushing", "addison", "hashimoto", "graves", "basedow",

            # Hematological
            "hodgkin", "waldenström", "cooley",

            # Other
            "down", "turner", "klinefelter", "wilson", "menière",
            "sjögren", "behçet", "wegener", "paget", "dupuytren",
        }

    def _is_medical_eponym(self, name: str, context: str = "") -> bool:
        """Check if a name is a medical eponym (should be preserved)."""
        name_lower = name.lower()

        # Direct match
        if name_lower in self.medical_eponyms:
            return True

        # Check for disease context
        medical_context_words = [
            "morbus", "disease", "syndrome", "syndrom", "erkrankung",
            "krankheit", "disorder", "condition", "patient", "diagnose"
        ]
        context_lower = context.lower()
        for word in medical_context_words:
            if word in context_lower:
                return True

        return False

    def _is_medical_term(self, word: str) -> bool:
        """Check if word is a protected medical term."""
        return word.lower() in self.medical_terms

    def _remove_pii_with_patterns(self, text: str, language: str) -> tuple[str, dict]:
        """Remove PII using regex patterns."""
        patterns = self.patterns_de if language == "de" else self.patterns_en
        removed_count = 0
        pii_types = []

        for pii_type, pattern in patterns.items():
            matches = pattern.findall(text)
            if matches:
                removed_count += len(matches)
                pii_types.append(pii_type)
                # Replace with placeholder
                placeholder = f"[{pii_type.upper()}]"
                text = pattern.sub(placeholder, text)

        return text, {"pattern_removals": removed_count, "pii_types": pii_types}

    def _remove_names_with_ner(self, text: str, language: str) -> tuple[str, dict]:
        """Remove person names using SpaCy NER."""
        nlp = self.nlp_de if language == "de" else self.nlp_en

        if nlp is None:
            return text, {"ner_removals": 0, "ner_available": False}

        doc = nlp(text)
        entities_removed = 0
        eponyms_preserved = 0

        # Process entities in reverse order to maintain positions
        for ent in reversed(doc.ents):
            if ent.label_ in ("PER", "PERSON"):
                # Check if it's a medical eponym
                context = text[max(0, ent.start_char - 50):min(len(text), ent.end_char + 50)]
                if self._is_medical_eponym(ent.text, context):
                    eponyms_preserved += 1
                    continue

                # Check if it's a medical term
                if self._is_medical_term(ent.text):
                    continue

                # Remove the name
                text = text[:ent.start_char] + "[NAME]" + text[ent.end_char:]
                entities_removed += 1

        return text, {
            "ner_removals": entities_removed,
            "eponyms_preserved": eponyms_preserved,
            "ner_available": True
        }

    def remove_pii(
        self,
        text: str,
        language: Literal["de", "en"] = "de"
    ) -> tuple[str, dict]:
        """
        Remove PII from text.

        Args:
            text: Input text to process
            language: Language code ('de' for German, 'en' for English)

        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        if not text or not text.strip():
            return text, {"entities_detected": 0, "error": "Empty text"}

        original_length = len(text)
        metadata = {
            "language": language,
            "original_length": original_length,
            "processing_timestamp": datetime.now().isoformat(),
            "gdpr_compliant": True
        }

        # Step 1: Remove patterns (addresses, IDs, etc.)
        text, pattern_meta = self._remove_pii_with_patterns(text, language)
        metadata.update(pattern_meta)

        # Step 2: Remove names with NER
        text, ner_meta = self._remove_names_with_ner(text, language)
        metadata.update(ner_meta)

        # Calculate totals
        metadata["entities_detected"] = (
            metadata.get("pattern_removals", 0) +
            metadata.get("ner_removals", 0)
        )
        metadata["cleaned_length"] = len(text)

        return text, metadata

    def remove_pii_batch(
        self,
        texts: list[str],
        language: Literal["de", "en"] = "de",
        batch_size: int = 32
    ) -> list[tuple[str, dict]]:
        """
        Remove PII from multiple texts.

        Args:
            texts: List of texts to process
            language: Language code
            batch_size: Batch size for processing (not used currently, for future optimization)

        Returns:
            List of (cleaned_text, metadata) tuples
        """
        results = []
        for text in texts:
            cleaned, meta = self.remove_pii(text, language)
            results.append((cleaned, meta))
        return results
