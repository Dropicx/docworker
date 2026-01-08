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
            # =============================================================
            # NAME PATTERNS (NEW - Critical for GDPR compliance)
            # =============================================================

            # German doctor/professional titles with names
            # Matches: "Dr. med. Schmidt", "Prof. Dr. Weber", "OA Müller"
            # IMPORTANT: Requires period or space after abbreviations to avoid matching
            # words like "Druckgefühle" (starts with "Dr") or "Professor" as separate
            "doctor_title_name": re.compile(
                r"\b(?:Dr\.[\s]*(?:med\.?|rer\.?\s*nat\.?|phil\.?|jur\.?|h\.?\s*c\.?)?[\s\.]*|"
                r"Prof\.[\s]*(?:Dr\.[\s]*(?:med\.?|h\.?\s*c\.?)?[\s\.]*)?|"
                r"Dipl\.[\s\-]?(?:Med\.?|Ing\.?|Psych\.?)\s*|"
                r"OA\s+|Oberarzt\s+|Oberärztin\s+|"
                r"CA\s+|Chefarzt\s+|Chefärztin\s+|"
                r"FA\s+|Facharzt\s+|Fachärztin\s+)"
                r"([A-ZÄÖÜ][a-zäöüß]+(?:[\s\-][A-ZÄÖÜ][a-zäöüß]+)?)\b",
                re.IGNORECASE
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
            # IMPORTANT: Requires colon separator to avoid matching "Patient hat" etc.
            "labeled_name": re.compile(
                r"(?:Patient(?:in)?|Versicherte[rn]?|"
                r"Auftraggeber|Einsender|Ansprechpartner|"
                r"Empfänger|Absender):\s*"
                r"([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)",
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
            "insurance_company": re.compile(
                r"(?:AOK|TK|Barmer|DAK|BKK|IKK|KKH|HEK|hkk|Techniker|"
                r"KNAPPSCHAFT|Viactiv|Mobil\s*Oil|SBK|mhplus|Novitas|"
                r"Pronova|Big\s*direkt|Audi\s*BKK|BMW\s*BKK|Bosch\s*BKK)"
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
            "doctor_title_name": re.compile(
                r"(?:Dr\.?|Prof\.?|Professor|"
                r"MD|M\.D\.|"
                r"PhD|Ph\.D\.|"
                r"RN|NP|PA|"
                r"Attending|Resident)\s+"
                r"([A-Z][a-z]+(?:[\s\-][A-Z][a-z]+)*)",
                re.IGNORECASE
            ),

            # English honorifics with names (Mr. Smith, Mrs. Johnson)
            "honorific_name": re.compile(
                r"(?:Mr\.?|Mrs\.?|Ms\.?|Miss|Sir|Madam|Dame)\s+"
                r"([A-Z][a-z]+(?:[\s\-][A-Z][a-z]+)*)",
                re.IGNORECASE
            ),

            # English patient name labels
            # IMPORTANT: Requires colon separator to avoid false matches
            "labeled_name": re.compile(
                r"(?:Patient|Name|First\s*Name|Last\s*Name|Surname|"
                r"Insured|Policyholder|Client|Customer):\s*"
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                re.IGNORECASE
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

    def _is_medical_term(self, word: str, custom_terms: set | None = None) -> bool:
        """Check if word is a protected medical term or drug name."""
        word_lower = word.lower()
        if word_lower in self.medical_terms or word_lower in self.drug_database:
            return True
        if custom_terms and word_lower in custom_terms:
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

        # Calculate totals (all PII entities removed)
        metadata["entities_detected"] = (
            metadata.get("pattern_removals", 0) +
            metadata.get("ner_removals", 0) +
            metadata.get("ner_locations_removed", 0) +
            metadata.get("ner_orgs_removed", 0) +
            metadata.get("ner_dates_removed", 0) +
            metadata.get("ner_times_removed", 0)
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
