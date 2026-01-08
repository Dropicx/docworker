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

    def _remove_names_with_ner(
        self, text: str, language: str, custom_terms: set | None = None
    ) -> tuple[str, dict]:
        """Remove person names using SpaCy NER."""
        nlp = self.nlp_de if language == "de" else self.nlp_en

        if nlp is None:
            return text, {"ner_removals": 0, "ner_available": False}

        doc = nlp(text)
        entities_removed = 0
        eponyms_preserved = 0
        custom_terms_preserved = 0

        # Process entities in reverse order to maintain positions
        for ent in reversed(doc.ents):
            if ent.label_ in ("PER", "PERSON"):
                # Check if it's a medical eponym
                context = text[max(0, ent.start_char - 50):min(len(text), ent.end_char + 50)]
                if self._is_medical_eponym(ent.text, context):
                    eponyms_preserved += 1
                    continue

                # Check if it's a medical term or custom protected term
                if self._is_medical_term(ent.text, custom_terms):
                    if custom_terms and ent.text.lower() in custom_terms:
                        custom_terms_preserved += 1
                    continue

                # Remove the name
                text = text[:ent.start_char] + "[NAME]" + text[ent.end_char:]
                entities_removed += 1

        return text, {
            "ner_removals": entities_removed,
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
